"""
AI 异常检测与预测引擎
- 统计阈值检测
- 趋势分析
- 退化曲线拟合
- 剩余使用寿命(RUL)预测
- 健康度评分
"""
import math
from datetime import datetime, timedelta


class AnomalyDetector:
    """异常检测与预测引擎"""

    def __init__(self, config):
        self.config = config
        self.thresholds = config.SENSOR_THRESHOLDS
        self.fault_modes = config.FAULT_MODES

    def detect(self, equipment_id, equipment_type, sensor_data_list):
        """
        执行异常检测
        sensor_data_list: 最近N个采样点 [{sensors: {vibration: x, ...}, ...}, ...]
        """
        if not sensor_data_list:
            return {
                "health_score": None,
                "anomalies": [],
                "trends": {},
                "risk_level": "unknown",
                "rul_hours": None,
                "rul_confidence": 0,
                "summary": "无数据",
            }

        latest = sensor_data_list[-1]
        sensors = latest.get("sensors", {})

        # 1. 阈值检测
        threshold_anomalies = self._check_thresholds(sensors)

        # 2. 趋势分析
        trends = self._analyze_trends(sensor_data_list)

        # 3. 统计异常检测（Z-score）
        stat_anomalies = self._statistical_detection(sensor_data_list)

        # 合并异常
        all_anomalies = threshold_anomalies + stat_anomalies

        # 4. 计算健康度
        health_score = self._calculate_health_score(sensors, all_anomalies, trends)

        # 5. 风险等级
        risk_level = self._get_risk_level(health_score)

        # 6. RUL 预测
        health_trend = [d.get("health_factor", 1.0) for d in sensor_data_list]
        rul_hours, rul_confidence = self._predict_rul_from_trend(health_trend)

        # 7. 综合摘要
        summary = self._generate_summary(health_score, all_anomalies, trends, risk_level)

        return {
            "health_score": round(health_score, 1),
            "anomalies": all_anomalies,
            "trends": trends,
            "risk_level": risk_level,
            "rul_hours": rul_hours,
            "rul_confidence": rul_confidence,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_thresholds(self, sensors):
        """阈值检测"""
        anomalies = []
        for sensor_type, value in sensors.items():
            threshold = self.thresholds.get(sensor_type)
            if not threshold:
                continue

            unit = threshold.get("unit", "")
            warn = threshold.get("warn")
            danger = threshold.get("danger")
            warn_low = threshold.get("warn_low")
            warn_high = threshold.get("warn_high")

            if danger is not None and value >= danger:
                anomalies.append({
                    "sensor": sensor_type,
                    "value": value,
                    "unit": unit,
                    "level": "danger",
                    "message": f"{sensor_type} = {value}{unit}，超过危险阈值 {danger}{unit}",
                })
            elif warn is not None and value >= warn:
                anomalies.append({
                    "sensor": sensor_type,
                    "value": value,
                    "unit": unit,
                    "level": "warning",
                    "message": f"{sensor_type} = {value}{unit}，超过预警阈值 {warn}{unit}",
                })
            elif warn_high is not None and value >= warn_high:
                anomalies.append({
                    "sensor": sensor_type,
                    "value": value,
                    "unit": unit,
                    "level": "warning",
                    "message": f"{sensor_type} = {value}{unit}，高于预警上限 {warn_high}{unit}",
                })
            elif warn_low is not None and value <= warn_low:
                anomalies.append({
                    "sensor": sensor_type,
                    "value": value,
                    "unit": unit,
                    "level": "warning",
                    "message": f"{sensor_type} = {value}{unit}，低于预警下限 {warn_low}{unit}",
                })

        return anomalies

    def _analyze_trends(self, data_list):
        """趋势分析"""
        trends = {}
        if len(data_list) < 5:
            return trends

        # 取前半段和后半段比较
        mid = len(data_list) // 2
        for sensor_type in data_list[-1].get("sensors", {}):
            values = [d["sensors"].get(sensor_type, 0) for d in data_list if "sensors" in d]
            if len(values) < 5:
                continue

            first_half = values[:mid]
            second_half = values[mid:]

            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            change_rate = ((avg_second - avg_first) / max(abs(avg_first), 0.001)) * 100

            # 线性回归斜率
            slope = self._linear_regression_slope(values)

            threshold = self.thresholds.get(sensor_type, {})
            unit = threshold.get("unit", "")

            trend_direction = "stable"
            if abs(change_rate) > 5:
                trend_direction = "increasing" if change_rate > 0 else "decreasing"
            if abs(change_rate) > 20:
                trend_direction = "rapidly_increasing" if change_rate > 0 else "rapidly_decreasing"

            trends[sensor_type] = {
                "current": round(values[-1], 2),
                "average": round(avg_second, 2),
                "change_rate": round(change_rate, 2),
                "slope": round(slope, 4),
                "direction": trend_direction,
                "unit": unit,
            }

        return trends

    def _linear_regression_slope(self, values):
        """简单线性回归斜率"""
        n = len(values)
        if n < 2:
            return 0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0
        return numerator / denominator

    def _statistical_detection(self, data_list):
        """统计异常检测（基于Z-score）"""
        anomalies = []
        if len(data_list) < 10:
            return anomalies

        latest = data_list[-1]
        sensors = latest.get("sensors", {})

        for sensor_type, current_value in sensors.items():
            values = [d["sensors"].get(sensor_type, 0) for d in data_list[:-1] if "sensors" in d]
            if len(values) < 10:
                continue

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(variance)

            if std < 0.001:
                continue

            z_score = abs(current_value - mean) / std

            if z_score > 3.0:
                threshold = self.thresholds.get(sensor_type, {})
                unit = threshold.get("unit", "")
                anomalies.append({
                    "sensor": sensor_type,
                    "value": current_value,
                    "unit": unit,
                    "level": "warning",
                    "message": f"{sensor_type} Z-score={z_score:.2f}，偏离均值{z_score:.1f}个标准差",
                })

        return anomalies

    def _calculate_health_score(self, sensors, anomalies, trends):
        """计算设备健康度（0-100）"""
        score = 100.0

        # 异常扣分
        for anomaly in anomalies:
            if anomaly["level"] == "danger":
                score -= 25
            elif anomaly["level"] == "warning":
                score -= 10

        # 趋势扣分
        for sensor_type, trend in trends.items():
            change_rate = abs(trend.get("change_rate", 0))
            if trend["direction"] in ("rapidly_increasing", "rapidly_decreasing"):
                score -= min(15, change_rate * 0.3)
            elif trend["direction"] in ("increasing", "decreasing"):
                score -= min(5, change_rate * 0.1)

        # 基于传感器值偏离度
        for sensor_type, value in sensors.items():
            threshold = self.thresholds.get(sensor_type)
            if not threshold:
                continue
            normal_max = threshold.get("normal_max")
            normal_min = threshold.get("normal_min")
            warn = threshold.get("warn")
            danger = threshold.get("danger")

            if danger and value >= danger:
                score -= 15
            elif warn and value >= warn:
                score -= 8
            elif normal_max and value > normal_max:
                # 轻度偏离
                deviation = (value - normal_max) / max(normal_max, 1)
                score -= min(5, deviation * 3)

        return max(0, min(100, score))

    def _get_risk_level(self, health_score):
        """根据健康度判定风险等级"""
        if health_score >= 85:
            return "low"
        elif health_score >= 70:
            return "moderate"
        elif health_score >= 50:
            return "high"
        elif health_score >= 30:
            return "critical"
        else:
            return "imminent"

    def _predict_rul_from_trend(self, health_trend):
        """基于健康度趋势预测RUL"""
        if len(health_trend) < 10:
            return None, 0

        # 取最近的健康度数据
        recent = health_trend[-min(len(health_trend), 30):]
        if len(recent) < 5:
            return None, 0

        # 线性拟合
        slope = self._linear_regression_slope(recent)

        if slope >= -0.001:
            # 健康度稳定或上升
            return None, 0.9

        current_health = recent[-1]
        # 预测到达危险阈值的时间
        target = self.config.HEALTH_THRESHOLD_CRIT  # 50

        if current_health <= target:
            return 0, 0.8

        # 数据点间隔时间
        interval_hours = self.config.SENSOR_INTERVAL / 3600.0
        remaining_points = (current_health - target) / abs(slope)
        rul_hours = remaining_points * interval_hours

        # 置信度
        confidence = min(0.95, max(0.3, len(recent) / 30.0))

        return round(rul_hours, 1), round(confidence, 2)

    def predict_rul(self, health_trend, equipment_type="motor"):
        """RUL 预测（公开接口）"""
        if not health_trend or len(health_trend) < 5:
            return {
                "rul_hours": None,
                "confidence": 0,
                "degradation_rate": 0,
                "estimated_failure_time": None,
                "recommendation": "数据不足，无法预测",
            }

        # 从字典列表中提取健康度数值
        if health_trend and isinstance(health_trend[0], dict):
            health_values = [h["health"] for h in health_trend]
        else:
            health_values = health_trend

        rul_hours, confidence = self._predict_rul_from_trend(health_values)
        slope = self._linear_regression_slope(health_values[-30:])

        recommendation = ""
        if rul_hours is None:
            recommendation = "设备健康状态稳定，无需立即维护"
        elif rul_hours > 168:
            recommendation = f"预计还有 {rul_hours:.0f} 小时到达危险阈值，建议安排计划性维护"
        elif rul_hours > 72:
            recommendation = f"预计 {rul_hours:.0f} 小时后需要维护，建议尽快制定维护计划"
        elif rul_hours > 24:
            recommendation = f"仅剩约 {rul_hours:.0f} 小时，建议立即安排预防性维护"
        elif rul_hours > 0:
            recommendation = f"紧急！预计 {rul_hours:.0f} 小时内将达到危险阈值，需立即停机维护"
        else:
            recommendation = "设备已进入危险区间，需立即停机检修"

        failure_time = None
        if rul_hours and rul_hours > 0:
            failure_time = (datetime.now() + timedelta(hours=rul_hours)).strftime("%Y-%m-%d %H:%M")

        return {
            "rul_hours": rul_hours,
            "confidence": confidence,
            "degradation_rate": round(slope, 4),
            "estimated_failure_time": failure_time,
            "recommendation": recommendation,
        }

    def _generate_summary(self, health_score, anomalies, trends, risk_level):
        """生成检测摘要"""
        risk_names = {
            "low": "低风险",
            "moderate": "中风险",
            "high": "高风险",
            "critical": "危险",
            "imminent": "即将故障",
        }

        parts = [f"健康度 {health_score:.0f}/100，风险等级：{risk_names.get(risk_level, '未知')}"]

        if anomalies:
            danger_count = sum(1 for a in anomalies if a["level"] == "danger")
            warn_count = sum(1 for a in anomalies if a["level"] == "warning")
            if danger_count:
                parts.append(f"检测到 {danger_count} 项严重异常")
            if warn_count:
                parts.append(f"{warn_count} 项预警")

        trend_issues = []
        for s, t in trends.items():
            if t["direction"] in ("rapidly_increasing", "rapidly_decreasing"):
                trend_issues.append(f"{s}快速{('上升' if 'increasing' in t['direction'] else '下降')}")
            elif t["direction"] in ("increasing", "decreasing"):
                trend_issues.append(f"{s}{'上升' if 'increasing' in t['direction'] else '下降'}趋势")

        if trend_issues:
            parts.append("趋势：" + "、".join(trend_issues[:3]))

        if not anomalies and not trend_issues:
            parts.append("各项指标正常")

        return "；".join(parts)
