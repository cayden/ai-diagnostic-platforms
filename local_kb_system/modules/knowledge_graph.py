# -*- coding: utf-8 -*-
"""湖企智库 - 知识图谱：从文档/片段中抽取实体与关系
规则式抽取（词典 + 高频词 + 标题词），零依赖；也可扩展为 LLM 抽取。
节点类型：document（文档）/ topic（主题）/ entity（实体）
"""
import re
from collections import Counter

from modules import database

# 预置企业领域实体词典（可按企业扩充）
ENTITY_DICT = [
    "报销", "发票", "差旅", "住宿", "补贴", "审批", "请假", "加班", "考勤", "工资", "社保",
    "SMT", "回流焊", "锡膏", "贴片", "波峰焊", "AOI", "SPI", "温度曲线", "炉温", "PCB", "元器件",
    "客户投诉", "退货", "换货", "赔偿", "售后", "质保", "三包", "巡检", "抽检", "AQL", "不合格品",
    "数据安全", "数据分级", "机密", "审计", "权限", "账号", "外发", "备份", "病毒", "防火墙",
    "供应商", "采购", "合同", "招标", "报价", "付款", "对账", "库存", "盘点", "ERP",
    "安全", "消防", "应急预案", "培训", "操作规程", "劳保", "危化品", "职业病",
]

TOPIC_WORDS = ["制度", "流程", "规范", "标准", "办法", "规定", "指引", "指南", "手册", "须知"]


def _extract_entities(text):
    found = set()
    for w in ENTITY_DICT:
        if w in text:
            found.add(w)
    # 高频词补充
    words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
    cnt = Counter(words)
    for w, c in cnt.most_common(6):
        if c >= 3 and not re.match(r"^(我们|你们|他们|可以|需要|进行|相关|以及|或者|对于|通过|如果|因为|所以)$", w):
            found.add(w)
    return list(found)[:8]


def _topic_of(doc_title, content):
    for t in TOPIC_WORDS:
        if t in doc_title:
            return doc_title[:8]
    for t in ["报销", "差旅", "发票"]:
        if t in content:
            return "财务管理"
    for t in ["SMT", "锡膏", "炉温", "贴片", "PCB"]:
        if t in content:
            return "生产工艺"
    for t in ["投诉", "退货", "售后", "质保"]:
        if t in content:
            return "客户服务"
    for t in ["数据", "机密", "审计", "权限"]:
        if t in content:
            return "信息安全"
    for t in ["检验", "抽样", "AQL", "不合格"]:
        if t in content:
            return "质量管理"
    return "综合知识"


def build_graph(max_level=2):
    """构造 {nodes, edges}；按用户权限过滤文档"""
    docs = [d for d in database.list_documents(max_level=max_level) if d["status"] == "ready"]
    nodes, edges = [], []
    node_keys, edge_keys = set(), set()

    def add_node(nid, label, ntype, size=1):
        key = "%s:%s" % (ntype, nid)
        if key not in node_keys:
            node_keys.add(key)
            nodes.append({"id": key, "label": label, "type": ntype, "size": size})

    def add_edge(src, dst, rel, weight=1):
        key = "%s->%s" % (src, dst)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append({"source": src, "target": dst, "rel": rel, "weight": weight})

    for doc in docs:
        did = "doc:%d" % doc["id"]
        add_node(did, doc["title"], "document", size=2)
        chunks = [c for c in database.all_chunks() if c["doc_id"] == doc["id"]]
        text = "\n".join(c["content"] for c in chunks)[:4000]
        topic = _topic_of(doc["title"], text)
        tid = "topic:%s" % topic
        add_node(tid, topic, "topic", size=1.6)
        add_edge(did, tid, "属于")
        for ent in _extract_entities(text):
            eid = "ent:%s" % ent
            add_node(eid, ent, "entity")
            add_edge(did, eid, "涉及", weight=2)

    return {"nodes": nodes, "edges": edges}
