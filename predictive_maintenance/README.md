# 生产设备预测性维护与智能运维平台

> 把"坏了再修"变成"提前数小时到数天预警"——通过传感器实时采集振动、温度、电流等信号，AI 自动识别异常征兆，实现维修从被动变主动。

## 核心能力

| 能力 | 说明 |
|------|------|
| 传感器实时采集 | 7 类传感器（振动 / 温度 / 电流 / 压力 / 转速 / 流量 / 声学），按需生成数据，开箱即用 |
| AI 异常检测 | 统计阈值 + Z-Score + 趋势分析，计算 0-100 健康度评分，自动判定五级风险 |
| RUL 寿命预测 | 基于健康度退化曲线线性拟合，预测设备到达危险阈值的剩余小时数 |
| 故障诊断 | 8 种故障模式知识库，基于征兆-权重矩阵推理，给出置信度和处置建议 |
| 告警与工单 | 健康度低于阈值自动生成告警，严重时自动创建维修工单，支持全流程管理 |
| 知识图谱 | 105 节点 / 156 边的力导向图，覆盖设备→故障→征兆→原因→处置方案关系网络 |

## 快速开始

### 环境要求

- Python 3.9+
- pip

### 安装与启动

```bash
# 1. 进入项目目录
cd predictive_maintenance

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python3 app.py
```

启动后控制台输出：

```
============================================================
  生产设备预测性维护与智能运维平台 v1.0
  AI 异常检测 + RUL 预测 + 故障诊断
  访问地址: http://127.0.0.1:5100
============================================================
[初始化] 已加载 5 台设备
[初始化] 按需数据采集模式已启用
```

浏览器打开 **http://127.0.0.1:5100** 即可使用。

### 验证服务

```bash
# 检查系统状态
curl http://127.0.0.1:5100/api/system/status

# 查看设备列表
curl http://127.0.0.1:5100/api/equipment

# 查看知识图谱
curl http://127.0.0.1:5100/api/knowledge-graph
```

## 演示：注入故障体验预警能力

系统预置了故障注入接口，可在数秒内模拟设备从健康到故障的全过程：

```bash
# 1. 注入轴承磨损故障（严重度 0.9）
curl -X POST http://127.0.0.1:5100/api/system/inject-fault \
  -H "Content-Type: application/json" \
  -d '{"equipment_id":"EQ-001","fault_type":"bearing_wear","severity":0.9}'

# 2. 加速退化速度（10 倍）
curl -X POST http://127.0.0.1:5100/api/system/config \
  -H "Content-Type: application/json" \
  -d '{"degradation_speed":10.0,"sensor_interval":1}'

# 3. 多次请求触发数据采集（每次 API 调用自动补齐采样周期）
for i in $(seq 1 10); do
  curl -s http://127.0.0.1:5100/api/analysis/EQ-001 > /dev/null
  sleep 2
done

# 4. 查看 AI 分析结果
curl http://127.0.0.1:5100/api/analysis/EQ-001

# 5. 查看告警
curl http://127.0.0.1:5100/api/alerts

# 6. 查看自动创建的工单
curl http://127.0.0.1:5100/api/work-orders

# 7. 维修后重置设备
curl -X POST http://127.0.0.1:5100/api/system/reset-equipment/EQ-001
```

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     Web 前端 (单页应用)                    │
│  监控看板 │ 设备详情 │ 告警中心 │ 维修工单 │ 知识图谱       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP API
┌──────────────────────┴──────────────────────────────────┐
│                    Flask 应用层 (app.py)                  │
│  设备管理 │ 传感器数据 │ AI分析 │ 告警 │ 工单 │ 知识图谱   │
└──┬───────────┬───────────┬───────────┬───────────┬──────┘
   │           │           │           │           │
   ▼           ▼           ▼           ▼           ▼
┌──────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│模拟器│ │ 异常检测  │ │故障诊断 │ │ SQLite │ │知识图谱 │
│Sensor│ │ Anomaly  │ │ Fault   │ │Database│ │Knowledge│
│Simul.│ │ Detector │ │Diagnosis│ │        │ │  Graph  │
└──────┘ └──────────┘ └─────────┘ └────────┘ └─────────┘
```

**按需数据采集模式**：不使用后台线程，而是在每次 API 请求时自动补齐距离上次调用的采样周期（最多 10 个），避免线程争用和 SQLite 锁问题。

## 项目结构

```
predictive_maintenance/
├── app.py                         # Flask 主应用，所有 API 路由
├── config.py                      # 系统配置（端口/阈值/设备类型/故障模式）
├── requirements.txt               # Python 依赖
├── INTEGRATION_GUIDE.md           # 真实传感器数据对接方案
├── README.md                      # 本文件
├── modules/
│   ├── __init__.py
│   ├── sensor_simulator.py        # 传感器数据模拟引擎
│   ├── anomaly_detector.py        # AI 异常检测 + RUL 预测
│   ├── fault_diagnosis.py         # 故障诊断知识库
│   ├── knowledge_graph.py         # 故障知识图谱
│   └── database.py                # SQLite 数据库管理
├── templates/
│   └── index.html                 # 单页应用入口
├── static/
│   ├── css/style.css              # 工业风格 UI
│   └── js/
│       ├── app.js                # 主应用逻辑
│       └── knowledge_graph.js     # 力导向图谱可视化
└── data/
    └── maintenance.db             # SQLite 数据库（运行时自动创建）
```

## 配置说明

所有配置集中在 `config.py` 的 `Config` 类中，运行时可通过 API 动态调整部分参数。

### 服务配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5100` | 服务端口 |
| `DEBUG` | `False` | 调试模式（生产环境关闭） |

### 传感器与采集

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SENSOR_INTERVAL` | `3` 秒 | 采样间隔，可通过 API 修改 |
| `HISTORY_RETENTION` | `720` 点 | 历史数据保留点数（约 36 分钟 @3s） |
| `DEGRADATION_SPEED` | `1.0` | 退化速度倍率，可通过 API 修改 |

### 健康度阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `HEALTH_THRESHOLD_WARN` | `70` | 低于此值生成 warning 告警 |
| `HEALTH_THRESHOLD_CRIT` | `50` | 低于此值生成 critical 告警 + 自动工单 |
| `HEALTH_THRESHOLD_FAIL` | `30` | 低于此值生成 emergency 告警 + 紧急工单 |
| `ALERT_COOLDOWN` | `60` 秒 | 告警冷却期，避免重复告警 |

### RUL 预测

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RUL_FORECAST_HOURS` | `72` 小时 | 预测未来时长 |
| `RUL_MIN_CONFIDENCE` | `0.6` | 最小置信度阈值 |

## 默认设备

系统启动时自动创建 5 台演示设备：

| 设备 ID | 名称 | 类型 | 厂商 | 传感器 |
|---------|------|------|------|--------|
| EQ-001 | A线主电机 | motor | 西门子 | 振动、温度、电流、转速 |
| EQ-002 | B线循环水泵 | pump | 格兰特 | 振动、温度、压力、电流、流量 |
| EQ-003 | C线主轴轴承 | bearing | SKF | 振动、温度、声学 |
| EQ-004 | D线空压机 | compressor | 阿特拉斯 | 振动、温度、压力、电流、转速 |
| EQ-005 | E线减速齿轮箱 | gearbox | SEW | 振动、温度、声学、转速 |

## 支持的传感器类型

| 传感器 | 单位 | 正常范围 | 警告阈值 | 危险阈值 |
|--------|------|----------|----------|----------|
| vibration 振动 | mm/s | 0.5 - 4.5 | 7.0 | 11.2 |
| temperature 温度 | °C | 30 - 65 | 80 | 95 |
| current 电流 | A | 5 - 25 | 32 | 40 |
| pressure 压力 | MPa | 0.3 - 1.2 | 1.6 | 2.0 |
| rpm 转速 | RPM | 1400 - 1600 | 1300 / 1750 | - |
| flow_rate 流量 | L/min | 80 - 120 | 60 / 140 | - |
| acoustic 声学 | dB | 55 - 75 | 85 | 95 |

## 故障模式知识库

| 故障类型 | 名称 | 影响传感器 | 退化模式 | 预估 RUL |
|----------|------|-----------|----------|----------|
| bearing_wear | 轴承磨损 | 振动、温度、声学 | 渐进式 | 168h |
| imbalance | 转子不平衡 | 振动、转速 | 突发型 | 48h |
| misalignment | 轴系不对中 | 振动、温度 | 渐进式 | 96h |
| overload | 过载运行 | 电流、温度 | 快速型 | 24h |
| lubrication_failure | 润滑失效 | 温度、振动、声学 | 渐进式 | 72h |
| cavitation | 气蚀 | 振动、压力、流量、声学 | 间歇型 | 120h |
| seal_failure | 密封失效 | 压力、温度 | 渐进式 | 96h |
| electrical_fault | 电气故障 | 电流、温度 | 突发型 | 12h |

## API 接口文档

### 系统控制

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/system/status` | 系统状态 |
| POST | `/api/system/config` | 更新配置（sensor_interval / degradation_speed） |
| POST | `/api/system/inject-fault` | 注入故障（演示用） |
| POST | `/api/system/reset-equipment/<id>` | 重置设备到健康状态 |
| POST | `/api/system/degrade` | 手动加速设备退化 |

**注入故障示例：**

```bash
curl -X POST http://127.0.0.1:5100/api/system/inject-fault \
  -H "Content-Type: application/json" \
  -d '{"equipment_id":"EQ-001","fault_type":"bearing_wear","severity":0.8}'
```

### 设备管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/equipment` | 设备列表（含最新数据和健康度趋势） |
| GET | `/api/equipment/<id>` | 设备详情（含传感器历史、告警、工单、AI 检测） |
| POST | `/api/equipment` | 添加设备 |
| DELETE | `/api/equipment/<id>` | 删除设备 |
| POST | `/api/equipment/<id>/control` | 设备控制（start / stop / maintenance） |

**添加设备示例：**

```bash
curl -X POST http://127.0.0.1:5100/api/equipment \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": "EQ-006",
    "name": "F线风机",
    "type": "motor",
    "location": "F车间-通风系统",
    "manufacturer": "ABB",
    "model": "M3BP",
    "rated_power": "30kW",
    "rated_speed": "1450RPM"
  }'
```

### 传感器数据

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/sensor/<id>/latest` | 最新传感器数据 |
| GET | `/api/sensor/<id>/history?points=100` | 传感器历史数据 |

### AI 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/analysis/<id>` | 综合分析（异常检测 + 故障诊断 + RUL 预测） |
| GET | `/api/analysis/overview` | 全局概览（设备统计、告警统计、健康度分布） |
| GET | `/api/diagnosis/<id>` | 故障诊断 |
| POST | `/api/diagnosis/query` | 按症状查询故障 |

**分析结果示例：**

```bash
curl http://127.0.0.1:5100/api/analysis/EQ-001
```

返回包含：
- `detection` — 健康度评分、风险等级、异常列表、趋势分析
- `fault_diagnosis` — 故障类型、置信度、发展阶段、处置建议
- `rul_prediction` — 剩余寿命预测、置信度、维护建议

### 告警管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/alerts?page=1&per_page=20&level=critical` | 告警列表（支持分页和筛选） |
| POST | `/api/alerts/<id>/acknowledge` | 确认告警 |

### 维修工单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/work-orders?status=open` | 工单列表 |
| POST | `/api/work-orders` | 创建工单 |
| POST | `/api/work-orders/<id>/update` | 更新工单（status / result / technician） |

**更新工单示例：**

```bash
curl -X POST http://127.0.0.1:5100/api/work-orders/WO-001/update \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","result":"更换轴承，振动恢复正常","technician":"张工"}'
```

### 知识图谱

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge-graph` | 图谱全量数据（105 节点 / 156 边） |
| GET | `/api/knowledge-graph/search?q=轴承` | 关键词搜索 |
| GET | `/api/knowledge-graph/node/<id>` | 节点详情及关联关系 |

## 对接真实传感器数据

当前系统使用模拟引擎生成数据。如需对接真实传感器（Modbus TCP / OPC-UA / MQTT / RS485），请参阅 **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)**，包含：

- 完整数据流时序图
- 数据适配器代码（MQTT + HTTP 双模式，替换 SensorSimulator 零改动下游）
- 边缘网关采集脚本示例（Modbus TCP）
- 字段映射与单位转换配置
- 单机 / 分布式部署方案
- 数据质量保障规则

核心设计：数据适配器输出格式与模拟器完全一致，AI 检测、告警、工单等下游模块无需任何改动。

## AI 检测算法说明

### 健康度评分（0-100）

综合以下因素计算：
1. **阈值检测** — 每个传感器值与配置的正常范围 / 警告 / 危险阈值比较
2. **Z-Score 检测** — 基于近 30 个数据点的均值和标准差，检测统计异常
3. **趋势分析** — 近 60 个数据点的变化率和方向（上升 / 下降 / 稳定）

每个异常根据严重程度扣分，最终映射到 0-100 区间。

### 风险等级

| 等级 | 健康度 | 含义 |
|------|--------|------|
| low | >= 70 | 正常运行 |
| medium | 50 - 69 | 需关注 |
| high | 30 - 49 | 需要维护 |
| danger | < 30 | 即将故障 |
| imminent | 快速下降 | 紧急停机 |

### RUL 预测

基于健康度趋势序列（最近 50 个点），使用线性回归拟合退化斜率，外推到危险阈值（30）的时间点。置信度取决于数据量和拟合优度（R²）。

## 常见问题

### 端口被占用

修改 `config.py` 中的 `PORT`，或通过环境变量启动：

```bash
PORT=5200 python3 app.py
```

### 数据库重置

删除 `data/maintenance.db`，重启服务会自动重建数据库并初始化默认设备。

### 告警不触发

- 确认设备状态为 `running`（非 stopped / maintenance 的设备不采集数据）
- 注入故障后需要多次请求 API 触发 `tick_data()` 数据采集
- 可通过 `/api/system/config` 调小 `sensor_interval` 和调大 `degradation_speed` 加速演示

### 模拟器 vs 真实数据

当前为**模拟模式**，所有传感器数据由 `SensorSimulator` 生成。切换到真实数据只需用数据适配器替换 `SensorSimulator`，详见 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)。

## 技术栈

- **后端**：Flask + Flask-CORS
- **数据库**：SQLite（WAL 模式，零配置）
- **前端**：原生 HTML / CSS / JavaScript
- **图表**：ECharts（传感器曲线）+ D3.js（知识图谱力导向图）
- **依赖**：flask, flask-cors, requests（仅 3 个 PyPI 包）

## 许可

本项目仅供学习和演示使用。
