"""缺陷诊断知识图谱

构建 制造缺陷-成因-工序-处置-预防措施 关系网络
用于知识图谱可视化和缺陷知识查询
"""

import json


class DefectKnowledgeGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_index = {}
        self._build()

    def _add_node(self, node_type, name, properties=None):
        node_id = f"n{len(self.nodes)}"
        node = {
            "id": node_id,
            "type": node_type,
            "name": name,
            **(properties or {}),
        }
        self.nodes.append(node)
        self.node_index[(node_type, name)] = node_id
        return node_id

    def _get_or_add(self, node_type, name, properties=None):
        key = (node_type, name)
        if key in self.node_index:
            return self.node_index[key]
        return self._add_node(node_type, name, properties)

    def _add_edge(self, source_id, target_id, relation, properties=None):
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "relation": relation,
            **(properties or {}),
        })

    def _build(self):
        # ========== 缺陷类型节点 ==========
        defect_types = {
            "scratch":     ("划痕",   "minor",    "#FFA726"),
            "dent":        ("凹痕",   "minor",    "#FF7043"),
            "crack":       ("裂纹",   "critical", "#E53935"),
            "stain":       ("污渍",   "minor",    "#AB47BC"),
            "deformation": ("变形",   "major",    "#5C6BC0"),
            "missing_part":("缺件",   "critical", "#26A69A"),
            "misalign":    ("错装",   "major",    "#42A5F5"),
            "color_diff":  ("色差",   "minor",    "#9CCC65"),
            "burrs":       ("毛刺",   "minor",    "#FFCA28"),
            "oxidation":   ("氧化",   "major",    "#8D6E63"),
        }

        defect_ids = {}
        for code, (name, severity, color) in defect_types.items():
            nid = self._add_node("defect", name, {
                "code": code,
                "severity": severity,
                "color": color,
            })
            defect_ids[code] = nid

        # ========== 成因节点 ==========
        causes = [
            ("来料缺陷",     "material",   "来料检验不充分，原材料存在缺陷"),
            ("工艺参数不当",  "process",    "生产过程中温度/压力/时间等参数偏离标准"),
            ("设备异常",      "equipment",  "生产设备精度下降、磨损或故障"),
            ("工装夹具问题",  "tooling",    "夹具磨损、定位不准或设计不合理"),
            ("操作不当",      "operation",  "操作人员未按SOP执行或操作失误"),
            ("环境因素",      "environment","温湿度、灰尘、静电等环境条件不达标"),
            ("运输损伤",      "logistics",  "搬运、周转、运输过程中造成的损伤"),
            ("设计缺陷",      "design",     "产品设计存在先天不足，易产生缺陷"),
        ]
        cause_ids = {}
        for name, category, desc in causes:
            nid = self._add_node("cause", name, {"category": category, "description": desc})
            cause_ids[name] = nid

        # ========== 工序节点 ==========
        processes = [
            ("来料检验",   "IQC"),
            ("注塑成型",   "injection"),
            ("冲压成型",   "stamping"),
            ("机加工",     "machining"),
            ("表面处理",   "surface"),
            ("组装装配",   "assembly"),
            ("成品检验",   "FQC"),
            ("包装入库",   "packaging"),
        ]
        process_ids = {}
        for name, code in processes:
            nid = self._add_node("process", name, {"code": code})
            process_ids[name] = nid

        # ========== 处置方案节点 ==========
        dispositions = [
            ("接收放行",     "ACCEPT",    "low",     "产品合格，正常放行"),
            ("有条件接收",   "REVIEW",    "low",     "轻微缺陷在标准内，记录后放行"),
            ("返工修复",     "REWORK",    "medium",  "缺陷可修复，返工后重新检验"),
            ("MRB评审",      "REVIEW",    "medium",  "组织材料评审委员会决定处置方案"),
            ("报废",         "REJECT",    "urgent",  "严重缺陷无法修复，直接报废"),
            ("让步接收",     "CONCESSION","medium",  "经客户同意后接收"),
        ]
        disp_ids = {}
        for name, action, priority, desc in dispositions:
            nid = self._add_node("disposition", name, {
                "action": action,
                "priority": priority,
                "description": desc,
            })
            disp_ids[name] = nid

        # ========== 预防措施节点 ==========
        preventions = [
            ("加强来料检验",     "增加来料抽检比例和项目"),
            ("工艺参数监控",     "安装实时监控系统，参数超限自动报警"),
            ("设备定期维保",     "制定预防性维护计划，定期校准精度"),
            ("工装定期检查",     "每班次检查工装状态，及时更换磨损件"),
            ("操作培训",         "定期培训操作人员，持证上岗"),
            ("环境改善",         "控制车间温湿度，增加防尘除静电措施"),
            ("包装防护优化",     "改进周转箱和包装材料，增加缓冲"),
            ("设计改进",         "优化产品设计，减少应力集中和易损部位"),
            ("防呆设计",         "增加防错装置，防止操作遗漏或错误"),
            ("SPC统计控制",      "实施统计过程控制，及时发现过程异常"),
        ]
        prev_ids = {}
        for name, desc in preventions:
            nid = self._add_node("prevention", name, {"description": desc})
            prev_ids[name] = nid

        # ========== 检测方法节点 ==========
        methods = [
            ("AI视觉检测",  "YOLO深度学习模型自动检测"),
            ("人工目检",     "检验员目视检查"),
            ("尺寸测量",     "卡尺/三坐标测量"),
            ("光学检测",     "AOI自动光学检测"),
            ("无损检测",     "X-ray/超声波检测"),
            ("色差仪检测",   "分光测色仪测量色差"),
        ]
        method_ids = {}
        for name, desc in methods:
            nid = self._add_node("method", name, {"description": desc})
            method_ids[name] = nid

        # ========== 关系连接 ==========
        # 缺陷 -> 成因
        defect_causes = {
            "scratch":     ["来料缺陷", "运输损伤", "工装夹具问题", "操作不当"],
            "dent":        ["运输损伤", "操作不当", "设备异常"],
            "crack":       ["来料缺陷", "工艺参数不当", "设计缺陷"],
            "stain":       ["环境因素", "操作不当", "工艺参数不当"],
            "deformation": ["工艺参数不当", "设备异常", "来料缺陷"],
            "missing_part":["操作不当", "设备异常", "设计缺陷"],
            "misalign":    ["工装夹具问题", "设备异常", "操作不当"],
            "color_diff":  ["来料缺陷", "工艺参数不当", "环境因素"],
            "burrs":       ["设备异常", "工艺参数不当", "工装夹具问题"],
            "oxidation":   ["环境因素", "工艺参数不当", "来料缺陷"],
        }
        for code, cause_names in defect_causes.items():
            for cn in cause_names:
                if cn in cause_ids:
                    self._add_edge(defect_ids[code], cause_ids[cn], "caused_by")

        # 缺陷 -> 工序 (在哪个工序最常见)
        defect_processes = {
            "scratch":     ["来料检验", "冲压成型", "机加工", "组装装配"],
            "dent":        ["冲压成型", "运输损伤", "组装装配"],
            "crack":       ["注塑成型", "冲压成型", "机加工"],
            "stain":       ["表面处理", "组装装配", "成品检验"],
            "deformation": ["注塑成型", "冲压成型", "机加工"],
            "missing_part":["组装装配", "成品检验"],
            "misalign":    ["组装装配", "机加工"],
            "color_diff":  ["表面处理", "注塑成型", "成品检验"],
            "burrs":       ["冲压成型", "机加工", "注塑成型"],
            "oxidation":   ["表面处理", "机加工", "包装入库"],
        }
        for code, proc_names in defect_processes.items():
            for pn in proc_names:
                if pn in process_ids:
                    self._add_edge(defect_ids[code], process_ids[pn], "found_in")

        # 缺陷 -> 处置方案
        defect_dispositions = {
            "scratch":     ["有条件接收", "返工修复"],
            "dent":        ["有条件接收", "返工修复", "MRB评审"],
            "crack":       ["报废", "MRB评审"],
            "stain":       ["接收放行", "返工修复"],
            "deformation": ["返工修复", "报废", "MRB评审"],
            "missing_part":["返工修复", "MRB评审"],
            "misalign":    ["返工修复", "MRB评审"],
            "color_diff":  ["让步接收", "返工修复", "MRB评审"],
            "burrs":       ["返工修复", "有条件接收"],
            "oxidation":   ["返工修复", "报废", "MRB评审"],
        }
        for code, disp_names in defect_dispositions.items():
            for dn in disp_names:
                if dn in disp_ids:
                    self._add_edge(defect_ids[code], disp_ids[dn], "disposed_as")

        # 缺陷 -> 预防措施
        defect_preventions = {
            "scratch":     ["加强来料检验", "包装防护优化", "工装定期检查"],
            "dent":        ["包装防护优化", "操作培训", "设备定期维保"],
            "crack":       ["加强来料检验", "工艺参数监控", "设计改进"],
            "stain":       ["环境改善", "操作培训", "工艺参数监控"],
            "deformation": ["工艺参数监控", "设备定期维保", "加强来料检验"],
            "missing_part":["防呆设计", "操作培训", "设备定期维保"],
            "misalign":    ["工装定期检查", "设备定期维保", "操作培训"],
            "color_diff":  ["加强来料检验", "工艺参数监控", "环境改善"],
            "burrs":       ["设备定期维保", "工艺参数监控", "工装定期检查"],
            "oxidation":   ["环境改善", "工艺参数监控", "加强来料检验"],
        }
        for code, prev_names in defect_preventions.items():
            for pn in prev_names:
                if pn in prev_ids:
                    self._add_edge(defect_ids[code], prev_ids[pn], "prevented_by")

        # 缺陷 -> 检测方法
        defect_methods = {
            "scratch":     ["AI视觉检测", "人工目检"],
            "dent":        ["AI视觉检测", "人工目检"],
            "crack":       ["AI视觉检测", "无损检测", "人工目检"],
            "stain":       ["AI视觉检测", "人工目检"],
            "deformation": ["AI视觉检测", "尺寸测量"],
            "missing_part":["AI视觉检测", "人工目检"],
            "misalign":    ["AI视觉检测", "尺寸测量", "人工目检"],
            "color_diff":  ["色差仪检测", "AI视觉检测"],
            "burrs":       ["AI视觉检测", "人工目检", "光学检测"],
            "oxidation":   ["AI视觉检测", "人工目检"],
        }
        for code, method_names in defect_methods.items():
            for mn in method_names:
                if mn in method_ids:
                    self._add_edge(defect_ids[code], method_ids[mn], "detected_by")

        # 成因 -> 预防措施
        cause_preventions = {
            "来料缺陷":     ["加强来料检验"],
            "工艺参数不当":  ["工艺参数监控", "SPC统计控制"],
            "设备异常":      ["设备定期维保"],
            "工装夹具问题":  ["工装定期检查"],
            "操作不当":      ["操作培训", "防呆设计"],
            "环境因素":      ["环境改善"],
            "运输损伤":      ["包装防护优化"],
            "设计缺陷":      ["设计改进"],
        }
        for cn, prev_names in cause_preventions.items():
            for pn in prev_names:
                if cn in cause_ids and pn in prev_ids:
                    self._add_edge(cause_ids[cn], prev_ids[pn], "mitigated_by")

    def get_graph_data(self):
        """获取完整图谱数据"""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def get_node_detail(self, node_id):
        """获取节点详情及其关联节点"""
        node = None
        for n in self.nodes:
            if n["id"] == node_id:
                node = n
                break

        if not node:
            return None

        related = []
        for e in self.edges:
            if e["source"] == node_id:
                target = self._find_node(e["target"])
                if target:
                    related.append({
                        "node": target,
                        "relation": e["relation"],
                        "direction": "outgoing",
                    })
            elif e["target"] == node_id:
                source = self._find_node(e["source"])
                if source:
                    related.append({
                        "node": source,
                        "relation": e["relation"],
                        "direction": "incoming",
                    })

        return {
            "node": node,
            "related": related,
            "related_count": len(related),
        }

    def _find_node(self, node_id):
        for n in self.nodes:
            if n["id"] == node_id:
                return n
        return None
