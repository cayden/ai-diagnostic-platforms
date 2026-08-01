"""
医学影像知识图谱模块
"""
import json
import os


class KnowledgeGraph:
    def __init__(self, data_path):
        self.data_path = data_path
        self.graph_data = None
        self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.graph_data = json.load(f)
        else:
            self.graph_data = self._create_default_graph()
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.graph_data, f, ensure_ascii=False, indent=2)

    def _create_default_graph(self):
        """创建默认的医学影像知识图谱"""
        nodes = [
            # 疾病节点
            {"id": "d_lung_cancer", "label": "肺癌", "type": "disease", "category": "恶性肿瘤", "description": "起源于肺部组织的恶性肿瘤，是全球死亡率最高的癌症之一"},
            {"id": "d_pulmonary_nodule", "label": "肺结节", "type": "disease", "category": "病变", "description": "肺内直径≤3cm的类圆形病灶，可为良性或恶性"},
            {"id": "d_ggo", "label": "磨玻璃影", "type": "disease", "category": "影像征象", "description": "CT上呈云雾状密度增高影，可见于早期肺癌或炎性病变"},
            {"id": "d_pneumonia", "label": "肺炎", "type": "disease", "category": "炎症", "description": "肺实质的炎症性病变"},
            {"id": "d_tuberculosis", "label": "肺结核", "type": "disease", "category": "感染性疾病", "description": "由结核分枝杆菌引起的慢性感染"},
            {"id": "d_effusion", "label": "胸腔积液", "type": "disease", "category": "并发症", "description": "胸膜腔内液体积聚"},
            {"id": "d_hemorrhage", "label": "肺出血", "type": "disease", "category": "急症", "description": "肺组织内出血"},
            {"id": "d_fibrosis", "label": "肺纤维化", "type": "disease", "category": "间质性病变", "description": "肺组织纤维化改变"},
            {"id": "d_hamartoma", "label": "错构瘤", "type": "disease", "category": "良性肿瘤", "description": "肺部最常见的良性肿瘤"},
            {"id": "d_metastasis", "label": "肺转移瘤", "type": "disease", "category": "恶性肿瘤", "description": "其他部位恶性肿瘤转移至肺"},

            # 症状节点
            {"id": "s_cough", "label": "咳嗽", "type": "symptom", "category": "呼吸系统症状", "description": "常见的呼吸系统症状"},
            {"id": "s_hemoptysis", "label": "咯血", "type": "symptom", "category": "危险信号", "description": "咳出血液，需警惕严重疾病"},
            {"id": "s_chest_pain", "label": "胸痛", "type": "symptom", "category": "疼痛症状", "description": "胸部疼痛感"},
            {"id": "s_dyspnea", "label": "呼吸困难", "type": "symptom", "category": "呼吸系统症状", "description": "呼吸费力或气短"},
            {"id": "s_weight_loss", "label": "体重下降", "type": "symptom", "category": "全身症状", "description": "不明原因的体重减轻"},
            {"id": "s_fever", "label": "发热", "type": "symptom", "category": "全身症状", "description": "体温升高"},
            {"id": "s_fatigue", "label": "乏力", "type": "symptom", "category": "全身症状", "description": "全身无力感"},

            # 检查方法节点
            {"id": "e_ct", "label": "CT检查", "type": "exam", "category": "影像检查", "description": "计算机断层扫描，肺部病变首选检查方法"},
            {"id": "e_ldct", "label": "低剂量CT", "type": "exam", "category": "筛查", "description": "低剂量CT肺癌筛查"},
            {"id": "e_cect", "label": "增强CT", "type": "exam", "category": "影像检查", "description": "静脉注射造影剂后CT扫描"},
            {"id": "e_petct", "label": "PET-CT", "type": "exam", "category": "功能影像", "description": "正电子发射断层扫描结合CT"},
            {"id": "e_xray", "label": "X线胸片", "type": "exam", "category": "基础检查", "description": "传统X线检查"},
            {"id": "e_mri", "label": "MRI", "type": "exam", "category": "影像检查", "description": "磁共振成像"},
            {"id": "e_biopsy", "label": "穿刺活检", "type": "exam", "category": "病理检查", "description": "经皮肺穿刺获取组织病理"},
            {"id": "e_bronchoscopy", "label": "支气管镜", "type": "exam", "category": "内镜检查", "description": "经支气管镜检查"},
            {"id": "e_tumor_marker", "label": "肿瘤标志物", "type": "exam", "category": "血液检查", "description": "CEA、CYFRA21-1等血清标志物检测"},

            # 影像特征节点
            {"id": "f_spiculation", "label": "毛刺征", "type": "feature", "category": "恶性征象", "description": "病灶边缘放射状毛刺，提示恶性可能"},
            {"id": "f_lobulation", "label": "分叶征", "type": "feature", "category": "恶性征象", "description": "病灶边缘呈分叶状，恶性特征"},
            {"id": "f_cavity", "label": "空洞", "type": "feature", "category": "影像征象", "description": "病灶内含气腔"},
            {"id": "f_calcification", "label": "钙化", "type": "feature", "category": "良性征象", "description": "病灶内钙质沉积，多为良性"},
            {"id": "f_pleural_retraction", "label": "胸膜牵拉", "type": "feature", "category": "恶性征象", "description": "病灶牵拉胸膜，恶性特征"},
            {"id": "f_vacuole", "label": "空泡征", "type": "feature", "category": "恶性征象", "description": "病灶内小气泡样低密度区"},
            {"id": "f_air_bronchogram", "label": "空气支气管征", "type": "feature", "category": "影像征象", "description": "病灶内可见支气管充气"},
            {"id": "f_ground_glass", "label": "磨玻璃密度", "type": "feature", "category": "密度特征", "description": "CT上云雾状密度增高"},
            {"id": "f_solid", "label": "实性", "type": "feature", "category": "密度特征", "description": "完全遮蔽肺组织的密度"},

            # 治疗方法节点
            {"id": "t_surgery", "label": "手术治疗", "type": "treatment", "category": "外科", "description": "肺叶切除、楔形切除等"},
            {"id": "t_chemo", "label": "化学治疗", "type": "treatment", "category": "内科", "description": "全身化疗"},
            {"id": "t_radio", "label": "放射治疗", "type": "treatment", "category": "放疗", "description": "包括SBRT等精准放疗"},
            {"id": "t_targeted", "label": "靶向治疗", "type": "treatment", "category": "精准医学", "description": "EGFR、ALK等靶向药物"},
            {"id": "t_immuno", "label": "免疫治疗", "type": "treatment", "category": "免疫", "description": "PD-1/PD-L1免疫检查点抑制剂"},
            {"id": "t_antibiotic", "label": "抗感染治疗", "type": "treatment", "category": "内科", "description": "抗生素治疗"},
            {"id": "t_anti_tb", "label": "抗结核治疗", "type": "treatment", "category": "感染", "description": "标准抗结核方案"},

            # 风险因素节点
            {"id": "r_smoking", "label": "吸烟", "type": "risk_factor", "category": "生活习惯", "description": "肺癌最重要的危险因素"},
            {"id": "r_age", "label": "高龄", "type": "risk_factor", "category": "人口学", "description": ">40岁肺癌风险增加"},
            {"id": "r_family", "label": "家族史", "type": "risk_factor", "category": "遗传", "description": "一级亲属肺癌史"},
            {"id": "r_asbestos", "label": "石棉暴露", "type": "risk_factor", "category": "职业", "description": "职业性石棉接触"},
            {"id": "r_copd", "label": "慢阻肺", "type": "risk_factor", "category": "基础疾病", "description": "COPD是肺癌危险因素"},
        ]

        edges = [
            # 疾病-症状关系
            {"source": "d_lung_cancer", "target": "s_cough", "relation": "常表现为"},
            {"source": "d_lung_cancer", "target": "s_hemoptysis", "relation": "可导致"},
            {"source": "d_lung_cancer", "target": "s_chest_pain", "relation": "可引起"},
            {"source": "d_lung_cancer", "target": "s_dyspnea", "relation": "可导致"},
            {"source": "d_lung_cancer", "target": "s_weight_loss", "relation": "常伴随"},
            {"source": "d_lung_cancer", "target": "s_fatigue", "relation": "常伴随"},
            {"source": "d_pneumonia", "target": "s_fever", "relation": "常表现为"},
            {"source": "d_pneumonia", "target": "s_cough", "relation": "常表现为"},
            {"source": "d_pneumonia", "target": "s_dyspnea", "relation": "可导致"},
            {"source": "d_tuberculosis", "target": "s_cough", "relation": "常表现为"},
            {"source": "d_tuberculosis", "target": "s_hemoptysis", "relation": "可导致"},
            {"source": "d_tuberculosis", "target": "s_fever", "relation": "常表现为"},
            {"source": "d_tuberculosis", "target": "s_weight_loss", "relation": "常伴随"},
            {"source": "d_effusion", "target": "s_dyspnea", "relation": "可导致"},
            {"source": "d_effusion", "target": "s_chest_pain", "relation": "可引起"},

            # 疾病-检查关系
            {"source": "d_lung_cancer", "target": "e_ldct", "relation": "筛查用"},
            {"source": "d_lung_cancer", "target": "e_cect", "relation": "评估用"},
            {"source": "d_lung_cancer", "target": "e_petct", "relation": "分期用"},
            {"source": "d_lung_cancer", "target": "e_biopsy", "relation": "确诊用"},
            {"source": "d_lung_cancer", "target": "e_bronchoscopy", "relation": "检查用"},
            {"source": "d_lung_cancer", "target": "e_tumor_marker", "relation": "辅助检查"},
            {"source": "d_pulmonary_nodule", "target": "e_ct", "relation": "首选检查"},
            {"source": "d_pulmonary_nodule", "target": "e_ldct", "relation": "筛查用"},
            {"source": "d_pneumonia", "target": "e_xray", "relation": "基础检查"},
            {"source": "d_pneumonia", "target": "e_ct", "relation": "进一步检查"},
            {"source": "d_tuberculosis", "target": "e_ct", "relation": "常用检查"},
            {"source": "d_effusion", "target": "e_ct", "relation": "评估用"},
            {"source": "d_effusion", "target": "e_xray", "relation": "初筛用"},

            # 疾病-影像特征关系
            {"source": "d_lung_cancer", "target": "f_spiculation", "relation": "典型特征"},
            {"source": "d_lung_cancer", "target": "f_lobulation", "relation": "典型特征"},
            {"source": "d_lung_cancer", "target": "f_pleural_retraction", "relation": "常见征象"},
            {"source": "d_lung_cancer", "target": "f_vacuole", "relation": "可见征象"},
            {"source": "d_lung_cancer", "target": "f_cavity", "relation": "可见征象"},
            {"source": "d_lung_cancer", "target": "f_solid", "relation": "密度特征"},
            {"source": "d_pulmonary_nodule", "target": "f_calcification", "relation": "良性特征"},
            {"source": "d_ggo", "target": "f_ground_glass", "relation": "密度特征"},
            {"source": "d_ggo", "target": "f_air_bronchogram", "relation": "可见征象"},
            {"source": "d_pneumonia", "target": "f_air_bronchogram", "relation": "典型征象"},
            {"source": "d_tuberculosis", "target": "f_cavity", "relation": "典型征象"},
            {"source": "d_tuberculosis", "target": "f_calcification", "relation": "常见特征"},
            {"source": "d_hamartoma", "target": "f_calcification", "relation": "典型特征"},

            # 疾病-治疗关系
            {"source": "d_lung_cancer", "target": "t_surgery", "relation": "首选治疗"},
            {"source": "d_lung_cancer", "target": "t_chemo", "relation": "辅助治疗"},
            {"source": "d_lung_cancer", "target": "t_radio", "relation": "可选治疗"},
            {"source": "d_lung_cancer", "target": "t_targeted", "relation": "精准治疗"},
            {"source": "d_lung_cancer", "target": "t_immuno", "relation": "免疫治疗"},
            {"source": "d_pneumonia", "target": "t_antibiotic", "relation": "首选治疗"},
            {"source": "d_tuberculosis", "target": "t_anti_tb", "relation": "标准治疗"},

            # 疾病-风险因素关系
            {"source": "d_lung_cancer", "target": "r_smoking", "relation": "危险因素"},
            {"source": "d_lung_cancer", "target": "r_age", "relation": "危险因素"},
            {"source": "d_lung_cancer", "target": "r_family", "relation": "危险因素"},
            {"source": "d_lung_cancer", "target": "r_asbestos", "relation": "危险因素"},
            {"source": "d_lung_cancer", "target": "r_copd", "relation": "相关因素"},
            {"source": "d_tuberculosis", "target": "r_age", "relation": "相关因素"},

            # 疾病间关系
            {"source": "d_pulmonary_nodule", "target": "d_lung_cancer", "relation": "可能进展为"},
            {"source": "d_ggo", "target": "d_lung_cancer", "relation": "可能进展为"},
            {"source": "d_metastasis", "target": "d_lung_cancer", "relation": "相关"},
            {"source": "d_copd", "target": "d_lung_cancer" if False else "r_copd", "relation": "相关"},
            {"source": "d_tuberculosis", "target": "d_pulmonary_nodule", "relation": "可表现为"},
            {"source": "d_pneumonia", "target": "d_effusion", "relation": "可并发"},
            {"source": "d_lung_cancer", "target": "d_effusion", "relation": "可并发"},
            {"source": "d_lung_cancer", "target": "d_hemorrhage", "relation": "可导致"},
        ]

        return {"nodes": nodes, "edges": edges}

    def get_graph_data(self):
        """获取完整图谱数据"""
        return self.graph_data

    def search(self, keyword):
        """搜索关键词相关的节点和边"""
        if not keyword:
            return {"nodes": [], "edges": []}

        keyword_lower = keyword.lower()
        matched_nodes = set()

        for node in self.graph_data["nodes"]:
            if (
                keyword_lower in node["label"].lower()
                or keyword_lower in node.get("description", "").lower()
                or keyword_lower in node.get("category", "").lower()
            ):
                matched_nodes.add(node["id"])

        # 找出关联边
        related_edges = []
        connected_nodes = set(matched_nodes)
        for edge in self.graph_data["edges"]:
            if edge["source"] in matched_nodes or edge["target"] in matched_nodes:
                related_edges.append(edge)
                connected_nodes.add(edge["source"])
                connected_nodes.add(edge["target"])

        nodes = [
            n for n in self.graph_data["nodes"] if n["id"] in connected_nodes
        ]

        return {"nodes": nodes, "edges": related_edges}

    def get_node_detail(self, node_id):
        """获取节点详情"""
        for node in self.graph_data["nodes"]:
            if node["id"] == node_id:
                # 获取关联节点
                related = []
                for edge in self.graph_data["edges"]:
                    if edge["source"] == node_id:
                        target_node = next(
                            (n for n in self.graph_data["nodes"] if n["id"] == edge["target"]),
                            None
                        )
                        if target_node:
                            related.append({
                                "node": target_node,
                                "relation": edge["relation"],
                                "direction": "outgoing"
                            })
                    elif edge["target"] == node_id:
                        source_node = next(
                            (n for n in self.graph_data["nodes"] if n["id"] == edge["source"]),
                            None
                        )
                        if source_node:
                            related.append({
                                "node": source_node,
                                "relation": edge["relation"],
                                "direction": "incoming"
                            })

                node_copy = node.copy()
                node_copy["related"] = related
                return node_copy
        return None
