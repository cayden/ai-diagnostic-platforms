# -*- coding: utf-8 -*-
"""湖企智库 - AI 本地知识库系统配置"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
SEED_DIR = os.path.join(DATA_DIR, "seed_docs")
DB_PATH = os.path.join(DATA_DIR, "kb.db")

PORT = 5102
HOST = "0.0.0.0"
DEBUG = False

# ---------- AI 服务配置（DeepSeek 本地部署） ----------
# Ollama 默认端口，本地部署地址；支持离线安装包形式
OLLAMA_HOST = "http://127.0.0.1:11434"
LLM_MODEL = "deepseek-r1:7b"     # 可切换 deepseek-r1:14b / deepseek-r1:32b
EMBED_MODEL = "bge-m3"           # 本地 Embedding 模型

# 运行模式:
#   simulate - 模拟模式（无需 GPU/模型，开箱即用，适合演示环境）
#   local    - 本地推理模式（调用本机 Ollama 的 DeepSeek 模型）
MODE = "simulate"

# ---------- 检索参数 ----------
TOP_K = 5                        # 检索返回片段数
CHUNK_SIZE = 500                 # 分块字符数
CHUNK_OVERLAP = 60               # 分块重叠
SIM_VECTOR_DIM = 512             # 模拟向量维度（特征哈希）

# ---------- 安全配置 ----------
SECRET_KEY = "huzhou-local-kb-secret-key-2026"
TOKEN_EXPIRE_HOURS = 12
MAX_UPLOAD_MB = 30
ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"}

# 演示账号（明文仅用于演示，生产请改数据库存储 + 强口令策略）
DEMO_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin", "dept": "信息中心"},
    {"username": "zhangwei", "password": "user123", "role": "user", "dept": "生产部"},
    {"username": "lihua", "password": "user123", "role": "user", "dept": "售后部"},
]
