# -*- coding: utf-8 -*-
"""湖企智库 - 文本分块"""
import re
import config


def split_text(text, chunk_size=None, overlap=None):
    """按段落聚合为近似 chunk_size 的块，支持重叠。返回 [(content, token_count)]"""
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    if not text or not text.strip():
        return []
    # 清洗：合并多余空行
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # 按段落切分（空行/换行分隔）
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    # 过长的段落按句子/字符再切
    chunks, buf = [], ""
    for p in paras:
        if len(p) > chunk_size * 1.5:
            for i in range(0, len(p), chunk_size - overlap):
                seg = p[i:i + chunk_size]
                if seg.strip():
                    chunks.append(seg.strip())
            continue
        if len(buf) + len(p) + 1 <= chunk_size:
            buf = (buf + "\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            # 重叠：保留上一块尾部
            tail = buf[-(overlap):] if buf else ""
            buf = (tail + "\n" + p).strip()
    if buf:
        chunks.append(buf)
    return [(c, len(c)) for c in chunks if c]
