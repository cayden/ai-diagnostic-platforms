"""
故障诊断引擎
基于故障模式知识库进行推理诊断
"""
import json
from datetime import datetime


class FaultDiagnosis:
    """故障诊断引擎"""

    def __init__(self, config):
        self.config = config
        self.fault_modes = config.FAULT_MODES
        self.thresholds = config.SENSOR_THRESHOLDS

        # 故障-征兆映射权重
        self.symptom_weights = {
            "bearing_wear": {
                "vibration_high": 0.35, "temperature_high": 0.25,
                "acoustic_high": 0.25, "vibration_trend_up": 0.15,
            },
            "imbalance": {
                "vibration_high": 0.40, "rpm_unstable": 0.30,
                "vibration_trend_up": 0.30,
            },
            "misalignment": {
                "vibration_high": 0.35, "temperature_high": 0.30,
                "vibration_trend_up": 0.35,
            },
            "overload": {
                "current_high": 0.40, "temperature_high": 0.35,
                "current_trend_up": 0.25,
            },
            "lubrication_failure": {
                "temperature_high": 0.30, "acoustic_high": 0.30,
                "vibration_high": 0.20, "temperature_trend_up": 0.20,
            },
            "cavitation": {
                "vibration_high": 0.20, "pressure_low": 0.25,
                "flow_rate_low": 0.20, "acoustic_high": 0.25,
                "pressure_fluctuating": 0.10,
            },
            "seal_failure": {
                "pressure_low": 0.40, "temperature_high": 0.20,
                "pressure_trend_down": 0.40,
            },
            "electrical_fault": {
                "current_high": 0.35, "temperature_high": 0.35,
                "current_fluctuating": 0.30,
            },
        }

    def diagnose(self, equipment_type, sensor_data, detection_result):
        """
        根据传感器数据和检测结果进行故障诊断
        """
        if not sensor_data:
            return {"fault_type": None, "fault_name": "无数据", "confidence": 0, "description": ""}

        sensors = sensor_data.get("sensors", {})
        anomalies = detection_result.get("anomalies", [])
        trends = detection_result.get("trends", {})

        # 提取征兆
        symptoms = self._extract_symptoms(sensors, anomalies, trends)

        # 计算各故障概率
        fault_scores = {}
        for fault_type, weights in self.symptom_weights.items():
            # 检查设备类型是否适用
            fault_mode = self.fault_modes.get(fault_type, {})
            affected_sensors = fault_mode.get("affected_sensors", [])
            eq_sensors = self.config.EQUIPMENT_TYPES.get(equipment_type, {}).get("sensors", [])

            # 交集检查
            sensor_overlap = set(affected_sensors) & set(eq_sensors)
            if not sensor_overlap:
                continue

            score = 0
            for symptom, weight in weights.items():
                if symptom in symptoms:
                    score += weight * symptoms[symptom]

            # 传感器交集越多，置信度越高
            overlap_factor = len(sensor_overlap) / max(len(affected_sensors), 1)
            score *= overlap_factor

            if score > 0:
                fault_scores[fault_type] = score

        if not fault_scores:
            return {
                "fault_type": None,
                "fault_name": "无明确故障",
                "confidence": 0,
                "description": "各项指标在正常范围内，未检测到明确的故障征兆",
                "symptoms": symptoms,
                "recommendations": ["继续保持日常巡检", "定期记录传感器数据趋势"],
            }

        # 排序，取最可能的故障
        sorted_faults = sorted(fault_scores.items(), key=lambda x: x[1], reverse=True)
        top_fault_type = sorted_faults[0][0]
        top_score = sorted_faults[0][1]
        confidence = min(0.95, top_score)

        fault_mode = self.fault_modes.get(top_fault_type, {})
        fault_name = fault_mode.get("name", top_fault_type)
        early_signs = fault_mode.get("early_signs", [])
        critical_signs = fault_mode.get("critical_signs", [])

        # 生成诊断描述
        health = detection_result.get("health_score", 100)
        if health < 50:
            stage = "严重阶段"
            signs = critical_signs
        elif health < 70:
            stage = "恶化阶段"
            signs = early_signs + critical_signs[:1]
        else:
            stage = "早期征兆阶段"
            signs = early_signs

        description = (
            f"诊断结果：{fault_name}（{stage}）\n"
            f"置信度：{confidence:.0%}\n"
            f"关键征兆：{', '.join(signs[:3])}\n"
            f"受影响传感器：{', '.join(fault_mode.get('affected_sensors', []))}\n"
            f"退化模式：{fault_mode.get('degradation_pattern', '未知')}\n"
            f"预计RUL：{fault_mode.get('rul_estimate_hours', '未知')} 小时"
        )

        # 维修建议
        recommendations = self._generate_recommendations(top_fault_type, confidence, health)

        return {
            "fault_type": top_fault_type,
            "fault_name": fault_name,
            "confidence": round(confidence, 2),
            "stage": stage,
            "description": description,
            "symptoms": symptoms,
            "early_signs": early_signs,
            "critical_signs": critical_signs,
            "all_candidates": [
                {"fault_type": ft, "fault_name": self.fault_modes.get(ft, {}).get("name", ft), "score": round(s, 2)}
                for ft, s in sorted_faults[:3]
            ],
            "recommendations": recommendations,
            "rul_estimate_hours": fault_mode.get("rul_estimate_hours"),
        }

    def _extract_symptoms(self, sensors, anomalies, trends):
        """从传感器数据中提取征兆"""
        symptoms = {}

        for sensor_type, value in sensors.items():
            threshold = self.thresholds.get(sensor_type, {})
            warn = threshold.get("warn")
            danger = threshold.get("danger")
            warn_low = threshold.get("warn_low")
            warn_high = threshold.get("warn_high")

            if danger and value >= danger:
                symptoms[f"{sensor_type}_high"] = 1.0
            elif warn and value >= warn:
                symptoms[f"{sensor_type}_high"] = 0.7
            elif warn_high and value >= warn_high:
                symptoms[f"{sensor_type}_high"] = 0.5
            elif normal_max := threshold.get("normal_max"):
                if value > normal_max:
                    symptoms[f"{sensor_type}_high"] = 0.3

            if warn_low and value <= warn_low:
                symptoms[f"{sensor_type}_low"] = 1.0

        # 趋势征兆
        for sensor_type, trend in trends.items():
            direction = trend.get("direction", "stable")
            if "increasing" in direction:
                symptoms[f"{sensor_type}_trend_up"] = min(1.0, abs(trend.get("change_rate", 0)) / 20)
            elif "decreasing" in direction:
                symptoms[f"{sensor_type}_trend_down"] = min(1.0, abs(trend.get("change_rate", 0)) / 20)

        # 波动检测
        for sensor_type, trend in trends.items():
            change_rate = abs(trend.get("change_rate", 0))
            if change_rate > 15:
                symptoms[f"{sensor_type}_fluctuating"] = min(1.0, change_rate / 30)

        return symptoms

    def _generate_recommendations(self, fault_type, confidence, health):
        """生成维修建议"""
        recs_map = {
            "bearing_wear": [
                "检查轴承润滑状态，补充或更换润滑脂",
                "测量轴承游隙，评估磨损程度",
                "如振动持续增大，安排更换轴承",
                "检查轴颈和轴承座配合精度",
            ],
            "imbalance": [
                "进行动平衡测试，确定不平衡量",
                "检查转子是否有附着物或磨损",
                "根据测试结果进行配重校正",
                "复查安装基准和紧固状态",
            ],
            "misalignment": [
                "使用激光对中仪检查轴系对中状态",
                "检查联轴器磨损和弹性元件状态",
                "重新校正对中至允许偏差范围内",
                "检查地脚螺栓和基础刚度",
            ],
            "overload": [
                "检查负载是否超过额定值",
                "测量实际运行电流和功率",
                "调整工艺参数降低负载",
                "检查传动系统是否有卡阻",
            ],
            "lubrication_failure": [
                "检查润滑油/脂的油位和质量",
                "更换受污染的润滑油",
                "检查油路是否堵塞",
                "评估密封件是否需要更换",
            ],
            "cavitation": [
                "检查吸入侧压力是否过低",
                "清理或更换吸入过滤器",
                "调整运行工况点至高效区",
                "检查叶轮和泵壳气蚀损伤",
            ],
            "seal_failure": [
                "检查机械密封/填料密封状态",
                "观察是否有泄漏迹象",
                "更换损坏的密封件",
                "检查密封冲洗系统是否正常",
            ],
            "electrical_fault": [
                "测量绝缘电阻，检查绝缘状态",
                "检查接线端子是否松动或过热",
                "使用红外热像仪检测电气连接",
                "必要时停机进行电气检测",
            ],
        }

        recs = list(recs_map.get(fault_type, ["进行全面检查", "联系设备制造商技术支持"]))

        if confidence > 0.7 and health < 50:
            recs.insert(0, "紧急：建议立即停机检修")
        elif confidence > 0.5 and health < 70:
            recs.insert(0, "建议尽快安排计划性维护")

        return recs

    def query_by_symptoms(self, equipment_type, symptoms):
        """根据症状查询可能的故障"""
        results = []
        for fault_type, weights in self.symptom_weights.items():
            fault_mode = self.fault_modes.get(fault_type, {})
            affected = fault_mode.get("affected_sensors", [])
            eq_sensors = self.config.EQUIPMENT_TYPES.get(equipment_type, {}).get("sensors", [])

            if not (set(affected) & set(eq_sensors)):
                continue

            matched = 0
            total_weight = 0
            for symptom, weight in weights.items():
                if symptom in symptoms:
                    matched += 1
                    total_weight += weight

            if matched > 0:
                results.append({
                    "fault_type": fault_type,
                    "fault_name": fault_mode.get("name", fault_type),
                    "matched_symptoms": matched,
                    "confidence": min(0.95, total_weight),
                    "description": fault_mode.get("early_signs", []),
                })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results
