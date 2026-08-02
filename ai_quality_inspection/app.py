"""AI质检系统 - Flask主应用"""

import os
import json
import time
import uuid
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

from config import Config
from modules.yolo_detector import YoloDetector
from modules.llm_analyzer import LlmAnalyzer
from modules.database import Database
from modules.knowledge_graph import DefectKnowledgeGraph

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
CORS(app)

# ========== 模块初始化 ==========
detector = YoloDetector(Config)
analyzer = LlmAnalyzer(Config)
db = Database(Config.DB_PATH)
kg = DefectKnowledgeGraph()


# ========== 前端页面 ==========
@app.route("/")
def index():
    return render_template("index.html")


# ========== 系统状态 ==========
@app.route("/api/system/status", methods=["GET"])
def system_status():
    return jsonify({
        "success": True,
        "system": "AI质检视觉检测平台",
        "version": "1.0.0",
        "detection_mode": Config.DETECTION_MODE,
        "llm_mode": Config.LLM_MODE,
        "defect_classes": len(Config.DEFECT_CLASSES),
        "upload_dir": Config.UPLOAD_DIR,
        "timestamp": datetime.now().isoformat(),
    })


# ========== 缺陷类型列表 ==========
@app.route("/api/defect-classes", methods=["GET"])
def get_defect_classes():
    classes = []
    for cid, code, name, severity, color in Config.DEFECT_CLASSES:
        sev = Config.SEVERITY_LEVELS.get(severity, {})
        classes.append({
            "class_id": cid,
            "code": code,
            "name": name,
            "severity": severity,
            "severity_label": sev.get("label", ""),
            "severity_score": sev.get("score", 0),
            "color": color,
        })
    return jsonify({"success": True, "classes": classes})


# ========== 图片上传 + YOLO检测 + LLM分析 ==========
@app.route("/api/inspect", methods=["POST"])
def inspect_image():
    t0 = time.time()

    if "image" not in request.files:
        return jsonify({"success": False, "error": "未上传图片"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名为空"}), 400

    # 保存图片
    ext = os.path.splitext(file.filename)[1] or ".png"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(Config.UPLOAD_DIR, saved_name)
    file.save(save_path)

    # 读取表单参数
    product_name = request.form.get("product_name", Config.DEFAULT_PRODUCT)
    product_code = request.form.get("product_code", "")
    batch_no = request.form.get("batch_no", f"BATCH-{datetime.now().strftime('%Y%m%d')}")
    line = request.form.get("line", Config.DEFAULT_LINE)
    inspector = request.form.get("inspector", Config.DEFAULT_INSPECTOR)
    process = request.form.get("process", "成品检验")
    notes = request.form.get("notes", "")

    # ---------- YOLO 检测 ----------
    t1 = time.time()
    detection = detector.detect(save_path)
    detection_time = round(time.time() - t1, 3)

    # ---------- 质量判定 ----------
    quality_result = _judge_quality(detection)

    # ---------- LLM 分析 ----------
    t2 = time.time()
    analysis = analyzer.analyze_defects(
        image_name=saved_name,
        detections=detection["detections"],
        quality_result=quality_result,
        product_name=product_name,
        process=process,
    )
    analysis_time = round(time.time() - t2, 3)

    total_time = round(time.time() - t0, 3)

    # ---------- 组装记录 ----------
    record_id = f"INS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    record = {
        "record_id": record_id,
        "product_name": product_name,
        "product_code": product_code,
        "batch_no": batch_no,
        "line": line,
        "inspector": inspector,
        "process": process,
        "notes": notes,
        "image_filename": saved_name,
        "image_path": save_path,
        "detection_result": detection,
        "quality_result": quality_result,
        "analysis_result": analysis,
        "detection_time": detection_time,
        "analysis_time": analysis_time,
        "total_time": total_time,
        "created_at": datetime.now().isoformat(),
    }

    db.add_record(record)

    return jsonify({
        "success": True,
        "record_id": record_id,
        "image_url": f"/api/image/{saved_name}",
        "detection": detection,
        "quality_result": quality_result,
        "analysis": analysis,
        "timing": {
            "detection": detection_time,
            "analysis": analysis_time,
            "total": total_time,
        },
    })


def _judge_quality(detection):
    """根据检测结果判定合格/不合格"""
    defects = detection.get("detections", [])
    counts = {"critical": 0, "major": 0, "minor": 0}
    for d in defects:
        sev = d.get("severity", "minor")
        counts[sev] = counts.get(sev, 0) + 1

    passed = (
        counts["critical"] <= Config.PASS_CRITERIA["critical_max"]
        and counts["major"] <= Config.PASS_CRITERIA["major_max"]
        and counts["minor"] <= Config.PASS_CRITERIA["minor_max"]
    )

    # 缺陷分数
    score = (
        counts["critical"] * Config.SEVERITY_LEVELS["critical"]["score"]
        + counts["major"] * Config.SEVERITY_LEVELS["major"]["score"]
        + counts["minor"] * Config.SEVERITY_LEVELS["minor"]["score"]
    )

    return {
        "verdict": "PASS" if passed else "FAIL",
        "verdict_label": "合格" if passed else "不合格",
        "defect_counts": counts,
        "total_defects": len(defects),
        "defect_score": score,
        "criteria": Config.PASS_CRITERIA,
    }


# ========== 获取图片 ==========
@app.route("/api/image/<filename>", methods=["GET"])
def get_image(filename):
    return send_from_directory(Config.UPLOAD_DIR, filename)


# ========== 历史检测记录 ==========
@app.route("/api/history", methods=["GET"])
def get_history():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    search = request.args.get("search", "")
    verdict = request.args.get("verdict", "")
    batch_no = request.args.get("batch_no", "")

    result = db.get_records(page, per_page, search, verdict, batch_no)
    return jsonify(result)


# ========== 检测记录详情 ==========
@app.route("/api/history/<record_id>", methods=["GET"])
def get_record_detail(record_id):
    record = db.get_record(record_id)
    if not record:
        return jsonify({"success": False, "error": "记录不存在"}), 404
    return jsonify({"success": True, "record": record})


# ========== 删除检测记录 ==========
@app.route("/api/history/<record_id>", methods=["DELETE"])
def delete_record(record_id):
    ok = db.delete_record(record_id)
    return jsonify({"success": ok})


# ========== 质量统计 ==========
@app.route("/api/stats/overview", methods=["GET"])
def get_stats_overview():
    days = int(request.args.get("days", 7))
    stats = db.get_stats(days)
    return jsonify({"success": True, "stats": stats})


# ========== 缺陷类型分布 ==========
@app.route("/api/stats/defect-distribution", methods=["GET"])
def get_defect_distribution():
    days = int(request.args.get("days", 7))
    dist = db.get_defect_distribution(days)
    return jsonify({"success": True, "distribution": dist})


# ========== SPC 统计过程控制 ==========
@app.route("/api/stats/spc", methods=["GET"])
def get_spc():
    days = int(request.args.get("days", 7))
    spc = db.get_spc_data(days)
    return jsonify({"success": True, "spc": spc})


# ========== 趋势分析 ==========
@app.route("/api/stats/trend", methods=["GET"])
def get_trend():
    days = int(request.args.get("days", 7))
    trend = db.get_trend(days)
    return jsonify({"success": True, "trend": trend})


# ========== AI 问答助手 ==========
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    context = data.get("context", "")

    result = analyzer.chat(message, context)
    db.add_chat_record(message, result)

    return jsonify({"success": True, "response": result})


# ========== 聊天历史 ==========
@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    records = db.get_chat_history(limit=50)
    return jsonify({"success": True, "history": records})


# ========== 知识图谱 ==========
@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    data = kg.get_graph_data()
    data["success"] = True
    return jsonify(data)


# ========== 知识图谱节点详情 ==========
@app.route("/api/knowledge-graph/node/<node_id>", methods=["GET"])
def get_kg_node(node_id):
    detail = kg.get_node_detail(node_id)
    if detail:
        resp = {"success": True}
        resp.update(detail)
        return jsonify(resp)
    return jsonify({"success": False, "error": "节点不存在"}), 404


# ========== 系统配置更新 ==========
@app.route("/api/system/config", methods=["POST"])
def update_config():
    data = request.get_json()
    updated = []

    if "llm_api_key" in data and data["llm_api_key"]:
        Config.LLM_API_KEY = data["llm_api_key"]
        Config.LLM_MODE = "api"
        analyzer.api_key = data["llm_api_key"]
        analyzer.mode = "api"
        updated.append("llm_api_key")

    if "llm_mode" in data:
        Config.LLM_MODE = data["llm_mode"]
        analyzer.mode = data["llm_mode"]
        updated.append("llm_mode")

    if "detection_mode" in data:
        Config.DETECTION_MODE = data["detection_mode"]
        detector.mode = data["detection_mode"]
        updated.append("detection_mode")

    if "conf_threshold" in data:
        Config.YOLO_CONF_THRESHOLD = float(data["conf_threshold"])
        detector.conf_threshold = float(data["conf_threshold"])
        updated.append("conf_threshold")

    return jsonify({"success": True, "updated": updated})


# ========== 批量检测 ==========
@app.route("/api/inspect/batch", methods=["POST"])
def batch_inspect():
    """批量上传多张图片同时检测"""
    files = request.files.getlist("images")
    if not files:
        return jsonify({"success": False, "error": "未上传图片"}), 400

    batch_no = request.form.get("batch_no", f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    results = []

    for file in files:
        ext = os.path.splitext(file.filename)[1] or ".png"
        saved_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(Config.UPLOAD_DIR, saved_name)
        file.save(save_path)

        detection = detector.detect(save_path)
        quality = _judge_quality(detection)

        record_id = f"INS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        record = {
            "record_id": record_id,
            "product_name": request.form.get("product_name", Config.DEFAULT_PRODUCT),
            "product_code": request.form.get("product_code", ""),
            "batch_no": batch_no,
            "line": request.form.get("line", Config.DEFAULT_LINE),
            "inspector": request.form.get("inspector", Config.DEFAULT_INSPECTOR),
            "process": request.form.get("process", "成品检验"),
            "notes": "",
            "image_filename": saved_name,
            "image_path": save_path,
            "detection_result": detection,
            "quality_result": quality,
            "analysis_result": {},
            "detection_time": 0,
            "analysis_time": 0,
            "total_time": 0,
            "created_at": datetime.now().isoformat(),
        }
        db.add_record(record)

        results.append({
            "record_id": record_id,
            "filename": file.filename,
            "verdict": quality["verdict"],
            "verdict_label": quality["verdict_label"],
            "defect_count": quality["total_defects"],
            "image_url": f"/api/image/{saved_name}",
        })

    # 批次汇总
    total = len(results)
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = total - passed

    return jsonify({
        "success": True,
        "batch_no": batch_no,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "results": results,
    })


if __name__ == "__main__":
    print(f"[AI质检系统] 启动中... 端口 {Config.PORT}")
    print(f"[AI质检系统] 检测模式: {Config.DETECTION_MODE}")
    print(f"[AI质检系统] LLM模式: {Config.LLM_MODE}")
    print(f"[AI质检系统] 缺陷类型: {len(Config.DEFECT_CLASSES)} 类")
    print(f"[AI质检系统] 访问地址: http://127.0.0.1:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
