# -*- coding: utf-8 -*-
"""湖企智库 - DeepSeek 本地大模型客户端
- local 模式：调用本机 Ollama 的 OpenAI 兼容接口（/v1/chat/completions）
- simulate 模式：基于检索片段的模板化回答（无需模型，用于演示）
"""
import json
import time
import urllib.request

import config


def _ollama_chat(messages, temperature=0.3):
    payload = json.dumps({
        "model": config.LLM_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        config.OLLAMA_HOST + "/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    ms = int((time.time() - t0) * 1000)
    return data["choices"][0]["message"]["content"].strip(), ms


def _simulate_answer(question, hits):
    """模拟模式：基于片段摘要生成有条理的回答，带引用标记 [1][2]"""
    if not hits:
        return ("抱歉，知识库中暂未检索到与「%s」直接相关的内容。\n\n"
                "您可以尝试：\n1. 换个关键词提问\n2. 确认知识库中是否已上传相关文档\n3. 联系管理员补充资料" % question)
    lines = ["根据企业本地知识库，为您梳理如下：\n"]
    for i, h in enumerate(hits[:3], 1):
        content = h["content"].replace("\n", " ")
        if len(content) > 180:
            content = content[:180] + "……"
        lines.append("[%d] %s" % (i, content))
    lines.append("\n以上内容分别引用自《%s》等文档（详见右侧引用来源），可点击原文核验。" % hits[0]["doc_title"])
    return "\n".join(lines)


def generate_answer(question, hits, mode=None):
    """生成回答。返回 (answer, mode, duration_ms)"""
    mode = mode or config.MODE
    if mode == "local":
        try:
            context = "\n\n".join(
                "【文档%d《%s》】%s" % (i + 1, h["doc_title"], h["content"][:800])
                for i, h in enumerate(hits))
            system = ("你是企业内部的智能知识库助手。请严格依据提供的知识库内容回答，"
                      "不得编造。回答结束时列出引用的文档编号。内容属于企业敏感资料，"
                      "不得泄露。")
            user = "知识库内容：\n%s\n\n问题：%s" % (context, question)
            ans, ms = _ollama_chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ])
            return ans, "local", ms
        except Exception:
            return _simulate_answer(question, hits), "simulate(fallback)", 0
    return _simulate_answer(question, hits), "simulate", 0
