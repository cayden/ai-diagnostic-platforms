"""
系统配置文件 - 生产设备预测性维护与智能运维平台
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Flask
    SECRET_KEY = "predictive-maintenance-2026"

    # 路径
    BASE_DIR = BASE_DIR
    DB_PATH = os.path.join(BASE_DIR, "data", "maintenance.db")
    UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")

    # 服务配置
    HOST = "0.0.0.0"
    PORT = 5100
    DEBUG = False

    # 传感器模拟配置
    SENSOR_INTERVAL = 3  # 采样间隔（秒）
    HISTORY_RETENTION = 720  # 保留最近720个数据点（约36分钟@3s间隔）
    DEGRADATION_SPEED = 1.0  # 退化速度倍率

    # 异常检测配置
    ANOMALY_WINDOW = 30       # 滑动窗口大小（数据点数）
    TREND_WINDOW = 60         # 趋势分析窗口
    ALERT_COOLDOWN = 60       # 告警冷却期（秒），避免重复告警
    HEALTH_THRESHOLD_WARN = 70   # 健康度警告阈值
    HEALTH_THRESHOLD_CRIT = 50   # 健康度危险阈值
    HEALTH_THRESHOLD_FAIL = 30   # 健康度故障阈值

    # RUL 预测配置
    RUL_FORECAST_HOURS = 72   # 预测未来72小时
    RUL_MIN_CONFIDENCE = 0.6  # 最小置信度

    # 设备类型配置
    EQUIPMENT_TYPES = {
        "motor": {
            "name": "电机",
            "sensors": ["vibration", "temperature", "current", "rpm"],
            "icon": "motor",
        },
        "pump": {
            "name": "水泵",
            "sensors": ["vibration", "temperature", "pressure", "current", "flow_rate"],
            "icon": "pump",
        },
        "bearing": {
            "name": "轴承",
            "sensors": ["vibration", "temperature", "acoustic"],
            "icon": "bearing",
        },
        "compressor": {
            "name": "压缩机",
            "sensors": ["vibration", "temperature", "pressure", "current", "rpm"],
            "icon": "compressor",
        },
        "gearbox": {
            "name": "齿轮箱",
            "sensors": ["vibration", "temperature", "acoustic", "rpm"],
            "icon": "gearbox",
        },
    }

    # 传感器阈值（正常范围）
    SENSOR_THRESHOLDS = {
        "vibration": {"unit": "mm/s", "normal_min": 0.5, "normal_max": 4.5, "warn": 7.0, "danger": 11.2},
        "temperature": {"unit": "°C", "normal_min": 30, "normal_max": 65, "warn": 80, "danger": 95},
        "current": {"unit": "A", "normal_min": 5, "normal_max": 25, "warn": 32, "danger": 40},
        "pressure": {"unit": "MPa", "normal_min": 0.3, "normal_max": 1.2, "warn": 1.6, "danger": 2.0},
        "rpm": {"unit": "RPM", "normal_min": 1400, "normal_max": 1600, "warn_low": 1300, "warn_high": 1750},
        "flow_rate": {"unit": "L/min", "normal_min": 80, "normal_max": 120, "warn_low": 60, "warn_high": 140},
        "acoustic": {"unit": "dB", "normal_min": 55, "normal_max": 75, "warn": 85, "danger": 95},
    }

    # 故障模式知识库
    FAULT_MODES = {
        "bearing_wear": {
            "name": "轴承磨损",
            "affected_sensors": ["vibration", "temperature", "acoustic"],
            "degradation_pattern": "progressive",
            "early_signs": ["振动高频分量增加", "温度缓慢上升", "异响出现"],
            "critical_signs": ["振动剧烈", "温度超限", "噪音显著"],
            "rul_estimate_hours": 168,
        },
        "imbalance": {
            "name": "转子不平衡",
            "affected_sensors": ["vibration", "rpm"],
            "degradation_pattern": "sudden",
            "early_signs": ["1倍频振动增大", "转速波动"],
            "critical_signs": ["振动超限", "设备抖动"],
            "rul_estimate_hours": 48,
        },
        "misalignment": {
            "name": "轴系不对中",
            "affected_sensors": ["vibration", "temperature"],
            "degradation_pattern": "progressive",
            "early_signs": ["2倍频振动增大", "轴向温度上升"],
            "critical_signs": ["振动剧烈", "联轴器过热"],
            "rul_estimate_hours": 96,
        },
        "overload": {
            "name": "过载运行",
            "affected_sensors": ["current", "temperature"],
            "degradation_pattern": "rapid",
            "early_signs": ["电流持续偏高", "温度上升加快"],
            "critical_signs": ["电流超限", "电机过热保护"],
            "rul_estimate_hours": 24,
        },
        "lubrication_failure": {
            "name": "润滑失效",
            "affected_sensors": ["temperature", "vibration", "acoustic"],
            "degradation_pattern": "progressive",
            "early_signs": ["摩擦温度升高", "润滑噪音"],
            "critical_signs": ["干摩擦异响", "温度急升"],
            "rul_estimate_hours": 72,
        },
        "cavitation": {
            "name": "气蚀",
            "affected_sensors": ["vibration", "pressure", "flow_rate", "acoustic"],
            "degradation_pattern": "intermittent",
            "early_signs": ["压力波动", "流量不稳定", "气泡噪音"],
            "critical_signs": ["压力骤降", "振动剧烈", "噪音刺耳"],
            "rul_estimate_hours": 120,
        },
        "seal_failure": {
            "name": "密封失效",
            "affected_sensors": ["pressure", "temperature"],
            "degradation_pattern": "progressive",
            "early_signs": ["压力微降", "温度微升"],
            "critical_signs": ["泄漏", "压力显著下降"],
            "rul_estimate_hours": 96,
        },
        "electrical_fault": {
            "name": "电气故障",
            "affected_sensors": ["current", "temperature"],
            "degradation_pattern": "sudden",
            "early_signs": ["电流波动", "局部温升"],
            "critical_signs": ["电流突变", "绝缘失效"],
            "rul_estimate_hours": 12,
        },
    }
