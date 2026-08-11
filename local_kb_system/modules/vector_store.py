# -*- coding: utf-8 -*-
"""湖企智库 - 向量存储与检索（余弦相似度 + 权限过滤）"""
import math

from modules import database
from modules.embedder import SimEmbedder, OllamaEmbedder

_embed_cache = {}


def _get_embedder():
    from modules import embedder
    return embedder.get_embedder()


def _embed_text(text):
    """带缓存取向量；本地模式失败时自动回退模拟向量"""
    key = text[:80]
    if key in _embed_cache:
        return _embed_cache[key]
    emb = _get_embedder().embed(text)
    if emb is None:
        emb = SimEmbedder().embed(text)
    _embed_cache[key] = emb
    return emb


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def index_document(doc_id):
    """对文档的所有片段做向量化并缓存（惰性，检索时实时计算向量）"""
    chunks = database.all_chunks()
    # 预热缓存
    for c in chunks:
        if c["doc_id"] == doc_id:
            _embed_text(c["content"])
    return True


def _kw_tokens(text):
    """中文字符 bigram 集合 + 英文/数字词集合（避免整句被贪婪匹配成单 token）"""
    import re
    t = re.sub(r"\s+", "", text or "")
    grams = {t[i:i + 2] for i in range(len(t) - 1)} if len(t) >= 2 else set()
    en = set(re.findall(r"[a-zA-Z0-9]{2,}", text or ""))
    return grams | en


def search(query, top_k=5, max_level=2, category=None):
    """向量相似度 + 关键词重叠 融合排序（提升中文短问句检索精度）"""
    query_vec = _embed_text(query)
    q_words = _kw_tokens(query)
    results = []
    chunks = database.all_chunks()
    for c in chunks:
        if c["level"] and database.LEVELS.get(c["level"], 1) > max_level:
            continue
        vec = _embed_text(c["content"])
        cos = _cosine(query_vec, vec)
        c_words = _kw_tokens(c["content"])
        kw = len(q_words & c_words) / max(1, len(q_words)) if q_words else 0.0
        score = 0.55 * cos + 0.45 * kw
        if score <= 0.001:
            continue
        doc = database.get_document(c["doc_id"])
        if not doc or doc["status"] != "ready":
            continue
        if category and doc["category"] != category:
            continue
        results.append({
            "doc_id": c["doc_id"],
            "doc_title": doc["title"],
            "category": doc["category"],
            "level": c["level"],
            "seq": c["seq"],
            "content": c["content"],
            "score": round(float(score), 4),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def keyword_fallback(query, top_k=5, max_level=2):
    """关键词重叠度兜底检索（本地模式 embedding 失败时）"""
    import re
    q = set(re.findall(r"[\u4e00-\u9fa5]{2,}", query))
    if not q:
        return []
    results = []
    for c in database.all_chunks():
        if database.LEVELS.get(c["level"], 1) > max_level:
            continue
        doc = database.get_document(c["doc_id"])
        if not doc or doc["status"] != "ready":
            continue
        words = set(re.findall(r"[\u4e00-\u9fa5]{2,}", c["content"]))
        overlap = len(q & words)
        if overlap >= 2:
            results.append({
                "doc_id": c["doc_id"], "doc_title": doc["title"],
                "category": doc["category"], "level": c["level"], "seq": c["seq"],
                "content": c["content"],
                "score": round(overlap / len(q), 4),
            })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]
