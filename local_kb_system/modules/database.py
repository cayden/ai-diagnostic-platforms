# -*- coding: utf-8 -*-
"""湖企智库 - SQLite 数据层：用户 / 文档 / 片段 / 问答 / 审计"""
import os
import sqlite3
import hashlib
import threading
from datetime import datetime

import config

_LOCK = threading.Lock()

LEVELS = {"公开": 0, "内部": 1, "机密": 2}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def init_db():
    with _LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            dept TEXT DEFAULT '',
            max_level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT DEFAULT '',
            filepath TEXT DEFAULT '',
            category TEXT DEFAULT '综合',
            level TEXT DEFAULT '公开',
            source TEXT DEFAULT 'upload',
            chunk_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error TEXT DEFAULT '',
            created_by TEXT DEFAULT 'system',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            seq INTEGER DEFAULT 0,
            content TEXT NOT NULL,
            level TEXT DEFAULT '公开',
            token_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS qa_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT DEFAULT '',
            question TEXT DEFAULT '',
            answer TEXT DEFAULT '',
            sources TEXT DEFAULT '',
            mode TEXT DEFAULT '',
            duration_ms INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT DEFAULT '',
            action TEXT DEFAULT '',
            target TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        );
        """)
        conn.commit()
        # 种子用户
        for u in config.DEMO_USERS:
            ph = hashlib.sha256((u["password"] + "kb-salt").encode()).hexdigest()
            max_level = 2 if u["role"] == "admin" else 1
            cur.execute("SELECT id FROM users WHERE username=?", (u["username"],))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users(username,password_hash,role,dept,max_level,created_at) VALUES(?,?,?,?,?,?)",
                    (u["username"], ph, u["role"], u["dept"], max_level, _now()))
        conn.commit()
        conn.close()


# ---------------- 用户 ----------------
def auth_user(username, password):
    ph = hashlib.sha256((password + "kb-salt").encode()).hexdigest()
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                       (username, ph)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT id,username,role,dept,max_level,created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user(username, password, role, dept):
    ph = hashlib.sha256((password + "kb-salt").encode()).hexdigest()
    max_level = 2 if role == "admin" else 1
    conn = get_conn()
    try:
        conn.execute("INSERT INTO users(username,password_hash,role,dept,max_level,created_at) VALUES(?,?,?,?,?,?)",
                     (username, ph, role, dept, max_level, _now()))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def update_user(uid, role, dept):
    max_level = 2 if role == "admin" else 1
    conn = get_conn()
    conn.execute("UPDATE users SET role=?, dept=?, max_level=? WHERE id=?", (role, dept, max_level, uid))
    conn.commit()
    conn.close()


def delete_user(uid):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()


# ---------------- 文档 ----------------
def add_document(title, filename, filepath, category, level, source, created_by):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO documents(title,filename,filepath,category,level,source,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (title, filename, filepath, category, level, source, "pending", created_by, _now(), _now()))
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def get_document(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_documents(max_level=2):
    """按用户权限过滤：level 数值 <= max_level 才可见。默认管理员可见全部"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows if LEVELS.get(dict(r)["level"], 2) <= max_level]


def update_doc_status(doc_id, status, chunk_count=None, error=""):
    conn = get_conn()
    if chunk_count is None:
        conn.execute("UPDATE documents SET status=?, error=?, updated_at=? WHERE id=?",
                     (status, error, _now(), doc_id))
    else:
        conn.execute("UPDATE documents SET status=?, chunk_count=?, error=?, updated_at=? WHERE id=?",
                     (status, chunk_count, error, _now(), doc_id))
    conn.commit()
    conn.close()


def delete_document(doc_id):
    conn = get_conn()
    conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()


def doc_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM documents WHERE status='ready'").fetchone()["c"]
    conn.close()
    return n


# ---------------- 片段 ----------------
def replace_chunks(doc_id, chunks):
    """chunks: list of (seq, content, level, token_count)"""
    conn = get_conn()
    conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    conn.executemany(
        "INSERT INTO chunks(doc_id,seq,content,level,token_count) VALUES(?,?,?,?,?)",
        [(doc_id, s, c, lv, tc) for s, c, lv, tc in chunks])
    conn.commit()
    conn.close()


def all_chunks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chunks ORDER BY doc_id, seq").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def chunk_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
    conn.close()
    return n


# ---------------- 问答 / 审计 ----------------
def log_qa(username, question, answer, sources, mode, duration_ms):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO qa_logs(username,question,answer,sources,mode,duration_ms,created_at) VALUES(?,?,?,?,?,?,?)",
        (username, question, answer, sources, mode, duration_ms, _now()))
    conn.commit()
    qid = cur.lastrowid
    conn.close()
    return qid


def rate_qa(qid, rating):
    conn = get_conn()
    conn.execute("UPDATE qa_logs SET rating=? WHERE id=?", (rating, qid))
    conn.commit()
    conn.close()


def list_qa(limit=30):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM qa_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def qa_count():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM qa_logs").fetchone()["c"]
    conn.close()
    return n


def log_audit(username, action, target="", detail="", ip=""):
    conn = get_conn()
    conn.execute("INSERT INTO audit_logs(username,action,target,detail,ip,created_at) VALUES(?,?,?,?,?,?)",
                 (username, action, target, detail, ip, _now()))
    conn.commit()
    conn.close()


def list_audit(limit=100):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
