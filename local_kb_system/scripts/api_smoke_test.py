#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""湖企智库 全量 API 冒烟测试 (v2 - cookie 会话版)
覆盖: 登录/统计/文档列表/问答/检索/图谱/审计/用户/系统/上传/反馈/登出
"""
import json
import sys
import uuid
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:5102"
passed, failed = 0, 0


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def req(self, method, path, data=None, multipart=None):
        """multipart: list of ("file", fname, ctype, bytes) 或 ("field", value)"""
        url = BASE + path
        headers = {}
        body = None
        if multipart:
            boundary = "----kb7f" + uuid.uuid4().hex
            chunks = []
            for item in multipart:
                if len(item) == 4 and isinstance(item[3], bytes):
                    name, fname, ctype, payload = item
                    chunks.append(
                        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fname}\"\r\n"
                        f"Content-Type: {ctype}\r\n\r\n".encode() + payload + b"\r\n"
                    )
                else:
                    name, value = item
                    chunks.append(
                        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
                    )
            chunks.append(f"--{boundary}--\r\n".encode())
            body = b"".join(chunks)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        r = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = self.opener.open(r, timeout=20)
            raw = resp.read().decode("utf-8", "replace")
            code = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            code = e.code
        except Exception as e:
            return {"_raw": "", "_err": str(e), "_code": 0}
        try:
            return {"_raw": raw, "_err": None, "_code": code, **json.loads(raw)}
        except Exception:
            return {"_raw": raw, "_err": None, "_code": code}


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}  <- {detail}")
    return cond


admin = Client()
user = Client()

print("=" * 60)
print("湖企智库 · 全量 API 冒烟测试 (cookie 会话)")
print("=" * 60)

# 1. 认证
r = admin.req("POST", "/api/login", {"username": "admin", "password": "admin123"})
check("1. 管理员登录", r.get("success") is True, f"{r.get('error')} / {r.get('_raw','')[:100]}")
r = user.req("POST", "/api/login", {"username": "zhangwei", "password": "user123"})
check("2. 普通用户登录", r.get("success") is True, f"{r.get('error')} / {r.get('_raw','')[:100]}")
r = admin.req("POST", "/api/login", {"username": "admin", "password": "wrong"})
check("3. 错误密码拒绝", r.get("success") is False, r.get("_raw", "")[:100])
r = admin.req("POST", "/api/login", {"username": "ghost", "password": "x"})
check("4. 不存在用户拒绝", r.get("success") is False, r.get("_raw", "")[:100])
r = admin.req("GET", "/api/me")
check("4b. /api/me 返回用户信息", r.get("success") is True and r.get("user", {}).get("username") == "admin",
      r.get("_raw", "")[:120])

# 2. 工作台统计
r = admin.req("GET", "/api/stats")
check("5. 工作台统计(管理员)", r.get("success") is True and isinstance(r.get("doc_total"), int) and r.get("doc_total") >= 5,
      json.dumps(r, ensure_ascii=False)[:200])

# 3. 文档列表 + 权限过滤
r = admin.req("GET", "/api/documents")
docs = r.get("documents") or []
admin_titles = [x.get("title") for x in docs if isinstance(x, dict)]
has_all_seed = all(k in admin_titles for k in ["数据安全管理规定", "客户投诉处理流程", "员工差旅与报销管理制度", "产品质量检验标准", "SMT贴片生产工艺规范"])
check("6. 管理员看到全部种子文档", r.get("success") is True and has_all_seed,
      f"got {len(admin_titles)}: {admin_titles}")

r = user.req("GET", "/api/documents")
udocs = r.get("documents") or []
user_titles = [x.get("title") for x in udocs if isinstance(x, dict)]
secret_visible = any("数据安全" in t for t in user_titles)
check("7. 普通用户看不到机密文档", r.get("success") is True and not secret_visible,
      f"可见 {len(user_titles)} 篇: {user_titles}")

# 4. RAG 问答（检索排序正确性）
qa_cases = [
    "出差住宿费标准是什么？",
    "客户投诉处理时限是多久？",
    "回流焊的温度曲线要求？",
    "发票报销需要什么材料？",
    "数据安全管理有哪些要求？",
]
for i, q in enumerate(qa_cases):
    r = admin.req("POST", "/api/chat", {"question": q})
    ans = r.get("answer") or ""
    src = r.get("sources") or []
    ok = r.get("success") is True and len(ans) > 10 and len(src) >= 1
    src_names = ",".join((s.get("content") or s.get("title") or "?")[:14] for s in src[:2])
    print(f"[{'PASS' if ok else 'FAIL'}] 8.{i+1} 问答「{q[:16]}」 来源={src_names}")
    if ok:
        passed += 1
    else:
        failed += 1

# 5. 检索接口
r = admin.req("POST", "/api/retrieve", {"question": "报销流程", "top_k": 3})
hits = r.get("hits") or []
check("9. 语义检索 top3", r.get("success") is True and len(hits) == 3,
      json.dumps(hits, ensure_ascii=False)[:200])

# 6. 知识图谱
r = admin.req("GET", "/api/graph")
g = r
check("10. 知识图谱 节点+边", r.get("success") is True and len(g.get("nodes", [])) >= 5 and len(g.get("edges", [])) >= 3,
      f"nodes={len(g.get('nodes', []))} edges={len(g.get('edges', []))}")

# 7. 审计日志
r = admin.req("GET", "/api/audit")
logs = r.get("logs") or []
check("11. 审计日志有记录", r.get("success") is True and len(logs) >= 5, f"got {len(logs)}")

# 8. 用户管理
r = admin.req("GET", "/api/users")
users = r.get("users") or []
check("12. 用户列表", r.get("success") is True and len(users) >= 2, f"got {len(users)}")

r = admin.req("POST", "/api/users", {"username": "testuser", "password": "test123", "role": "user", "dept": "测试"})
check("13. 新增用户", r.get("success") is True, f"{r.get('error')} / {r.get('_raw','')[:120]}")
r = admin.req("GET", "/api/users")
uid = None
for x in (r.get("users") or []):
    if x.get("username") == "testuser":
        uid = x.get("id")
        break
if uid:
    r = admin.req("PUT", f"/api/users/{uid}", {"role": "user", "dept": "信息中心"})
    check("14. 修改用户信息", r.get("success") is True, r.get("_raw", "")[:120])
    r = admin.req("DELETE", f"/api/users/{uid}")
    check("15. 删除用户", r.get("success") is True, r.get("_raw", "")[:120])
else:
    check("14. 修改用户信息", False, "no uid")
    check("15. 删除用户", False, "no uid")

r = user.req("POST", "/api/users", {"username": "hack", "password": "x", "role": "admin"})
check("16. 普通用户禁止管理用户", r.get("success") is False, r.get("_raw", "")[:120])

# 9. 系统状态 / 模式切换 / LLM 连通性
r = admin.req("GET", "/api/system")
check("17. 系统状态(模式/模型)", r.get("success") is True and "mode" in r and "llm_model" in r,
      json.dumps(r, ensure_ascii=False)[:200])

r = admin.req("POST", "/api/system/mode", {"mode": "simulate"})
check("18. 模式切换 simulate", r.get("success") is True, r.get("_raw", "")[:120])

r = admin.req("POST", "/api/system/llm-test", {})
# 本机未装 Ollama 时, 应优雅返回 success=False + 错误信息(而非崩溃)
check("19. LLM 连通性测试(优雅降级)", r.get("success") is False and bool(r.get("error")),
      json.dumps(r, ensure_ascii=False)[:200])

# 10. 文档上传 (multipart) + 删除
md_payload = "# 测试上传文档\n\n这是用于验证上传接口的临时文档内容，包含关键字：临时验证条目。\n".encode()
r = admin.req("POST", "/api/documents", multipart=[("file", "upload_test.md", "text/markdown", md_payload)])
check("20. 上传文档入库", r.get("success") is True, f"{r.get('error')} / {r.get('_raw','')[:150]}")
up_doc_id = r.get("doc_id")
if up_doc_id:
    r = admin.req("DELETE", f"/api/documents/{up_doc_id}")
    check("21. 删除上传文档", r.get("success") is True, r.get("_raw", "")[:120])

# 11. 问答历史 + 点赞反馈
r = admin.req("GET", "/api/qa/history")
hist = r.get("logs") or []
check("22. 问答历史", r.get("success") is True and len(hist) >= 1, f"got {len(hist)}")
qid = (hist[0] or {}).get("id") if hist else None
if qid:
    r = admin.req("POST", f"/api/qa/{qid}/feedback", {"helpful": True})
    check("23. 点赞反馈", r.get("success") is True, r.get("_raw", "")[:120])
else:
    check("23. 点赞反馈", False, "no qa id")

# 12. 登出
r = admin.req("POST", "/api/logout")
check("24. 登出", r.get("success") is True, r.get("_raw", "")[:120])

# 13. 未登录访问受保护接口
r = admin.req("GET", "/api/stats")
check("25. 登出后访问受限", r.get("success") is False, r.get("_raw", "")[:120])

# 14. 权限负向测试（普通用户越权应被拒绝）
r = user.req("GET", "/api/audit")
check("26. 普通用户禁止看审计日志", r.get("success") is False, r.get("_raw", "")[:120])
r = user.req("GET", "/api/qa/history")
check("27. 普通用户禁止看全量问答历史", r.get("success") is False, r.get("_raw", "")[:120])
md2 = "# 越权上传\n\n机密内容。\n".encode()
r = user.req("POST", "/api/documents",
             multipart=[("file", "secret.md", "text/markdown", md2), ("level", "机密")])
check("28. 普通用户禁止上传机密文档", r.get("success") is False, r.get("_raw", "")[:120])
r = user.req("DELETE", "/api/documents/1")
check("29. 普通用户禁止删除文档", r.get("success") is False, r.get("_raw", "")[:120])

print("=" * 60)
print(f"结果: {passed} 通过 / {failed} 失败 / 共 {passed + failed} 项")
print("=" * 60)
sys.exit(1 if failed else 0)
