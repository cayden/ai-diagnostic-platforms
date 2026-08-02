"""Deepseek LLM 智能分析模块

功能:
  1. 缺陷根因分析 — 基于检测结果推断可能原因
  2. 处置建议 — 返工/报废/让步接收/复检
  3. 质检报告生成 — 结构化检验报告
  4. AI 问答助手 — 质检知识问答

双模式:
  - simulation: 内置知识库生成分析结果，开箱即用
  - api:       调用 Deepseek API 进行真实AI分析
"""

import json
import requests

from config import Config


class LlmAnalyzer:
    def __init__(self, config: Config):
        self.config = config
        self.api_url = config.LLM_API_URL
        self.api_key = config.LLM_API_KEY
        self.model = config.LLM_MODEL
        self.mode = config.LLM_MODE
        self.timeout = config.LLM_TIMEOUT

        # 内置缺陷知识库 (code -> 详情)
        self.defect_knowledge = {
            "scratch": {
                "causes": ["来料划伤", "搬运/周转过程碰撞", "工装夹具磨损锐边", "机器人路径规划不合理"],
                "impact": "影响外观，严重者影响功能性表面",
                "actions": ["轻微划痕: 抛光返工", "深划痕: 记录并评审", "严重划痕: 报废"],
                "prevention": ["优化来料包装防护", "检查工装锐边", "定期维护夹具", "调整搬运路径"],
            },
            "dent": {
                "causes": ["搬运碰撞", "夹持力过大", "跌落", "工具敲击"],
                "impact": "表面凹陷影响外观和结构强度",
                "actions": ["浅凹痕: 外观评审后让步接收", "深凹痕: 报废或返工修复"],
                "prevention": ["规范搬运操作", "调整夹持力参数", "增加防撞垫"],
            },
            "crack": {
                "causes": ["材料内部缺陷", "注塑/压铸工艺参数不当", "应力集中", "热处理不当"],
                "impact": "严重影响结构完整性，存在安全隐患",
                "actions": ["任何裂纹: 直接报废", "追溯同批次产品全部复检"],
                "prevention": ["加强来料检验", "优化注塑工艺参数", "改进热处理工艺", "减少应力集中设计"],
            },
            "stain": {
                "causes": ["冷却液/润滑油残留", "环境灰尘", "操作员手汗", "清洗不彻底"],
                "impact": "影响外观，可能影响后续工序",
                "actions": ["清洁后复检合格即可放行", "顽固污渍: 返工清洗"],
                "prevention": ["加强清洗工序", "改善车间环境", "操作员佩戴手套"],
            },
            "deformation": {
                "causes": ["注塑/冲压工艺参数不当", "冷却不均匀", "脱模力过大", "材料收缩率异常"],
                "impact": "尺寸超差，影响装配和功能",
                "actions": ["轻微变形: 校正返工", "严重变形: 报废", "追溯同模号产品"],
                "prevention": ["优化工艺参数", "改善冷却系统", "调整脱模力度", "材料批次管控"],
            },
            "missing_part": {
                "causes": ["装配遗漏", "来料缺件", "自动化设备卡料", "BOM错误"],
                "impact": "功能缺失，影响最终产品性能",
                "actions": ["立即补充缺失零件", "检查同批次产品", "追溯装配过程"],
                "prevention": ["增加防呆设计", "装配后自动检测", "优化BOM核对流程", "设备维护"],
            },
            "misalign": {
                "causes": ["定位夹具磨损", "装配力度不当", "基准面变形", "设备精度漂移"],
                "impact": "装配精度不足，影响功能",
                "actions": ["重新校正装配", "检查夹具精度", "严重偏移: 报废"],
                "prevention": ["定期校验夹具精度", "规范装配力度", "设备定期校准"],
            },
            "color_diff": {
                "causes": ["原材料批次差异", "喷涂/染色工艺参数波动", "烘烤温度不均", "色母配比错误"],
                "impact": "外观不一致，影响产品一致性",
                "actions": ["轻微色差: 让步接收(需客户确认)", "明显色差: 返工重涂"],
                "prevention": ["来料色差管控", "稳定工艺参数", "定期校准色差仪", "批次隔离管理"],
            },
            "burrs": {
                "causes": ["模具/刀具磨损", "切削参数不当", "材料延展性过高", "模具间隙不当"],
                "impact": "影响外观，可能影响装配和安全性",
                "actions": ["去毛刺返工", "检查模具/刀具状态"],
                "prevention": ["定期更换模具/刀具", "优化切削参数", "模具定期维护"],
            },
            "oxidation": {
                "causes": ["表面处理不良", "存储环境潮湿", "材料防锈处理缺失", "工序间停留过长"],
                "impact": "影响外观和耐腐蚀性",
                "actions": ["轻微氧化: 重新表面处理", "严重氧化: 报废"],
                "prevention": ["改善存储环境", "加强防锈处理", "缩短工序间停留时间"],
            },
        }

    def analyze_defects(self, image_name, detections, quality_result, product_name, process):
        """分析检测结果，生成根因分析和处置建议"""
        if self.mode == "api" and self.api_key:
            return self._api_analyze(image_name, detections, quality_result, product_name, process)
        return self._simulate_analyze(image_name, detections, quality_result, product_name, process)

    def _simulate_analyze(self, image_name, detections, quality_result, product_name, process):
        """模拟分析"""
        defects = detections if isinstance(detections, list) else detections.get("detections", [])
        verdict = quality_result.get("verdict", "PASS")
        counts = quality_result.get("defect_counts", {})

        # 收集缺陷类型
        defect_types = {}
        for d in defects:
            code = d.get("code", "unknown")
            name = d.get("class_name", "未知")
            sev = d.get("severity", "minor")
            conf = d.get("confidence", 0)
            if code not in defect_types:
                defect_types[code] = {"name": name, "severity": sev, "count": 0, "confidences": []}
            defect_types[code]["count"] += 1
            defect_types[code]["confidences"].append(conf)

        # 生成根因分析
        root_causes = []
        for code, info in defect_types.items():
            knowledge = self.defect_knowledge.get(code, {})
            avg_conf = sum(info["confidences"]) / len(info["confidences"])
            root_causes.append({
                "defect_type": code,
                "defect_name": info["name"],
                "count": info["count"],
                "avg_confidence": round(avg_conf, 4),
                "possible_causes": knowledge.get("causes", ["未知原因"]),
                "impact": knowledge.get("impact", "影响待评估"),
                "prevention": knowledge.get("prevention", ["加强检测"]),
            })

        # 处置建议
        disposition = self._generate_disposition(verdict, counts, defect_types)

        # 总体评价
        summary = self._generate_summary(verdict, counts, defect_types, product_name, process)

        # 风险评估
        risk_assessment = self._assess_risk(counts, defect_types)

        return {
            "mode": "simulation",
            "summary": summary,
            "root_causes": root_causes,
            "disposition": disposition,
            "risk_assessment": risk_assessment,
            "recommendations": self._gen_recommendations(verdict, defect_types, counts),
            "follow_up": self._gen_follow_up(verdict, defect_types),
        }

    def _generate_disposition(self, verdict, counts, defect_types):
        """生成处置建议"""
        if verdict == "PASS":
            if not defect_types:
                return {
                    "action": "ACCEPT",
                    "action_label": "接收放行",
                    "description": "未检出缺陷，判定合格，可正常放行进入下一工序。",
                    "priority": "normal",
                }
            return {
                "action": "ACCEPT_WITH_NOTE",
                "action_label": "有条件接收",
                "description": f"检出轻微缺陷({counts.get('minor', 0)}个)，在合格标准内，建议记录后放行。",
                "priority": "low",
            }

        # 不合格
        if counts.get("critical", 0) > 0:
            return {
                "action": "REJECT",
                "action_label": "报废",
                "description": f"检出{counts['critical']}个严重缺陷，存在安全隐患，建议直接报废处理。",
                "priority": "urgent",
            }

        if counts.get("major", 0) > 0:
            return {
                "action": "REWORK",
                "action_label": "返工",
                "description": f"检出{counts['major']}个一般缺陷，建议返工修复后重新检验。",
                "priority": "high",
            }

        return {
            "action": "REVIEW",
            "action_label": "评审",
            "description": f"检出{counts.get('minor', 0)}个轻微缺陷，超合格标准，建议组织MRB评审后决定。",
            "priority": "medium",
        }

    def _generate_summary(self, verdict, counts, defect_types, product_name, process):
        """生成总体评价"""
        total = counts.get("critical", 0) + counts.get("major", 0) + counts.get("minor", 0)
        verdict_label = "合格" if verdict == "PASS" else "不合格"

        if total == 0:
            summary = (
                f"{product_name}在{process}工序经AI视觉检测，未检出任何缺陷，"
                f"判定为{verdict_label}。产品表面质量良好，建议正常放行。"
            )
        else:
            parts = []
            if counts.get("critical", 0):
                parts.append(f"严重缺陷{counts['critical']}个")
            if counts.get("major", 0):
                parts.append(f"一般缺陷{counts['major']}个")
            if counts.get("minor", 0):
                parts.append(f"轻微缺陷{counts['minor']}个")

            defect_names = [info["name"] for info in defect_types.values()]
            summary = (
                f"{product_name}在{process}工序经AI视觉检测，"
                f"共检出{total}个缺陷（{'、'.join(parts)}），"
                f"主要缺陷类型为{'、'.join(defect_names)}。"
                f"综合判定为{verdict_label}。"
            )

        return summary

    def _assess_risk(self, counts, defect_types):
        """风险评估"""
        critical = counts.get("critical", 0)
        major = counts.get("major", 0)
        minor = counts.get("minor", 0)

        risk_score = critical * 5 + major * 3 + minor * 1

        if critical > 0:
            level = "high"
            label = "高风险"
            advice = "存在严重缺陷，需立即隔离产品并追溯同批次"
        elif major > 2:
            level = "high"
            label = "高风险"
            advice = "一般缺陷较多，建议停机排查工艺问题"
        elif major > 0:
            level = "medium"
            label = "中风险"
            advice = "存在一般缺陷，需返工并加强过程监控"
        elif minor > 3:
            level = "medium"
            label = "中风险"
            advice = "轻微缺陷偏多，建议关注工序稳定性"
        else:
            level = "low"
            label = "低风险"
            advice = "质量稳定，维持正常检验"

        # 检查是否有需要追溯的缺陷类型
        trace_codes = ["crack", "missing_part", "deformation"]
        need_trace = any(code in defect_types for code in trace_codes)

        return {
            "level": level,
            "label": label,
            "score": risk_score,
            "advice": advice,
            "need_batch_trace": need_trace,
        }

    def _gen_recommendations(self, verdict, defect_types, counts):
        """生成改进建议"""
        recs = []

        for code, info in defect_types.items():
            knowledge = self.defect_knowledge.get(code, {})
            for p in knowledge.get("prevention", []):
                rec = f"[{info['name']}] {p}"
                if rec not in recs:
                    recs.append(rec)

        if verdict == "FAIL":
            recs.insert(0, "建议暂停该批次生产，进行工艺排查")

        if counts.get("critical", 0) > 0:
            recs.insert(0, "严重缺陷检出！建议立即隔离同批次产品，全面追溯排查")

        if not recs:
            recs.append("当前质量状态良好，建议维持现有检验频次")

        return recs

    def _gen_follow_up(self, verdict, defect_types):
        """生成后续行动建议"""
        actions = []

        if verdict == "PASS":
            actions.append("正常放行，进入下一工序")
            if defect_types:
                actions.append("记录缺陷信息用于质量趋势分析")
        else:
            actions.append("隔离不合格品，悬挂标识")
            actions.append("通知质量工程师进行评审")

            if "crack" in defect_types:
                actions.append("追溯同批次/同模号产品，全检排查裂纹")
            if "missing_part" in defect_types:
                actions.append("检查装配线防呆装置是否有效")
            if "deformation" in defect_types:
                actions.append("检查工艺参数（温度/压力/时间）是否正常")

            actions.append("更新控制计划，增加该缺陷的检验频次")

        return actions

    def _api_analyze(self, image_name, detections, quality_result, product_name, process):
        """调用 Deepseek API 进行真实分析"""
        defects = detections if isinstance(detections, list) else detections.get("detections", [])

        system_prompt = (
            "你是一名专业的制造质量工程师，擅长分析产品缺陷、根因分析和质量改进建议。"
            "请基于AI视觉检测的结果，给出专业的缺陷根因分析和处置建议。"
        )

        user_prompt = (
            f"产品: {product_name}\n"
            f"工序: {process}\n"
            f"判定结果: {quality_result.get('verdict_label', '未知')}\n"
            f"缺陷统计: {json.dumps(quality_result.get('defect_counts', {}), ensure_ascii=False)}\n"
            f"缺陷详情:\n"
        )
        for i, d in enumerate(defects, 1):
            user_prompt += (
                f"  {i}. {d.get('class_name', '未知')} (置信度: {d.get('confidence', 0):.2%})\n"
                f"     严重度: {d.get('severity', '未知')}\n"
            )

        user_prompt += (
            "\n请以JSON格式返回分析结果，包含以下字段:\n"
            '{"summary": "总体评价", "root_causes": [{"defect_name":"","possible_causes":[],'
            '"impact":"","prevention":[]}], "disposition": {"action":"","action_label":"",'
            '"description":"","priority":""}, "risk_assessment": {"level":"","label":"","advice":""},'
            '"recommendations": [], "follow_up": []}'
        )

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": self.config.LLM_MAX_TOKENS,
                    "temperature": 0.3,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # 尝试解析JSON
            try:
                result = json.loads(content)
                result["mode"] = "api"
                return result
            except json.JSONDecodeError:
                # 如果不是有效JSON，包装一下
                return {
                    "mode": "api",
                    "summary": content,
                    "root_causes": [],
                    "disposition": {},
                    "risk_assessment": {},
                    "recommendations": [],
                    "follow_up": [],
                }
        except Exception as e:
            print(f"[LLM API Error] {e}")
            # 降级到模拟模式
            return self._simulate_analyze(image_name, detections, quality_result, product_name, process)

    # ========== AI 问答助手 ==========
    def chat(self, message, context=""):
        """AI问答"""
        if self.mode == "api" and self.api_key:
            return self._api_chat(message, context)
        return self._simulate_chat(message, context)

    def _simulate_chat(self, message, context=""):
        """模拟问答"""
        msg = message.lower()

        # 缺陷类型相关
        defect_keywords = {
            "划痕": "scratch", "scratch": "scratch",
            "凹痕": "dent", "dent": "dent",
            "裂纹": "crack", "crack": "crack",
            "污渍": "stain", "stain": "stain",
            "变形": "deformation", "deformation": "deformation",
            "缺件": "missing_part", "missing": "missing_part",
            "错装": "misalign", "misalign": "misalign",
            "色差": "color_diff", "color": "color_diff",
            "毛刺": "burrs", "burr": "burrs",
            "氧化": "oxidation", "oxidation": "oxidation",
        }

        for kw, code in defect_keywords.items():
            if kw in msg:
                k = self.defect_knowledge.get(code, {})
                return {
                    "mode": "simulation",
                    "content": (
                        f"## {kw}缺陷分析\n\n"
                        f"**可能原因：**\n"
                        + "".join(f"- {c}\n" for c in k.get("causes", ["未知"]))
                        + f"\n**影响：** {k.get('impact', '待评估')}\n\n"
                        f"**处置建议：**\n"
                        + "".join(f"- {a}\n" for a in k.get("actions", ["记录并评审"]))
                        + f"\n**预防措施：**\n"
                        + "".join(f"- {p}\n" for p in k.get("prevention", ["加强检测"]))
                        + "\n*以上信息仅供参考，具体处置需结合实际产品标准和客户要求。*"
                    ),
                }

        # SPC相关
        if any(k in msg for k in ["spc", "统计过程控制", "控制图", "cpk"]):
            return {
                "mode": "simulation",
                "content": (
                    "## SPC统计过程控制\n\n"
                    "SPC (Statistical Process Control) 是利用统计方法监控生产过程质量的工具。\n\n"
                    "**关键指标：**\n"
                    "- **不良率 (P-chart):** 监控不合格品比例\n"
                    "- **缺陷数 (C-chart):** 监控单位产品缺陷数\n"
                    "- **CPK:** 过程能力指数，CPK≥1.33为合格，≥1.67为优秀\n\n"
                    "**控制限：**\n"
                    "- UCL (上控制限) = 均值 + 3σ\n"
                    "- LCL (下控制限) = 均值 - 3σ\n"
                    "- 超出控制限需立即排查异常原因\n\n"
                    "本系统支持自动计算不良率趋势和缺陷数控制图，可在「质量统计」页面查看。"
                ),
            }

        # 合格判定
        if any(k in msg for k in ["合格", "判定", "标准", "accept", "pass"]):
            return {
                "mode": "simulation",
                "content": (
                    "## 质量判定标准\n\n"
                    "本系统采用多级判定标准：\n\n"
                    "| 缺陷等级 | 允许数量 | 说明 |\n"
                    "|---------|---------|------|\n"
                    "| 严重(critical) | 0 | 任何严重缺陷即不合格 |\n"
                    "| 一般(major) | ≤2 | 一般缺陷超过2个即不合格 |\n"
                    "| 轻微(minor) | ≤5 | 轻微缺陷超过5个即不合格 |\n\n"
                    "**严重缺陷**：裂纹、缺件 — 影响功能和安全\n"
                    "**一般缺陷**：变形、错装、氧化 — 影响装配和性能\n"
                    "**轻微缺陷**：划痕、凹痕、污渍、色差、毛刺 — 主要影响外观\n\n"
                    "判定标准可在config.py中根据客户要求调整。"
                ),
            }

        # AI检测相关
        if any(k in msg for k in ["yolo", "检测", "模型", "识别", "如何检测"]):
            return {
                "mode": "simulation",
                "content": (
                    "## AI视觉检测原理\n\n"
                    "本系统采用 **YOLO目标检测模型** 进行缺陷检测：\n\n"
                    "1. **模型训练**：使用标注的缺陷图像训练YOLO模型，学习各类缺陷的视觉特征\n"
                    "2. **实时推理**：上传产品图片后，模型在毫秒级完成检测\n"
                    "3. **结果输出**：缺陷位置(边界框)、类型、置信度\n"
                    "4. **LLM分析**：Deepseek大模型对检测结果进行根因分析和处置建议\n\n"
                    "**支持10类缺陷检测：**\n"
                    "划痕、凹痕、裂纹、污渍、变形、缺件、错装、色差、毛刺、氧化\n\n"
                    "**置信度阈值**：默认0.45，可在系统设置中调整。提高阈值减少误报，降低阈值减少漏报。"
                ),
            }

        # 批量检测
        if any(k in msg for k in ["批量", "batch", "批次"]):
            return {
                "mode": "simulation",
                "content": (
                    "## 批量检测功能\n\n"
                    "系统支持批量图片上传检测，适用于整批次来料检验或产线抽样：\n\n"
                    "**使用方式：**\n"
                    "1. 在检测页面上传多张图片\n"
                    "2. 系统自动逐张检测并汇总\n"
                    "3. 输出批次合格率、缺陷分布统计\n"
                    "4. 自动生成批次检验报告\n\n"
                    "API调用：`POST /api/inspect/batch`，使用 `images[]` 字段上传多文件。"
                ),
            }

        # 追溯
        if any(k in msg for k in ["追溯", "traceability", "溯源"]):
            return {
                "mode": "simulation",
                "content": (
                    "## 质量追溯体系\n\n"
                    "每次检测均关联以下追溯信息：\n\n"
                    "- **产品信息**：产品名称、产品编码\n"
                    "- **批次信息**：批次号、生产线\n"
                    "- **检验信息**：检验工序、检验员/系统\n"
                    "- **检测详情**：缺陷类型、位置、严重度、置信度\n"
                    "- **分析结果**：根因分析、处置建议、风险评估\n"
                    "- **时间记录**：检测时间、处理时间\n\n"
                    "在「历史记录」页面可按批次号、产品名称搜索，实现全流程追溯。"
                ),
            }

        # 通用回答
        general_answer = (
            f"您的问题涉及 \"{message[:30]}\"，这是一个AI质检相关的问题。\n\n"
            "我可以帮您解答以下方面的问题：\n\n"
            "1. **缺陷类型**：划痕、凹痕、裂纹、污渍、变形、缺件、错装、色差、毛刺、氧化\n"
            "2. **检测技术**：YOLO模型原理、置信度调整、检测模式切换\n"
            "3. **质量标准**：合格判定标准、缺陷分级、AQL抽样\n"
            "4. **SPC统计**：控制图、CPK、不良率趋势分析\n"
            "5. **质量追溯**：批次追溯、检测记录、报告生成\n"
            "6. **批量检测**：批量上传、批次检验、合格率统计\n\n"
            "请提供更具体的问题以获得更有针对性的回答。\n\n"
            "*注意：以上信息仅供参考，不能替代专业质量工程师的判断。*"
        )

        return {"mode": "simulation", "content": general_answer}

    def _api_chat(self, message, context=""):
        """调用 Deepseek API 进行问答"""
        system_prompt = (
            "你是一名专业的制造质量工程师和AI质检系统助手。"
            "你的职责是回答关于AI视觉检测、缺陷分析、质量控制、SPC统计等方面的问题。"
            "回答请使用中文，格式清晰，适当使用Markdown。"
        )

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": self.config.LLM_MAX_TOKENS,
                    "temperature": 0.7,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"mode": "api", "content": content}
        except Exception as e:
            print(f"[LLM Chat API Error] {e}")
            return self._simulate_chat(message, context)
