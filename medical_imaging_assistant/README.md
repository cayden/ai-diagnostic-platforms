# 智能影像辅助诊断系统

> 融合 YOLO 目标检测 + Deepseek 大语言模型，实现影像自动化分析的辅助诊断平台。

## 系统架构

```
影像上传 → YOLO 目标检测（区域精准定位）→ Deepseek LLM（良恶性判定 + 风险评估）
    → 诊断报告自动生成 → SQLite 持久化存储（历史追溯）
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 影像分析 | 上传影像后自动检测异常区域（结节、肿块、钙化等 8 类），Canvas 绘制检测框 |
| 良恶性判定 | 基于病灶大小、形态、边缘、密度等特征综合评估 |
| 风险等级评估 | 自动计算 0-100 风险评分，分低/中/高三级 |
| 诊断报告 | 自动生成结构化报告，支持导出 |
| 历史追溯 | SQLite 存储所有分析记录，支持搜索、分页、详情查看 |
| AI 问答助手 | 基于 Deepseek LLM 的医学影像问答 |
| 知识图谱 | 疾病-症状-检查-治疗关系网络，力导向图可视化 |

## 快速开始

### 1. 环境要求

- Python 3.9+（推荐 3.9 / 3.10 / 3.11）
- 无需 GPU，模拟模式开箱即用

### 2. 安装依赖

```bash
cd medical_imaging_assistant

# 创建虚拟环境（可选但推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

依赖列表：

```
flask
flask-cors
Pillow
requests
```

### 3. 启动服务

```bash
python app.py
```

启动成功后，在浏览器访问：

```
http://127.0.0.1:5099
```

终端会输出：

```
============================================================
  智能影像辅助诊断系统 v1.0
  YOLO + Deepseek LLM 融合架构
  访问地址: http://127.0.0.1:5099
============================================================
```

### 4. 开始使用

1. **上传影像** — 在「影像分析」页面上传医学影像（支持 PNG / JPG / BMP / TIFF），填写患者信息和检查类型
2. **查看结果** — 系统自动执行 YOLO 检测 + LLM 分析，展示检测框、良恶性判定、风险评分、诊断报告
3. **历史追溯** — 在「历史记录」页面查看所有分析记录，支持搜索和详情查看
4. **AI 问答** — 在「AI 助手」页面提问，获取医学影像相关解答
5. **知识图谱** — 在「知识图谱」页面浏览疾病-症状-检查-治疗关系网络

## 双模式架构

系统采用**模拟模式**和**真实模式**双轨设计：

| 模式 | YOLO 检测 | LLM 分析 | 启用条件 |
|------|-----------|----------|----------|
| 模拟模式（默认） | 基于图像复杂度生成逼真检测结果 | 基于内置医学知识库生成分析 | 开箱即用，无需任何配置 |
| 真实模式 | 加载 YOLOv8 预训练模型推理 | 调用 Deepseek API 生成分析 | 配置模型文件 / API Key |

### 切换到真实模式

**方式一：环境变量**

```bash
export DEEPSEEK_API_KEY=your_api_key_here
python app.py
```

**方式二：Web 界面**

在侧边栏点击「系统设置」，填入 Deepseek API Key，并关闭模拟模式开关。

### 配置 YOLO 真实模型

将 YOLOv8 预训练模型文件放置到 `models/` 目录：

```
models/
└── yolov8n.pt    # YOLOv8 模型权重
```

然后在 `config.py` 中设置：

```python
YOLO_USE_SIMULATION = False
```

> 启用真实 YOLO 检测需要额外安装 `ultralytics`：`pip install ultralytics`

## 配置说明

所有配置项在 `config.py` 中：

```python
# 服务端口
PORT = 5099

# YOLO 配置
YOLO_MODEL_PATH = "models/yolov8n.pt"     # 模型路径
YOLO_CONF_THRESHOLD = 0.25                 # 置信度阈值
YOLO_IOU_THRESHOLD = 0.45                  # NMS IOU 阈值
YOLO_USE_SIMULATION = True                 # 是否使用模拟模式

# Deepseek LLM 配置
DEEPSEEK_API_KEY = ""                      # API Key（也可通过环境变量设置）
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
LLM_USE_SIMULATION = True                  # 是否使用模拟模式
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.3

# 上传限制
MAX_CONTENT_LENGTH = 50 * 1024 * 1024     # 50MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "dcm", "tiff"}
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Web 主界面 |
| `POST` | `/api/analyze` | 上传影像并执行分析 |
| `GET` | `/api/history` | 获取历史记录列表（支持分页和搜索） |
| `GET` | `/api/history/<record_id>` | 获取单条记录详情 |
| `DELETE` | `/api/history/<record_id>` | 删除历史记录 |
| `GET` | `/api/history/stats` | 获取统计数据 |
| `POST` | `/api/chat` | AI 问答助手 |
| `GET` | `/api/chat/history` | 获取问答历史 |
| `DELETE` | `/api/chat/clear` | 清空问答历史 |
| `GET` | `/api/knowledge-graph` | 获取知识图谱数据 |
| `GET` | `/api/knowledge-graph/search?q=关键词` | 知识图谱搜索 |
| `GET` | `/api/knowledge-graph/node/<node_id>` | 获取节点详情 |
| `GET` | `/api/system/status` | 获取系统状态 |
| `POST` | `/api/system/config` | 更新系统配置 |

### API 调用示例

**影像分析：**

```bash
curl -X POST http://127.0.0.1:5099/api/analyze \
  -F "image=@/path/to/medical_image.png" \
  -F "patient_name=张三" \
  -F "patient_age=45" \
  -F "patient_gender=男" \
  -F "exam_type=胸部CT" \
  -F "clinical_info=体检发现肺部阴影"
```

**AI 问答：**

```bash
curl -X POST http://127.0.0.1:5099/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是肺结节？", "context": ""}'
```

## 项目结构

```
medical_imaging_assistant/
├── app.py                     # Flask 主应用（API 路由）
├── config.py                  # 系统配置
├── requirements.txt           # Python 依赖
├── README.md                  # 本文件
├── modules/
│   ├── __init__.py
│   ├── yolo_detector.py       # YOLO 目标检测（模拟 + 真实双模式）
│   ├── llm_analyzer.py        # Deepseek LLM（分析 + 问答）
│   ├── database.py            # SQLite 数据库（历史记录）
│   ├── knowledge_graph.py     # 医学知识图谱数据与查询
│   └── report_generator.py    # 诊断报告生成
├── templates/
│   └── index.html             # 单页应用入口
├── static/
│   ├── css/style.css          # 医学风格 UI 样式
│   └── js/
│       ├── app.js            # 主应用逻辑
│       └── knowledge_graph.js # 力导向图谱可视化
├── models/                    # YOLO 模型文件目录
└── data/
    ├── uploads/              # 上传的影像文件
    ├── reports/              # 生成的诊断报告
    ├── imaging.db            # SQLite 数据库
    └── medical_kg.json       # 知识图谱数据
```

## 检测类别

系统支持以下 8 类医学影像异常检测：

| 类别 | 说明 |
|------|------|
| 结节 | 肺结节等圆形高密度灶 |
| 肿块 | 较大的占位性病变 |
| 钙化 | 钙质沉积灶 |
| 囊性病变 | 囊肿等液性低密度灶 |
| 实性病变 | 实性组织密度灶 |
| 磨玻璃影 | 磨玻璃样密度增高 |
| 纤维条索 | 纤维化条索影 |
| 胸腔积液 | 胸腔内液体积聚 |

## 技术栈

- **后端**：Flask + Flask-CORS
- **目标检测**：YOLOv8（ultralytics）/ 模拟检测
- **大语言模型**：Deepseek Chat API / 模拟响应
- **数据库**：SQLite
- **前端**：原生 HTML/CSS/JavaScript，Canvas 绘制检测框，D3 力导向图

## 常见问题

**Q: 启动后页面打不开？**

确认服务已启动且端口 5099 未被占用。可通过 `lsof -i:5099` 检查。

**Q: 如何启用真实的 Deepseek AI 分析？**

在系统设置中填入 Deepseek API Key，或设置环境变量 `DEEPSEEK_API_KEY`，然后关闭 LLM 模拟模式。

**Q: 如何使用真实的 YOLO 模型？**

将 `yolov8n.pt` 放入 `models/` 目录，安装 `ultralytics`，在 `config.py` 中设置 `YOLO_USE_SIMULATION = False`。

**Q: 支持哪些影像格式？**

PNG、JPG、JPEG、BMP、TIFF、DCM，单文件最大 50MB。

## 免责声明

本系统仅用于辅助诊断参考，不能替代专业医师的诊断意见。所有 AI 生成的分析结果仅供参考，最终诊断请以专业医师意见为准。
