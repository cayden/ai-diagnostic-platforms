# -*- coding: utf-8 -*-
"""湖企智库 - AI 本地知识库系统（Flask 主应用）
面向湖州企业敏感数据场景：DeepSeek 本地部署 + RAG，数据不出域。
运行：python app.py  →  http://127.0.0.1:5102
"""
import os
import time
import uuid
import hashlib
import json
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, session

import config
from modules import database
from modules import document_parser, chunker, embedder, rag_engine, knowledge_graph, vector_store

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.SEED_DIR, exist_ok=True)


# ---------------- 会话与鉴权 ----------------
def _user():
    return session.get("username")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _user():
            return jsonify({"success": False, "error": "未登录"}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = database.get_user(_user() or "")
        if not u or u["role"] != "admin":
            return jsonify({"success": False, "error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return wrapper


def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64]


# ---------------- 页面 ----------------
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ---------------- 认证 ----------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    u = database.auth_user(data.get("username", ""), data.get("password", ""))
    if not u:
        return jsonify({"success": False, "error": "用户名或密码错误"})
    session["username"] = u["username"]
    session["role"] = u["role"]
    database.log_audit(u["username"], "登录", "", "", _client_ip())
    return jsonify({"success": True, "user": {"username": u["username"], "role": u["role"], "dept": u["dept"]}})


@app.route("/api/logout", methods=["POST"])
def logout():
    if _user():
        database.log_audit(_user(), "登出", "", "", _client_ip())
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def me():
    if not _user():
        return jsonify({"success": False, "logged_in": False})
    u = database.get_user(_user())
    if not u:
        return jsonify({"success": False, "logged_in": False})
    return jsonify({"success": True, "logged_in": True, "user": {
        "username": u["username"], "role": u["role"], "dept": u["dept"], "max_level": u["max_level"]}})


# ---------------- 文档管理 ----------------
@app.route("/api/documents", methods=["GET"])
@login_required
def list_docs():
    u = database.get_user(_user())
    max_level = u["max_level"] if u else 1
    return jsonify({"success": True, "documents": database.list_documents(max_level=max_level)})


@app.route("/api/documents", methods=["POST"])
@login_required
def upload_doc():
    u = database.get_user(_user())
    if not u:
        return jsonify({"success": False, "error": "用户不存在"})
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"success": False, "error": "未选择文件"})
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in config.ALLOWED_EXTS:
        return jsonify({"success": False, "error": "不支持的文件类型: %s" % ext})
    title = (request.form.get("title") or os.path.splitext(f.filename)[0]).strip()
    category = request.form.get("category") or "综合"
    level = request.form.get("level") or "公开"
    if level not in database.LEVELS:
        level = "公开"
    # 权限校验：用户只能上传不高于自身权限级别的文档
    if database.LEVELS.get(level, 2) > u["max_level"]:
        return jsonify({"success": False, "error": "无权上传 %s 级别文档" % level})
    uid = uuid.uuid4().hex[:12]
    save_path = os.path.join(config.UPLOAD_DIR, uid + ext)
    f.save(save_path)
    doc_id = database.add_document(title, f.filename, save_path, category, level, "upload", u["username"])
    ok, msg = _process_document(doc_id)
    database.log_audit(u["username"], "上传文档", title, "%s %s" % (msg, level), _client_ip())
    return jsonify({"success": ok, "doc_id": doc_id, "message": msg, "doc": database.get_document(doc_id)})


@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
@admin_required
def delete_doc(doc_id):
    doc = database.get_document(doc_id)
    if not doc:
        return jsonify({"success": False, "error": "文档不存在"})
    if doc["filepath"] and os.path.exists(doc["filepath"]) and doc["source"] == "upload":
        try:
            os.remove(doc["filepath"])
        except OSError:
            pass
    database.delete_document(doc_id)
    database.log_audit(_user(), "删除文档", doc["title"], "", _client_ip())
    return jsonify({"success": True})


@app.route("/api/documents/<int:doc_id>/reindex", methods=["POST"])
@admin_required
def reindex_doc(doc_id):
    ok, msg = _process_document(doc_id)
    return jsonify({"success": ok, "message": msg})


def _process_document(doc_id):
    """解析 → 分块 → 入库 → 标记完成"""
    doc = database.get_document(doc_id)
    if not doc:
        return False, "文档不存在"
    path = doc["filepath"]
    text = ""
    if doc["source"] == "seed":
        text = document_parser.parse_document(path)
    elif path and os.path.exists(path):
        text = document_parser.parse_document(path)
    if not text or not text.strip():
        database.update_doc_status(doc_id, "error", error="解析失败：无法提取文本内容（请检查文件格式）")
        return False, "解析失败：无法提取文本内容"
    chunks = chunker.split_text(text)
    if not chunks:
        database.update_doc_status(doc_id, "error", error="文本内容为空")
        return False, "文本内容为空"
    level = doc["level"]
    database.replace_chunks(doc_id, [(i, c, level, t) for i, (c, t) in enumerate(chunks)])
    database.update_doc_status(doc_id, "ready", chunk_count=len(chunks))
    vector_store.index_document(doc_id)
    return True, "解析成功，共生成 %d 个知识片段" % len(chunks)


# ---------------- 问答 ----------------
@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    u = database.get_user(_user())
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"success": False, "error": "请输入问题"})
    if len(question) > 500:
        return jsonify({"success": False, "error": "问题过长"})
    max_level = u["max_level"] if u else 1
    result = rag_engine.query(question, username=_user(), max_level=max_level,
                              category=data.get("category") or None)
    return jsonify({"success": True, **result})


@app.route("/api/retrieve", methods=["POST"])
@login_required
def retrieve():
    u = database.get_user(_user())
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"success": False, "error": "请输入检索词"})
    max_level = u["max_level"] if u else 1
    hits = rag_engine.retrieve(question, max_level=max_level,
                               category=data.get("category") or None,
                               top_k=int(data.get("top_k") or 5))
    return jsonify({"success": True, "hits": hits})


@app.route("/api/qa/<int:qid>/feedback", methods=["POST"])
@login_required
def feedback(qid):
    data = request.get_json(force=True)
    rating = int(data.get("rating") or 0)
    database.rate_qa(qid, rating)
    return jsonify({"success": True})


@app.route("/api/qa/history")
@admin_required
def qa_history():
    return jsonify({"success": True, "logs": database.list_qa(limit=30)})


# ---------------- 知识图谱 ----------------
@app.route("/api/graph")
@login_required
def graph():
    u = database.get_user(_user())
    max_level = u["max_level"] if u else 1
    g = knowledge_graph.build_graph(max_level=max_level)
    return jsonify({"success": True, **g})


# ---------------- 审计与用户 ----------------
@app.route("/api/audit")
@admin_required
def audit():
    return jsonify({"success": True, "logs": database.list_audit(limit=100)})


@app.route("/api/users", methods=["GET"])
@admin_required
def users():
    return jsonify({"success": True, "users": database.list_users()})


@app.route("/api/users", methods=["POST"])
@admin_required
def add_user_api():
    data = request.get_json(force=True)
    ok = database.add_user(data.get("username", ""), data.get("password", ""),
                           data.get("role", "user"), data.get("dept", ""))
    if not ok:
        return jsonify({"success": False, "error": "用户名已存在"})
    database.log_audit(_user(), "新增用户", data.get("username", ""), "", _client_ip())
    return jsonify({"success": True})


@app.route("/api/users/<int:uid>", methods=["PUT"])
@admin_required
def update_user_api(uid):
    data = request.get_json(force=True)
    database.update_user(uid, data.get("role", "user"), data.get("dept", ""))
    return jsonify({"success": True})


@app.route("/api/users/<int:uid>", methods=["DELETE"])
@admin_required
def delete_user_api(uid):
    u = database.get_user(_user())
    target = database.get_user_by_id(uid) if hasattr(database, "get_user_by_id") else None
    if u and u["id"] == uid:
        return jsonify({"success": False, "error": "不能删除当前登录账号"})
    database.delete_user(uid)
    return jsonify({"success": True})


# ---------------- 系统状态 ----------------
@app.route("/api/system")
@login_required
def system_status():
    ready, models = embedder.is_ollama_ready()
    llm_ok = any(config.LLM_MODEL in m or config.LLM_MODEL.split(":")[0] in m for m in models) if ready else False
    return jsonify({
        "success": True,
        "mode": config.MODE,
        "ollama_ready": ready,
        "ollama_host": config.OLLAMA_HOST,
        "llm_model": config.LLM_MODEL,
        "llm_ready": llm_ok,
        "embed_model": config.EMBED_MODEL,
        "models": models if ready else [],
    })


@app.route("/api/system/mode", methods=["POST"])
@admin_required
def set_mode():
    data = request.get_json(force=True)
    mode = data.get("mode")
    if mode not in ("simulate", "local"):
        return jsonify({"success": False, "error": "无效模式"})
    config.MODE = mode
    database.log_audit(_user(), "切换模式", mode, "", _client_ip())
    return jsonify({"success": True, "mode": mode})


@app.route("/api/system/llm-test", methods=["POST"])
@admin_required
def llm_test():
    """测试本地 DeepSeek 连通性"""
    from modules import llm_client
    t0 = time.time()
    try:
        ans, ms = llm_client._ollama_chat([
            {"role": "user", "content": "你好，请用一句话回复：本地模型已就绪。"}])
        return jsonify({"success": True, "reply": ans, "duration_ms": ms})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:200]})


# ---------------- 看板统计 ----------------
@app.route("/api/stats")
@login_required
def stats():
    u = database.get_user(_user())
    max_level = u["max_level"] if u else 1
    docs = database.list_documents(max_level=max_level)
    ready_docs = [d for d in docs if d["status"] == "ready"]
    cats = {}
    for d in ready_docs:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
    qas = database.list_qa(limit=100)
    rated = [q for q in qas if q["rating"] > 0]
    good = len([q for q in rated if q["rating"] >= 4])
    return jsonify({
        "success": True,
        "doc_total": len(docs),
        "doc_ready": len(ready_docs),
        "chunk_total": database.chunk_count(),
        "qa_total": database.qa_count(),
        "categories": [{"name": k, "value": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "satisfaction": round(good / len(rated) * 100) if rated else None,
        "recent_qa": qas[:8],
    })


# ---------------- 启动初始化 ----------------
def seed_documents():
    """首次启动：导入预置示例知识库"""
    if database.doc_count() > 0:
        return
    for fn in sorted(os.listdir(config.SEED_DIR)):
        path = os.path.join(config.SEED_DIR, fn)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(fn)[1].lower()
        if ext not in (".md", ".txt"):
            continue
        title = os.path.splitext(fn)[0]
        level = "机密" if "数据安全" in title else "内部"
        doc_id = database.add_document(title, fn, path, "综合", level, "seed", "system")
        _process_document(doc_id)


if __name__ == "__main__":
    database.init_db()
    seed_documents()
    print("=" * 56)
    print("  湖企智库 · AI 本地知识库系统")
    print("  模式: %s   端口: %s" % (config.MODE, config.PORT))
    print("  访问: http://127.0.0.1:%s" % config.PORT)
    print("  演示账号: admin/admin123（管理员）  zhangwei/user123（普通）")
    print("=" * 56)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
