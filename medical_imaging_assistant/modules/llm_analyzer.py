"""
Deepseek 大语言模型分析模块
负责良恶性判定、风险等级评估、诊断报告分析、AI问答
支持真实API调用和模拟响应两种模式
"""
import json
import random
import requests


class LLMAnalyzer:
    def __init__(self, config):
        self.config = config
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_url = config.DEEPSEEK_API_URL
        self.model = config.DEEPSEEK_MODEL
        self.use_simulation = config.LLM_USE_SIMULATION
        self.max_tokens = config.LLM_MAX_TOKENS
        self.temperature = config.LLM_TEMPERATURE

    def update_api_key(self, api_key):
        """更新API Key"""
        self.api_key = api_key
        if api_key:
            self.use_simulation = False
            self.config.LLM_USE_SIMULATION = False

    def analyze(self, detection_result, patient_info):
        """
        基于检测结果进行智能分析
        输出: 良恶性判定、风险等级、详细分析
        """
        detections = detection_result.get("detections", [])

        if not detections:
            return self._no_finding_analysis(patient_info)

        if self.use_simulation or not self.api_key:
            return self._simulate_analysis(detections, patient_info)
        else:
            return self._api_analysis(detections, patient_info)

    def _api_analysis(self, detections, patient_info):
        """调用Deepseek API进行真实分析"""
        prompt = self._build_analysis_prompt(detections, patient_info)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位专业的影像诊断AI助手，具备丰富的医学影像分析经验。"
                    "请基于YOLO目标检测结果，对影像进行专业分析，包括良恶性判定和风险等级评估。"
                    "请以JSON格式输出分析结果。注意：此分析仅供辅助参考，不能替代专业医师诊断。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self._call_api(messages)
            return self._parse_analysis_response(response, detections)
        except Exception as e:
            print(f"[LLM] API调用失败: {e}，回退到模拟分析")
            return self._simulate_analysis(detections, patient_info)

    def _call_api(self, messages):
        """调用Deepseek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(
            self.api_url, headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _build_analysis_prompt(self, detections, patient_info):
        """构建分析提示词"""
        det_text = json.dumps(detections, ensure_ascii=False, indent=2)
        patient_text = json.dumps(patient_info, ensure_ascii=False, indent=2)
        return f"""请基于以下YOLO目标检测结果进行医学影像分析。

患者信息:
{patient_text}

检测结果（YOLO检测到的异常区域）:
{det_text}

请以JSON格式返回以下内容:
{{
  "overall_impression": "总体印象（一段话总结）",
  "findings": [
    {{
      "region": "区域名称",
      "description": "详细描述",
      "benign_malignant": "良性/恶性/不确定",
      "confidence_level": "高/中/低",
      "recommendation": "处理建议"
    }}
  ],
  "risk_level": "低风险/中风险/高风险",
  "risk_score": 0-100的数字,
  "risk_factors": ["风险因素1", "风险因素2"],
  "differential_diagnosis": ["鉴别诊断1", "鉴别诊断2"],
  "recommendations": ["建议1", "建议2", "建议3"],
  "follow_up": "随访建议",
  "disclaimer": "免责声明"
}}"""

    def _parse_analysis_response(self, response_text, detections):
        """解析API返回的分析结果"""
        try:
            result = json.loads(response_text)
            result["analysis_mode"] = "api"
            result["model"] = self.model
            return result
        except json.JSONDecodeError:
            return self._simulate_analysis(detections, {})

    def _simulate_analysis(self, detections, patient_info):
        """模拟LLM分析（无API Key时使用）"""
        findings = []
        risk_scores = []
        risk_factors_all = []
        diff_dx_all = []

        for det in detections:
            cls_name = det["class_name"]
            conf = det["confidence"]
            attrs = det.get("attributes", {})

            # 良恶性判定逻辑
            benign_ratio, risk_score, risk_level = self._assess_malignancy(
                cls_name, conf, attrs
            )

            # 生成描述
            description = self._generate_finding_description(cls_name, attrs, conf)

            # 鉴别诊断
            diff_dx = self._get_differential_diagnosis(cls_name)

            # 建议
            recommendation = self._get_recommendation(cls_name, risk_level)

            findings.append({
                "region": f"{cls_name}区域",
                "description": description,
                "benign_malignant": benign_ratio,
                "confidence_level": "高" if conf > 0.85 else ("中" if conf > 0.7 else "低"),
                "recommendation": recommendation,
                "risk_score": risk_score,
                "size_mm": attrs.get("size_mm", 0),
                "shape": attrs.get("shape", ""),
                "edge": attrs.get("edge", ""),
                "density": attrs.get("density", ""),
            })

            risk_scores.append(risk_score)
            risk_factors_all.extend(self._get_risk_factors(cls_name, attrs))
            diff_dx_all.extend(diff_dx)

        # 总体风险等级
        overall_risk = max(risk_scores) if risk_scores else 0
        if overall_risk >= 70:
            risk_level = "高风险"
        elif overall_risk >= 40:
            risk_level = "中风险"
        else:
            risk_level = "低风险"

        # 总体印象
        overall_impression = self._generate_overall_impression(
            findings, risk_level, patient_info
        )

        return {
            "overall_impression": overall_impression,
            "findings": findings,
            "risk_level": risk_level,
            "risk_score": overall_risk,
            "risk_factors": list(set(risk_factors_all)),
            "differential_diagnosis": list(set(diff_dx_all)),
            "recommendations": self._generate_recommendations(risk_level, findings),
            "follow_up": self._generate_follow_up(risk_level, findings),
            "disclaimer": "本报告由AI辅助诊断系统自动生成，仅供参考，不能替代专业医师的诊断和治疗建议。请结合临床情况综合判断。",
            "analysis_mode": "simulation",
            "model": "deepseek-chat (simulated)",
        }

    def _assess_malignancy(self, class_name, confidence, attrs):
        """评估良恶性"""
        # 各类别的恶性概率参考（基于医学知识）
        malignancy_ref = {
            "结节": {"low": 0.15, "mid": 0.35, "high": 0.65},
            "肿块": {"low": 0.40, "mid": 0.60, "high": 0.85},
            "钙化": {"low": 0.05, "mid": 0.15, "high": 0.30},
            "囊性病变": {"low": 0.03, "mid": 0.08, "high": 0.15},
            "实性病变": {"low": 0.20, "mid": 0.40, "high": 0.60},
            "磨玻璃影": {"low": 0.10, "mid": 0.30, "high": 0.55},
            "纤维条索": {"low": 0.02, "mid": 0.05, "high": 0.10},
            "胸腔积液": {"low": 0.05, "mid": 0.10, "high": 0.20},
        }

        ref = malignancy_ref.get(class_name, malignancy_ref["结节"])
        size_mm = attrs.get("size_mm", 10)
        edge = attrs.get("edge", "")

        # 大小影响
        if size_mm > 30:
            risk = ref["high"]
        elif size_mm > 15:
            risk = ref["mid"]
        else:
            risk = ref["low"]

        # 边缘特征影响
        if "模糊" in edge or "分叶" in edge:
            risk = min(risk + 0.15, 0.95)

        # 置信度修正
        risk = risk * (0.7 + 0.3 * confidence)

        risk_score = int(risk * 100)

        if risk < 0.2:
            benign = "良性"
        elif risk < 0.5:
            benign = "良性可能性大"
        elif risk < 0.7:
            benign = "不确定"
        else:
            benign = "恶性可能性大"

        return benign, risk_score, (
            "高风险" if risk_score >= 70 else ("中风险" if risk_score >= 40 else "低风险")
        )

    def _generate_finding_description(self, class_name, attrs, conf):
        """生成单个发现的描述"""
        size = attrs.get("size_mm", 0)
        shape = attrs.get("shape", "不规则形")
        edge = attrs.get("edge", "边缘清晰")
        density = attrs.get("density", "均匀密度")

        return (
            f"检出{class_name}样病灶，大小约{size}mm，形态{shape}，"
            f"{edge}，{density}。检测置信度{conf:.1%}。"
        )

    def _get_differential_diagnosis(self, class_name):
        """获取鉴别诊断"""
        dx_map = {
            "结节": ["炎性肉芽肿", "早期肺癌", "错构瘤", "肺结核结节"],
            "肿块": ["肺癌", "肺脓肿", "结核球", "转移瘤"],
            "钙化": ["陈旧性病变", "肉芽肿钙化", "血管钙化"],
            "囊性病变": ["肺囊肿", "包虫囊肿", "支气管囊肿"],
            "实性病变": ["肺炎实变", "肺梗死", "肺肿瘤"],
            "磨玻璃影": ["早期腺癌", "炎性病变", "不典型腺瘤样增生"],
            "纤维条索": ["陈旧性结核", "肺纤维化", "放射治疗后改变"],
            "胸腔积液": ["漏出性积液", "渗出性积液", "血性积液"],
        }
        return dx_map.get(class_name, ["待进一步检查明确"])

    def _get_risk_factors(self, class_name, attrs):
        """获取风险因素"""
        factors = []
        size = attrs.get("size_mm", 0)
        if size > 20:
            factors.append(f"病灶较大（{size}mm）")
        if "分叶" in attrs.get("edge", ""):
            factors.append("边缘可见分叶")
        if "模糊" in attrs.get("edge", ""):
            factors.append("边缘模糊")
        if "不均" in attrs.get("density", ""):
            factors.append("密度不均匀")
        if class_name in ("肿块", "实性病变"):
            factors.append("实性成分")
        return factors

    def _get_recommendation(self, class_name, risk_level):
        """获取处理建议"""
        if risk_level == "高风险":
            return f"建议进一步行增强CT/PET-CT检查，必要时行穿刺活检明确病理诊断，尽早专科就诊。"
        elif risk_level == "中风险":
            return f"建议3-6个月复查，观察病灶变化情况，结合临床进一步评估。"
        else:
            return f"建议6-12个月常规复查，目前无需特殊处理。"

    def _generate_overall_impression(self, findings, risk_level, patient_info):
        """生成总体印象"""
        count = len(findings)
        classes = list(set(f["region"] for f in findings))
        patient_str = ""
        if patient_info.get("name"):
            patient_str = f"{patient_info['name']}，"
        if patient_info.get("exam_type"):
            patient_str += f"{patient_info['exam_type']}检查示"

        findings_desc = "、".join(classes) if classes else "未见明显异常"

        return (
            f"{patient_str}共检出{count}处异常区域（{findings_desc}）。"
            f"综合各区域形态、大小、边缘及密度特征，"
            f"整体风险评估为{risk_level}。"
            f"建议结合临床进一步评估。"
        )

    def _generate_recommendations(self, risk_level, findings):
        """生成总体建议"""
        recs = []
        if risk_level == "高风险":
            recs.append("建议尽快至胸外科/呼吸科专科门诊就诊")
            recs.append("建议进一步完善增强CT检查，评估病灶血供情况")
            recs.append("必要时行CT引导下穿刺活检或支气管镜检查")
            recs.append("完善肿瘤标志物等相关血液检查")
        elif risk_level == "中风险":
            recs.append("建议3-6个月后复查影像，对比病灶变化")
            recs.append("建议完善相关血液检查（炎症指标、肿瘤标志物）")
            recs.append("注意观察有无症状变化，如有不适及时就诊")
        else:
            recs.append("建议6-12个月后常规复查")
            recs.append("保持健康生活方式，定期体检")
            recs.append("如有新发症状及时就医")

        return recs

    def _generate_follow_up(self, risk_level, findings):
        """生成随访建议"""
        if risk_level == "高风险":
            return "建议2-4周内完成进一步检查评估，根据结果制定后续随访计划。"
        elif risk_level == "中风险":
            return "建议3-6个月复查胸部CT，对比病灶大小及形态变化。"
        else:
            return "建议6-12个月常规体检复查。"

    def _no_finding_analysis(self, patient_info):
        """无异常发现的分析"""
        return {
            "overall_impression": "影像检查未见明显异常征象。各区域结构清晰，未检出明确病灶。",
            "findings": [],
            "risk_level": "低风险",
            "risk_score": 5,
            "risk_factors": [],
            "differential_diagnosis": [],
            "recommendations": [
                "保持健康生活方式",
                "建议定期体检复查",
            ],
            "follow_up": "建议年度体检复查。",
            "disclaimer": "本报告由AI辅助诊断系统自动生成，仅供参考，不能替代专业医师的诊断和治疗建议。",
            "analysis_mode": "simulation",
            "model": "deepseek-chat (simulated)",
        }

    def chat(self, message, context=""):
        """AI问答助手"""
        if self.use_simulation or not self.api_key:
            return self._simulate_chat(message, context)

        return self._api_chat(message, context)

    def _api_chat(self, message, context=""):
        """调用API进行问答"""
        system_prompt = (
            "你是一位专业的医学影像AI助手，擅长解答医学影像诊断相关问题。"
            "请用专业但易懂的语言回答问题。"
            "注意：你的回答仅供参考，不能替代专业医师的诊断和治疗建议。"
        )

        user_content = message
        if context:
            user_content = f"当前影像分析上下文:\n{context}\n\n用户问题: {message}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response = self._call_api_simple(messages)
            return {"role": "assistant", "content": response, "mode": "api"}
        except Exception as e:
            print(f"[LLM] 问答API调用失败: {e}")
            return self._simulate_chat(message, context)

    def _call_api_simple(self, messages):
        """简单API调用（不强制JSON格式）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        resp = requests.post(
            self.api_url, headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _simulate_chat(self, message, context=""):
        """模拟问答"""
        # 预定义问答库
        qa_pairs = {
            "结节": (
                "关于肺结节：肺结节是指肺内直径≤3cm的类圆形病灶。根据密度可分为实性结节、"
                "部分实性结节和纯磨玻璃结节。\n\n"
                "• 直径<5mm：微小结节，恶性风险极低（<1%），建议年度复查\n"
                "• 直径5-10mm：小结节，恶性风险低（1-5%），建议6-12月复查\n"
                "• 直径10-30mm：结节，需进一步评估，建议3月复查或增强CT\n\n"
                "高风险特征包括：分叶征、毛刺征、胸膜牵拉、空泡征等。\n"
                "注意：此信息仅供参考，请咨询专业医师获取个体化建议。"
            ),
            "良恶性": (
                "良恶性判定主要依据以下特征综合评估：\n\n"
                "1. 大小：>3cm的肿块恶性风险显著增加\n"
                "2. 形态：分叶状、不规则形提示恶性可能\n"
                "3. 边缘：毛刺征、模糊边缘是恶性特征\n"
                "4. 密度：不均匀密度、实性成分增加恶性风险\n"
                "5. 增强模式：恶性肿瘤多呈明显不均匀强化\n"
                "6. 随访变化：短期内增大提示恶性可能\n\n"
                "最终诊断需要结合病理检查结果。"
            ),
            "风险": (
                "影像风险评估综合考量多个因素：\n\n"
                "• 病灶大小和形态\n"
                "• 边缘特征（分叶、毛刺）\n"
                "• 密度特征（实性/磨玻璃/混合）\n"
                "• 患者年龄和吸烟史\n"
                "• 既往病史和家族史\n\n"
                "系统会基于这些因素自动计算风险评分并分级（低/中/高）。"
            ),
            "CT": (
                "CT检查注意事项：\n\n"
                "1. 检查前需去除金属物品\n"
                "2. 增强CT需禁食4-6小时\n"
                "3. 告知医生过敏史和肾功能\n"
                "4. 检查后多饮水促进造影剂排泄\n\n"
                "低剂量CT是肺癌筛查的首选方法，辐射剂量约为常规CT的1/5。"
            ),
            "随访": (
                "影像随访建议：\n\n"
                "• 低风险：6-12个月复查\n"
                "• 中风险：3-6个月复查\n"
                "• 高风险：2-4周内进一步检查\n\n"
                "随访时建议使用相同CT参数，便于对比病灶变化。"
                "Fleischner指南是常用的结节管理指南。"
            ),
        }

        # 匹配关键词
        for keyword, answer in qa_pairs.items():
            if keyword in message:
                return {"role": "assistant", "content": answer, "mode": "simulation"}

        # 通用回答
        general_answer = (
            f'您的问题涉及「{message[:20]}...」，这是一个医学影像相关的问题。\n\n'
            "基于医学知识，建议您：\n"
            "1. 结合具体影像表现综合判断\n"
            "2. 咨询专业影像科医师获取准确诊断\n"
            "3. 如有不适症状，及时就医\n\n"
            "我可以帮您解答关于结节、肿块、良恶性判定、CT检查、随访计划等"
            "影像诊断相关问题。请提供更具体的问题以获得更有针对性的回答。\n\n"
            "注意：以上信息仅供参考，不能替代专业医疗建议。"
        )

        return {"role": "assistant", "content": general_answer, "mode": "simulation"}
