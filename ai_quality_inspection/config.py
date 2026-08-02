"""AI质检系统配置"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # ========== 服务配置 ==========
    HOST = "0.0.0.0"
    PORT = 5101
    DEBUG = False
    SECRET_KEY = "ai-quality-inspection-2026"

    # ========== 数据存储 ==========
    DB_PATH = os.path.join(BASE_DIR, "data", "quality.db")
    UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")

    # ========== YOLO 检测配置 ==========
    # 检测模式: "simulation" 模拟模式 | "model" 真实模型模式
    DETECTION_MODE = "simulation"
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
    YOLO_CONF_THRESHOLD = 0.45
    YOLO_IOU_THRESHOLD = 0.5

    # 缺陷类型定义 (class_id, 名称, 中文名, 严重度, 颜色)
    DEFECT_CLASSES = [
        (0, "scratch",    "划痕",    "minor",  "#FFA726"),
        (1, "dent",       "凹痕",    "minor",  "#FF7043"),
        (2, "crack",      "裂纹",    "critical","#E53935"),
        (3, "stain",      "污渍",    "minor",  "#AB47BC"),
        (4, "deformation","变形",    "major",  "#5C6BC0"),
        (5, "missing_part","缺件",   "critical","#26A69A"),
        (6, "misalign",   "错装",    "major",  "#42A5F5"),
        (7, "color_diff", "色差",    "minor",  "#9CCC65"),
        (8, "burrs",      "毛刺",    "minor",  "#FFCA28"),
        (9, "oxidation",  "氧化",    "major",  "#8D6E63"),
    ]

    # 缺陷严重度等级
    SEVERITY_LEVELS = {
        "minor":    {"label": "轻微", "score": 1, "color": "#FFA726"},
        "major":    {"label": "一般", "score": 3, "color": "#5C6BC0"},
        "critical": {"label": "严重", "score": 5, "color": "#E53935"},
    }

    # ========== 质量判定标准 ==========
    # 合格判定: 严重缺陷数=0 且 一般缺陷数<=2 且 轻微缺陷数<=5
    PASS_CRITERIA = {
        "critical_max": 0,
        "major_max": 2,
        "minor_max": 5,
    }

    # ========== Deepseek LLM 配置 ==========
    LLM_API_URL = "https://api.deepseek.com/v1/chat/completions"
    LLM_API_KEY = ""  # 填入 Deepseek API Key 启用真实AI分析
    LLM_MODEL = "deepseek-chat"
    LLM_MODE = "simulation"  # "simulation" | "api"
    LLM_TIMEOUT = 30
    LLM_MAX_TOKENS = 2048

    # ========== 检测批次默认信息 ==========
    DEFAULT_PRODUCT = "通用零件"
    DEFAULT_LINE = "1号线"
    DEFAULT_INSPECTOR = "AI视觉系统"

    # ========== SPC 统计过程控制 ==========
    SPC_SAMPLE_SIZE = 25  # 每组样本数
    SPC_UCL = 0.10       # 不良率上控制限 (10%)
    SPC_LCL = 0.0        # 不良率下控制限
    SPC_UCL2 = 3.0       # 缺陷数上控制限 (3-sigma)
