"""
故障诊断知识图谱
设备故障-征兆-原因-处置方案的关系网络
"""


class FaultKnowledgeGraph:
    """故障知识图谱"""

    def __init__(self):
        self.nodes = []
        self.edges = []
        self._build_graph()

    def _build_graph(self):
        # 节点类型：category(分类), fault(故障), symptom(征兆), cause(原因),
        #           action(处置), equipment(设备类型), sensor(传感器)

        node_id = 0

        def add_node(node_type, name, properties=None):
            nonlocal node_id
            nid = f"n{node_id}"
            node_id += 1
            self.nodes.append({
                "id": nid,
                "type": node_type,
                "name": name,
                "properties": properties or {},
            })
            return nid

        def add_edge(source, target, relation, weight=1):
            self.edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "weight": weight,
            })

        # === 根节点 ===
        root = add_node("category", "预测性维护知识体系", {"level": 0})

        # === 设备类型 ===
        eq_types = {}
        for eq_type, eq_info in [
            ("motor", "电机"), ("pump", "水泵"), ("bearing", "轴承"),
            ("compressor", "压缩机"), ("gearbox", "齿轮箱"),
        ]:
            nid = add_node("equipment", eq_info, {"code": eq_type, "level": 1})
            eq_types[eq_type] = nid
            add_edge(root, nid, "包含")

        # === 传感器类型 ===
        sensor_nodes = {}
        for s_type, s_name, s_unit in [
            ("vibration", "振动", "mm/s"), ("temperature", "温度", "°C"),
            ("current", "电流", "A"), ("pressure", "压力", "MPa"),
            ("rpm", "转速", "RPM"), ("flow_rate", "流量", "L/min"),
            ("acoustic", "声学", "dB"),
        ]:
            nid = add_node("sensor", s_name, {"code": s_type, "unit": s_unit, "level": 1})
            sensor_nodes[s_type] = nid
            add_edge(root, nid, "监测维度")

        # === 故障类型 ===
        fault_data = [
            ("bearing_wear", "轴承磨损", "progressive", 168,
             ["振动高频分量增加", "温度缓慢上升", "异响出现"],
             ["润滑不良", "长期疲劳", "污染进入", "安装不当"],
             ["更换轴承", "改善润滑", "清洁密封", "调整游隙"]),
            ("imbalance", "转子不平衡", "sudden", 48,
             ["1倍频振动增大", "转速波动"],
             ["质量偏心", "积灰不均", "部件脱落", "材料磨损"],
             ["动平衡校正", "清理积灰", "更换脱落部件"]),
            ("misalignment", "轴系不对中", "progressive", 96,
             ["2倍频振动增大", "轴向温度上升"],
             ["安装误差", "基础沉降", "热膨胀", "联轴器磨损"],
             ["激光对中", "调整垫片", "更换联轴器", "加固基础"]),
            ("overload", "过载运行", "rapid", 24,
             ["电流持续偏高", "温度上升加快"],
             ["负载过大", "传动效率低", "机械卡阻", "电源异常"],
             ["降低负载", "检查传动系统", "清除卡阻", "检查电源"]),
            ("lubrication_failure", "润滑失效", "progressive", 72,
             ["摩擦温度升高", "润滑噪音"],
             ["油量不足", "油质劣化", "油路堵塞", "密封泄漏"],
             ["补充润滑油", "更换润滑油", "疏通油路", "更换密封"]),
            ("cavitation", "气蚀", "intermittent", 120,
             ["压力波动", "流量不稳定", "气泡噪音"],
             ["吸入压力低", "过滤器堵塞", "工况偏离", "安装高度高"],
             ["提高吸入压力", "清理过滤器", "调整工况点", "降低安装高度"]),
            ("seal_failure", "密封失效", "progressive", 96,
             ["压力微降", "温度微升"],
             ["密封件老化", "磨损", "压力冲击", "安装不当"],
             ["更换密封件", "检查压力系统", "改善安装"]),
            ("electrical_fault", "电气故障", "sudden", 12,
             ["电流波动", "局部温升"],
             ["绝缘老化", "接线松动", "过电压", "谐波干扰"],
             ["绝缘检测", "紧固接线", "加装保护", "谐波治理"]),
        ]

        fault_nodes = {}
        for fault_code, fault_name, pattern, rul, signs, causes, actions in fault_data:
            nid = add_node("fault", fault_name, {
                "code": fault_code, "pattern": pattern,
                "rul_hours": rul, "level": 2,
            })
            fault_nodes[fault_code] = nid
            add_edge(root, nid, "故障模式")

            # 故障 → 征兆
            for sign in signs:
                s_nid = add_node("symptom", sign, {"level": 3})
                add_edge(nid, s_nid, "表现为")

            # 故障 → 原因
            for cause in causes:
                c_nid = add_node("cause", cause, {"level": 3})
                add_edge(nid, c_nid, "由...引起")

            # 故障 → 处置
            for action in actions:
                a_nid = add_node("action", action, {"level": 3})
                add_edge(nid, a_nid, "处置方案")

        # === 故障与设备类型关联 ===
        fault_eq_map = {
            "bearing_wear": ["motor", "pump", "bearing", "compressor", "gearbox"],
            "imbalance": ["motor", "pump", "compressor"],
            "misalignment": ["motor", "pump", "compressor", "gearbox"],
            "overload": ["motor", "pump", "compressor"],
            "lubrication_failure": ["motor", "pump", "bearing", "gearbox"],
            "cavitation": ["pump"],
            "seal_failure": ["pump", "compressor"],
            "electrical_fault": ["motor", "compressor"],
        }

        for fault_code, eq_list in fault_eq_map.items():
            if fault_code in fault_nodes:
                for eq_code in eq_list:
                    if eq_code in eq_types:
                        add_edge(eq_types[eq_code], fault_nodes[fault_code], "易发故障")

        # === 故障与传感器关联 ===
        fault_sensor_map = {
            "bearing_wear": ["vibration", "temperature", "acoustic"],
            "imbalance": ["vibration", "rpm"],
            "misalignment": ["vibration", "temperature"],
            "overload": ["current", "temperature"],
            "lubrication_failure": ["temperature", "vibration", "acoustic"],
            "cavitation": ["vibration", "pressure", "flow_rate", "acoustic"],
            "seal_failure": ["pressure", "temperature"],
            "electrical_fault": ["current", "temperature"],
        }

        for fault_code, sensor_list in fault_sensor_map.items():
            if fault_code in fault_nodes:
                for s_code in sensor_list:
                    if s_code in sensor_nodes:
                        add_edge(sensor_nodes[s_code], fault_nodes[fault_code], "关联故障")

        # === 维护策略节点 ===
        strategies = [
            ("predictive", "预测性维护", "基于数据驱动的主动维护，在故障发生前预警"),
            ("preventive", "预防性维护", "按固定周期进行定期维护"),
            ("corrective", "纠正性维护", "故障后修复（被动维护）"),
            ("condition_based", "状态监测维护", "基于实时状态评估的按需维护"),
        ]
        for code, name, desc in strategies:
            s_nid = add_node("strategy", name, {"code": code, "description": desc, "level": 1})
            add_edge(root, s_nid, "维护策略")
            if code == "predictive":
                # 预测性维护关联所有故障
                for fault_code, f_nid in fault_nodes.items():
                    add_edge(s_nid, f_nid, "预防目标")

    def get_graph_data(self):
        return {"nodes": self.nodes, "edges": self.edges}

    def search(self, keyword):
        results = []
        kw = keyword.lower()
        for node in self.nodes:
            if kw in node["name"].lower() or kw in node.get("properties", {}).get("code", "").lower():
                related = self._get_related_nodes(node["id"])
                results.append({
                    "node": node,
                    "related_nodes": related[:10],
                })
        return results

    def _get_related_nodes(self, node_id):
        related = []
        for edge in self.edges:
            if edge["source"] == node_id:
                target = self._find_node(edge["target"])
                if target:
                    related.append({"node": target, "relation": edge["relation"]})
            elif edge["target"] == node_id:
                source = self._find_node(edge["source"])
                if source:
                    related.append({"node": source, "relation": f"被{edge['relation']}"})
        return related

    def _find_node(self, node_id):
        for node in self.nodes:
            if node["id"] == node_id:
                return node
        return None

    def get_node_detail(self, node_id):
        node = self._find_node(node_id)
        if not node:
            return None

        related = self._get_related_nodes(node_id)
        return {
            "node": node,
            "related": related,
            "related_count": len(related),
        }
