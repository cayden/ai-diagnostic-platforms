# -*- coding: utf-8 -*-
"""湖企智库 - RAG 编排：检索 → 增强 → 生成 → 审计"""
import time

from modules import database, llm_client, vector_store


def query(question, username="guest", max_level=2, category=None):
    """完整 RAG 问答链路，返回结果字典"""
    t0 = time.time()
    hits = vector_store.search(question, top_k=5, max_level=max_level, category=category)
    if not hits:
        hits = vector_store.keyword_fallback(question, top_k=5, max_level=max_level)
    answer, mode, gen_ms = llm_client.generate_answer(question, hits)
    duration_ms = int((time.time() - t0) * 1000) + gen_ms
    sources = [{
        "doc_id": h["doc_id"],
        "doc_title": h["doc_title"],
        "category": h["category"],
        "level": h["level"],
        "seq": h["seq"],
        "content": h["content"],
        "score": h["score"],
    } for h in hits]

    # 审计留痕
    qa_id = database.log_qa(username, question, answer,
                    json_dumps(sources), mode, duration_ms)
    database.log_audit(username, "问答", question[:50], "mode=%s hits=%d" % (mode, len(hits)))
    return {
        "qa_id": qa_id,
        "answer": answer,
        "sources": sources,
        "mode": mode,
        "duration_ms": duration_ms,
        "hit_count": len(hits),
    }


def retrieve(question, max_level=2, category=None, top_k=5):
    """仅检索不生成，用于「检索测试」页"""
    hits = vector_store.search(question, top_k=top_k, max_level=max_level, category=category)
    if not hits:
        hits = vector_store.keyword_fallback(question, top_k=top_k, max_level=max_level)
    return hits


import json


def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)
