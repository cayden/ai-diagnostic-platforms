# 湖企智库 · AI 本地知识库 + DeepSeek 大语言模型

面向湖州制造企业的**本地化知识库智能问答系统**。敏感数据不出内网，DeepSeek 本地推理，RAG 检索增强回答。

> 核心承诺：**模型不出域 · 知识不出域 · 推理不出域**

---

## 一、它能解决什么痛点

| 痛点 | 解决方案 |
|---|---|
| 制度/规范散落在 Word、PDF、邮件里，员工查不到 | 统一入库 + 语义检索 + 智能问答 |
| 老员工经验沉淀在个人手里，人走知识丢 | 知识文档化入库，构建知识图谱 |
| 数据敏感，不敢用公有云大模型 API | 全链路本地化：Ollama + DeepSeek + bge-m3 |
| 制度条款翻半天找不到对应条款 | 向量 + 关键词融合检索，直接命中原文片段 |
| 权限混乱，机密资料谁都看得见 | 三级权限（公开/内部/机密）+ 审计日志 |

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    企业内网安全边界                       │
│                                                         │
│  ① 用户接入层    Web 浏览器（演示） / 企业微信 / 内部 API  │
│                                                         │
│  ② 应用功能层    知识库管理 · 智能问答 · 语义检索          │
│                  知识图谱 · 权限分级 · 审计日志            │
│                                                         │
│  ③ AI 服务层     RAG 引擎（分块→向量→融合检索→生成）      │
│                  本地 Embedding  bge-m3                  │
│                  DeepSeek 本地推理（Ollama）             │
│                                                         │
│  ④ 数据存储层    文档仓库 · 向量索引 · SQLite（日志/审计） │
└─────────────────────────────────────────────────────────┘
```

**双模式设计**（`config.py` 中 `MODE` 字段，或「系统设置」页切换）：

- `simulate`：模拟模式，**零依赖开箱即用**。本地字符 bigram 特征向量 + 模板化回答，适合无 GPU 环境演示完整链路（本仓库默认）
- `local`：本地推理模式，调用 Ollama 上的 `deepseek-r1` + `bge-m3`，真实 RAG 生成

## 三、快速开始

### 1. 环境要求

- Python 3.9+（推荐 3.10+）
- 演示用（simulate 模式）：无需其他依赖
- 真实推理（local 模式）：需安装 [Ollama](https://ollama.com) 并拉取模型

```bash
# 拉取本地大模型（企业内网服务器上执行一次）
ollama pull deepseek-r1:7b
ollama pull bge-m3
```

### 2. 安装与启动

```bash
cd local_kb_system
pip install -r requirements.txt          # flask / pypdf
python app.py                            # 默认端口 5102
```

浏览器打开 `http://<服务器IP>:5102` 即可。

### 3. 演示账号

| 账号 | 密码 | 角色 | 权限级别 |
|---|---|---|---|
| `admin` | `admin123` | 管理员 | 2（可看公开/内部/机密） |
| `zhangwei` | `user123` | 普通用户 | 1（仅公开/内部） |

## 四、5 分钟演示流程（对齐方案 PPT）

> 建议演示前先把浏览器开到登录页。以下脚本配合 PPT 第 8 页使用。

**0:00–0:30 登录，展示工作台**
用 `admin/admin123` 登录。工作台展示：知识库共 5 篇文档、15+ 知识片段、问答次数统计。点明「预置了 5 篇湖州制造业示例文档（制度/工艺/质检/投诉/数据安全）」。

**0:30–1:30 智能问答（核心环节）**
进入「智能问答」，提问：
- 「出差住宿费标准是什么？」→ 回答命中《员工差旅与报销管理制度》原文片段
- 「回流焊的温度曲线要求？」→ 命中《SMT贴片生产工艺规范》
- 「发票报销需要什么材料？」→ 命中报销条款

强调：**答案带出处，可溯源**；所有检索和推理都发生在内网。

**1:30–2:00 语义检索**
进入「知识检索」，输入「客户投诉处理时限」，展示 Top3 相关片段及相似度，说明「向量 + 关键词融合检索」的排序逻辑。

**2:00–2:40 知识图谱**
进入「知识图谱」，展示文档—主题—实体关联网络，点明「老员工经验被结构化了」。

**2:40–3:20 权限与安全（差异化亮点）**
登出，用 `zhangwei/user123` 登录，对比：
- 文档列表里**看不到**《数据安全管理规定》（机密级）
- 提问机密内容会被过滤
- 说明三级权限 + 全量审计日志（换回 admin 展示「审计日志」页）

**3:20–4:00 文档上传**
用 admin 在「知识库」页上传一份 .md 文件，实时完成解析→分块→向量化→可问答，展示「知识入库全自动」。

**4:00–4:40 模式与部署**
「系统设置」页展示双模式开关与 DeepSeek 连通性检测。说明真实部署：内网一台 GPU 服务器装 Ollama，切换 local 模式即接上真实大模型。

**4:40–5:00 收尾**
回到 PPT 价值总结页：「3 分钟让新员工变老师傅，制度查询从 30 分钟变 3 秒，数据 100% 不出域」。

## 五、权限模型

```
公开 (level 0) ── 全员可见
内部 (level 1) ── max_level ≥ 1 可见（普通用户默认）
机密 (level 2) ── 仅管理员可见
```

| 能力 | 管理员 | 普通用户 |
|---|---|---|
| 查看文档列表 / 图谱 / 统计 | 全部 | 按权限过滤 |
| 智能问答 / 语义检索 | ✅ | ✅（机密内容自动过滤） |
| 上传文档 | ✅ | ✅（不得上传高于自身级别文档） |
| 删除文档 / 重建索引 | ✅ | ❌ |
| 用户管理 / 审计日志 / 问答历史 | ✅ | ❌ |
| 模式切换 / LLM 连通性测试 | ✅ | ❌ |

## 六、API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/login` `/api/logout` | 登录 / 登出（session cookie） |
| GET | `/api/me` | 当前用户信息 |
| GET | `/api/documents` | 文档列表（按权限过滤） |
| POST | `/api/documents` | 上传文档（multipart，可选 title/category/level） |
| DELETE | `/api/documents/<id>` | 删除文档（管理员） |
| POST | `/api/documents/<id>/reindex` | 重建索引（管理员） |
| POST | `/api/chat` | RAG 问答 `{question, category?}` |
| POST | `/api/retrieve` | 语义检索 `{question, top_k}` |
| POST | `/api/qa/<id>/feedback` | 问答点赞/踩 `{rating}` |
| GET | `/api/qa/history` | 问答历史（管理员） |
| GET | `/api/graph` | 知识图谱 `{nodes, edges}` |
| GET | `/api/audit` | 审计日志（管理员） |
| GET/POST/PUT/DELETE | `/api/users[/<id>]` | 用户管理（管理员） |
| GET | `/api/system` | 系统状态（模式/模型/连通性） |
| POST | `/api/system/mode` | 切换 simulate/local |
| POST | `/api/system/llm-test` | DeepSeek 连通性测试 |
| GET | `/api/stats` | 工作台统计 |

## 七、自动化测试

```bash
# 需先启动服务
python scripts/api_smoke_test.py
```

34 项冒烟测试覆盖：认证、统计、文档 CRUD、权限过滤、RAG 问答、语义检索、知识图谱、审计、用户管理、模式切换、上传、反馈、登出、越权防护。

## 八、目录结构

```
local_kb_system/
├── app.py                    # Flask 主应用（路由 + 权限 + 审计）
├── config.py                 # 端口/模式/模型/演示账号配置
├── requirements.txt
├── scripts/
│   └── api_smoke_test.py     # 全量 API 冒烟测试
├── modules/
│   ├── database.py           # SQLite 数据层（WAL，5 张表）
│   ├── document_parser.py    # PDF/docx/xlsx/pptx/txt/md/csv 解析
│   ├── chunker.py            # 分块（段落聚合 + 重叠）
│   ├── embedder.py           # bge-m3（local）/ bigram 特征向量（simulate）
│   ├── vector_store.py       # 融合检索（0.55 向量 + 0.45 关键词）
│   ├── llm_client.py         # DeepSeek 本地调用（OpenAI 兼容）
│   ├── rag_engine.py         # RAG 编排
│   └── knowledge_graph.py    # 知识图谱（规则式抽取）
├── templates/index.html      # 单页应用（8 个功能页）
├── static/                   # css / js（含力导向图）
├── data/
│   ├── seed_docs/            # 5 篇湖州制造业示例文档
│   └── kb.db                 # SQLite（首次启动自动生成）
└── ppt/
    ├── gen_ppt.js            # 方案 PPT 生成脚本
    └── out/湖企智库_方案演示.pptx
```

## 九、对接真实 DeepSeek（local 模式）

1. 内网 GPU 服务器安装 Ollama，拉取 `deepseek-r1:7b`（建议 14b/32b 视显存）与 `bge-m3`
2. 修改 `config.py`：`OLLAMA_HOST` 指向该服务器（如 `http://192.168.1.50:11434`），`LLM_MODEL`、`EMBED_MODEL` 按实际设置
3. 启动后到「系统设置」页点「连通性测试」，通过后切换 `local` 模式即生效

> 说明：Ollama 提供 OpenAI 兼容接口 `/v1/chat/completions` 与原生 `/api/embed`，本系统已内置适配。
