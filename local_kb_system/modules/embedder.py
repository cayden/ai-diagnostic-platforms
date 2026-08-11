# -*- coding: utf-8 -*-
"""湖企智库 - Embedding 向量化
- simulate 模式：基于字符 bigram 的特征哈希向量（零依赖，开箱即用）
- local 模式：调用本机 Ollama 的 bge-m3（本地部署，数据不出域）
"""
import hashlib
import math
import re
import urllib.request
import json

import config


def _bigrams(text):
    """提取字符 bigram 特征（中文场景强于单字/分词）"""
    t = re.sub(r"\s+", "", text or "")
    grams = []
    prev = ""
    for ch in t:
        if ch.strip():
            if prev:
                grams.append(prev + ch)
            prev = ch
        else:
            prev = ""
    return grams


class SimEmbedder:
    """特征哈希向量：dim 维稀疏哈希，L2 归一化"""

    def __init__(self, dim=None):
        self.dim = dim or config.SIM_VECTOR_DIM

    def _hash(self, s):
        return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)

    def embed(self, text):
        vec = [0.0] * self.dim
        for g in set(_bigrams(text)):
            h = self._hash(g)
            idx = h % self.dim
            sign = 1.0 if (h >> 32) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class OllamaEmbedder:
    """调用本机 Ollama /api/embed 接口"""

    def __init__(self):
        self.model = config.EMBED_MODEL
        self.host = config.OLLAMA_HOST

    def embed(self, text):
        payload = json.dumps({"model": self.model, "input": [text[:2000]]}).encode()
        req = urllib.request.Request(self.host + "/api/embed", data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                emb = data["embeddings"][0]
                norm = math.sqrt(sum(v * v for v in emb)) or 1.0
                return [v / norm for v in emb]
        except Exception:
            return None


def get_embedder():
    if config.MODE == "local":
        return OllamaEmbedder()
    return SimEmbedder()


def is_ollama_ready():
    """探测本地 Ollama 是否在线"""
    try:
        with urllib.request.urlopen(config.OLLAMA_HOST + "/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
    except Exception:
        return False, []
