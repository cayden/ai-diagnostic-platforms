"""
系统配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Flask
    SECRET_KEY = "medical-imaging-assistant-2024"

    # 路径
    BASE_DIR = BASE_DIR
    UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
    REPORT_DIR = os.path.join(BASE_DIR, "data", "reports")
    MODEL_DIR = os.path.join(BASE_DIR, "models")
    DB_PATH = os.path.join(BASE_DIR, "data", "imaging.db")
    KG_DATA_PATH = os.path.join(BASE_DIR, "data", "medical_kg.json")

    # YOLO 配置
    YOLO_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.pt")  # 预训练模型路径
    YOLO_CONF_THRESHOLD = 0.25  # 置信度阈值
    YOLO_IOU_THRESHOLD = 0.45   # NMS IOU阈值
    YOLO_USE_SIMULATION = True  # 默认使用模拟检测（无GPU/模型时）
    # 检测类别（医学影像常见类别）
    DETECTION_CLASSES = [
        "结节", "肿块", "钙化", "囊性病变",
        "实性病变", "磨玻璃影", "纤维条索", "胸腔积液"
    ]

    # Deepseek LLM 配置
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL = "deepseek-chat"
    LLM_USE_SIMULATION = True  # 默认使用模拟响应（无API Key时）
    LLM_MAX_TOKENS = 2048
    LLM_TEMPERATURE = 0.3

    # 服务配置
    HOST = "0.0.0.0"
    PORT = 5099
    DEBUG = True

    # 上传限制
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "dcm", "tiff"}
