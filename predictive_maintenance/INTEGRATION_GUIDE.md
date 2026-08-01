# 预测性维护平台 — 真实传感器数据对接方案

## 一、现状与目标

### 当前架构

```
SensorSimulator（模拟引擎）→ tick_data() → Database → AnomalyDetector → 告警/工单
```

系统目前使用 `SensorSimulator` 生成模拟数据，数据格式为：

```json
{
    "timestamp": "2026-08-01T09:30:00",
    "cycle": 142,
    "sensors": {
        "vibration": 2.5,      // mm/s
        "temperature": 45.0,    // °C
        "current": 15.0,        // A
        "pressure": 0.8,        // MPa
        "rpm": 1500,            // RPM
        "flow_rate": 100,       // L/min
        "acoustic": 62.0        // dB
    },
    "health_factor": 1.0,
    "fault_type": null,
    "fault_progress": 0.0
}
```

### 目标架构

```
真实传感器/PLC → 边缘网关 → MQTT/消息队列 → 数据适配器 → 平台API → AI检测 → 告警/工单
                                                                    ↑
                                                         替换 SensorSimulator
```

**核心原则**：数据适配器输出格式与 `SensorSimulator.generate()` 完全一致，平台其余模块零改动。

---

## 二、数据采集层 — 现场设备对接

### 2.1 支持的工业协议

| 协议 | 适用场景 | 采集方式 | 推荐库 |
|------|---------|---------|--------|
| **Modbus TCP** | PLC、变频器、传感器模块 | 轮询读取寄存器 | `pymodbus` |
| **OPC-UA** | SCADA、DCS、高端PLC | 订阅数据变化 | `asyncua` |
| **MQTT** | IoT网关、无线传感器 | 发布/订阅 | `paho-mqtt` |
| **REST API** | 智能传感器、第三方系统 | HTTP轮询 | `requests` |
| **串口 RS485** | 老旧设备、振动传感器 | 串口通信 | `pyserial` |

### 2.2 传感器选型建议

| 传感器类型 | 推荐型号 | 接口 | 输出 |
|-----------|---------|------|------|
| 振动 | 加速度计 IEPE / ADXL355 | Modbus/模拟量 | mm/s (ISO 10816) |
| 温度 | PT100 / 热电偶 | Modbus RTU | °C |
| 电流 | 电流互感器 / 霍尔传感器 | Modbus/4-20mA | A |
| 压力 | 压力变送器 | 4-20mA/Modbus | MPa |
| 转速 | 编码器 / 电涡流 | 脉冲/Modbus | RPM |
| 流量 | 电磁流量计 | Modbus/脉冲 | L/min |
| 声学 | 声级计 / 麦克风阵列 | Modbus/模拟量 | dB |

### 2.3 边缘网关部署

```
现场设备
  ├── 电机 (Modbus TCP: 192.168.1.10:502)
  ├── 水泵 (OPC-UA: opc.tcp://192.168.1.20:4840)
  ├── 轴承 (RS485: /dev/ttyUSB0, 9600bps)
  └── 压缩机 (MQTT: 192.168.1.30:1883)
         │
    ┌────┴────┐
    │ 边缘网关 │  ← 工业IPC / 树莓派 / 边缘计算盒子
    └────┬────┘
         │ MQTT (统一协议上报)
    ┌────┴────┐
    │  Broker  │  ← Mosquitto / EMQX / RabbitMQ
    └────┬────┘
         │
    数据适配器 (本系统)
```

**边缘网关职责**：
1. 多协议统一采集（Modbus/OPC-UA/串口 → 统一数据格式）
2. 数据预处理（滤波去噪、异常值剔除、时间戳对齐）
3. 本地缓存（断网续传）
4. MQTT 上报（QoS=1 保证可达）

---

## 三、数据适配器设计（核心对接模块）

### 3.1 模块定位

数据适配器是**替换 `SensorSimulator`** 的适配层，从 MQTT/消息队列消费真实传感器数据，转换为平台标准格式后通过 API 推入系统。

### 3.2 数据适配器代码

```python
# modules/data_adapter.py
"""
真实传感器数据适配器
从 MQTT Broker 消费传感器数据，转换为平台标准格式
替换 SensorSimulator，平台其余模块零改动
"""
import json
import time
import threading
import paho.mqtt.client as mqtt
from datetime import datetime
from collections import defaultdict


class DataAdapter:
    """真实数据适配器 — 替换 SensorSimulator"""

    def __init__(self, config):
        self.config = config
        self.mqtt_host = config.MQTT_HOST
        self.mqtt_port = config.MQTT_PORT
        self.mqtt_topics = config.MQTT_TOPICS  # ["sensors/+/data"]

        # 设备配置：设备ID → 传感器字段映射
        self.field_mappings = config.FIELD_MAPPINGS

        # 缓存：每个设备最新一组传感器读数
        self.data_buffer = defaultdict(dict)
        self.lock = threading.Lock()
        self.client = None
        self.connected = False

        # 兼容 simulator 的状态字段
        self.equipment_states = {}

    def init_equipment_state(self, equipment_id, equipment_type):
        """兼容 simulator 接口"""
        self.equipment_states[equipment_id] = {
            "type": equipment_type,
            "sensors": self.config.EQUIPMENT_TYPES.get(
                equipment_type, {}
            ).get("sensors", ["vibration", "temperature"]),
            "running": True,
            "cycle": 0,
        }

    def remove_equipment_state(self, equipment_id):
        self.equipment_states.pop(equipment_id, None)

    def set_equipment_running(self, equipment_id, running):
        if equipment_id in self.equipment_states:
            self.equipment_states[equipment_id]["running"] = running

    def inject_fault(self, equipment_id, fault_type, severity=0.5):
        """真实模式下不支持注入故障，仅记录"""
        print(f"[DataAdapter] 真实模式不支持注入故障: {equipment_id}/{fault_type}")
        return False

    def reset_equipment(self, equipment_id):
        """重置缓冲"""
        with self.lock:
            self.data_buffer.pop(equipment_id, None)

    def generate(self, equipment_id, equipment_type):
        """
        生成一个采样周期的传感器数据
        兼容 SensorSimulator.generate() 接口
        返回真实采集的数据而非模拟数据
        """
        if equipment_id not in self.equipment_states:
            self.init_equipment_state(equipment_id, equipment_type)

        state = self.equipment_states[equipment_id]
        if not state["running"]:
            return self._generate_stopped_data(state)

        state["cycle"] += 1

        with self.lock:
            raw = dict(self.data_buffer.get(equipment_id, {}))

        # 字段映射 + 单位转换
        mapping = self.field_mappings.get(equipment_id, {})
        readings = {}
        for platform_field, source_config in mapping.items():
            raw_value = raw.get(source_config["field"])
            if raw_value is not None:
                # 单位转换
                scale = source_config.get("scale", 1.0)
                offset = source_config.get("offset", 0.0)
                value = raw_value * scale + offset
                readings[platform_field] = round(value, 2)

        # 缺失字段用上次值或默认值填充
        for sensor_type in state["sensors"]:
            if sensor_type not in readings:
                readings[sensor_type] = 0.0

        return {
            "timestamp": datetime.now().isoformat(),
            "cycle": state["cycle"],
            "sensors": readings,
            "health_factor": 1.0,  # 由 AnomalyDetector 计算
            "fault_type": None,
            "fault_progress": 0.0,
        }

    def _generate_stopped_data(self, state):
        readings = {}
        for sensor_type in state["sensors"]:
            readings[sensor_type] = 0.0
        return {
            "timestamp": datetime.now().isoformat(),
            "cycle": state["cycle"],
            "sensors": readings,
            "health_factor": 0.0,
            "fault_type": None,
            "fault_progress": 0.0,
        }

    # ========== MQTT 消费 ==========

    def start_mqtt_client(self):
        """启动 MQTT 客户端，订阅传感器数据"""
        self.client = mqtt.Client(client_id="predictive_maintenance")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # 认证（如需）
        if self.config.MQTT_USERNAME:
            self.client.username_pw_set(
                self.config.MQTT_USERNAME, self.config.MQTT_PASSWORD
            )

        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
        print(f"[DataAdapter] MQTT 客户端已启动 → {self.mqtt_host}:{self.mqtt_port}")

    def stop_mqtt_client(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)
        if self.connected:
            for topic in self.mqtt_topics:
                client.subscribe(topic, qos=1)
            print(f"[DataAdapter] MQTT 已连接，订阅: {self.mqtt_topics}")
        else:
            print(f"[DataAdapter] MQTT 连接失败, rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            print(f"[DataAdapter] MQTT 意外断开, rc={rc}, 将自动重连")

    def _on_message(self, client, userdata, msg):
        """处理收到的传感器数据"""
        try:
            # 解析 topic: sensors/{equipment_id}/data
            parts = msg.topic.split("/")
            if len(parts) >= 3:
                equipment_id = parts[1]
            else:
                return

            payload = json.loads(msg.payload.decode())

            # 写入缓冲区
            with self.lock:
                self.data_buffer[equipment_id].update(payload)

        except Exception as e:
            print(f"[DataAdapter] 消息处理错误: {e}")


# ========== 备选：HTTP 轮询适配器 ==========

class HttpPollingAdapter:
    """
    HTTP 轮询适配器
    适用于不支持 MQTT 的场景，定时从第三方 API 拉取数据
    """

    def __init__(self, config):
        self.config = config
        self.endpoints = config.HTTP_ENDPOINTS  # {eq_id: {"url": "...", "interval": 3}}
        self.field_mappings = config.FIELD_MAPPINGS
        self.data_buffer = defaultdict(dict)
        self.lock = threading.Lock()
        self.equipment_states = {}

    def init_equipment_state(self, equipment_id, equipment_type):
        self.equipment_states[equipment_id] = {
            "type": equipment_type,
            "sensors": self.config.EQUIPMENT_TYPES.get(
                equipment_type, {}
            ).get("sensors", ["vibration", "temperature"]),
            "running": True,
            "cycle": 0,
        }

    def generate(self, equipment_id, equipment_type):
        """从最新缓冲读取数据（兼容 simulator 接口）"""
        import requests

        if equipment_id not in self.equipment_states:
            self.init_equipment_state(equipment_id, equipment_type)

        state = self.equipment_states[equipment_id]
        state["cycle"] += 1

        endpoint = self.endpoints.get(equipment_id)
        if not endpoint:
            return self._fallback_data(state)

        try:
            resp = requests.get(endpoint["url"], timeout=3)
            raw = resp.json()

            mapping = self.field_mappings.get(equipment_id, {})
            readings = {}
            for platform_field, source_config in mapping.items():
                raw_value = raw.get(source_config["field"])
                if raw_value is not None:
                    scale = source_config.get("scale", 1.0)
                    offset = source_config.get("offset", 0.0)
                    readings[platform_field] = round(
                        raw_value * scale + offset, 2
                    )

            for sensor_type in state["sensors"]:
                if sensor_type not in readings:
                    readings[sensor_type] = 0.0

            return {
                "timestamp": datetime.now().isoformat(),
                "cycle": state["cycle"],
                "sensors": readings,
                "health_factor": 1.0,
                "fault_type": None,
                "fault_progress": 0.0,
            }
        except Exception as e:
            print(f"[HttpPolling] {equipment_id} 采集失败: {e}")
            return self._fallback_data(state)

    def _fallback_data(self, state):
        readings = {s: 0.0 for s in state["sensors"]}
        return {
            "timestamp": datetime.now().isoformat(),
            "cycle": state["cycle"],
            "sensors": readings,
            "health_factor": 0.0,
            "fault_type": None,
            "fault_progress": 0.0,
        }

    def set_equipment_running(self, equipment_id, running):
        if equipment_id in self.equipment_states:
            self.equipment_states[equipment_id]["running"] = running

    def remove_equipment_state(self, equipment_id):
        self.equipment_states.pop(equipment_id, None)

    def inject_fault(self, equipment_id, fault_type, severity=0.5):
        return False

    def reset_equipment(self, equipment_id):
        pass
```

### 3.3 配置扩展

在 `config.py` 中新增以下配置：

```python
# ========== 数据源配置 ==========

# 数据源模式：simulation(模拟) / mqtt(MQTT真实) / http(HTTP轮询)
DATA_SOURCE = "simulation"

# MQTT 配置
MQTT_HOST = "192.168.1.100"
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
MQTT_TOPICS = ["sensors/+/data"]

# HTTP 轮询端点
HTTP_ENDPOINTS = {
    "EQ-001": {"url": "http://192.168.1.10:8080/api/sensors", "interval": 3},
    "EQ-002": {"url": "http://192.168.1.20:8080/api/sensors", "interval": 3},
}

# 字段映射：平台字段 → 设备原始字段
# 每个设备配置其传感器在原始数据中的字段名、缩放系数和偏移量
FIELD_MAPPINGS = {
    "EQ-001": {
        "vibration":     {"field": "vib_rms",   "scale": 1.0,  "offset": 0.0},   # 原始 mm/s → 平台 mm/s
        "temperature":   {"field": "temp_c",    "scale": 1.0,  "offset": 0.0},   # 原始 °C → 平台 °C
        "current":       {"field": "motor_i",   "scale": 1.0,  "offset": 0.0},   # 原始 A → 平台 A
        "rpm":           {"field": "speed",     "scale": 1.0,  "offset": 0.0},   # 原始 RPM → 平台 RPM
    },
    "EQ-002": {
        "vibration":     {"field": "vib_rms",   "scale": 1.0,  "offset": 0.0},
        "temperature":   {"field": "temp_c",    "scale": 1.0,  "offset": 0.0},
        "pressure":      {"field": "p_out",     "scale": 0.001, "offset": 0.0},  # 原始 kPa → 平台 MPa
        "current":       {"field": "motor_i",   "scale": 1.0,  "offset": 0.0},
        "flow_rate":     {"field": "flow",      "scale": 1.0,  "offset": 0.0},
    },
}
```

### 3.4 平台切换逻辑

在 `app.py` 初始化时，根据 `DATA_SOURCE` 配置选择数据源：

```python
# app.py 初始化部分

if Config.DATA_SOURCE == "mqtt":
    from modules.data_adapter import DataAdapter
    simulator = DataAdapter(Config)  # 替换 SensorSimulator
    simulator.start_mqtt_client()
    print("[数据源] MQTT 真实采集模式")
elif Config.DATA_SOURCE == "http":
    from modules.data_adapter import HttpPollingAdapter
    simulator = HttpPollingAdapter(Config)
    print("[数据源] HTTP 轮询采集模式")
else:
    from modules.sensor_simulator import SensorSimulator
    simulator = SensorSimulator(Config)
    print("[数据源] 模拟模式（演示用）")
```

**关键设计**：`DataAdapter` 和 `HttpPollingAdapter` 实现了与 `SensorSimulator` 相同的接口（`init_equipment_state`、`generate`、`set_equipment_running` 等），因此平台其余代码（`tick_data`、`_run_one_data_cycle`、`AnomalyDetector`、`Database`、前端）**零改动**。

---

## 四、数据上报 API（平台侧接收）

### 4.1 REST API 上报接口

平台新增一个接收推送数据的 API 端点，供边缘网关或适配器调用：

```
POST /api/sensor/upload
```

**请求体**：

```json
{
    "equipment_id": "EQ-001",
    "timestamp": "2026-08-01T09:30:00",
    "sensors": {
        "vibration": 3.2,
        "temperature": 48.5,
        "current": 16.2,
        "rpm": 1498
    }
}
```

**实现**（添加到 `app.py`）：

```python
@app.route("/api/sensor/upload", methods=["POST"])
def upload_sensor_data():
    """接收外部推送的传感器数据"""
    data = request.get_json()

    equipment_id = data.get("equipment_id")
    if not equipment_id:
        return jsonify({"error": "缺少 equipment_id"}), 400

    eq = db.get_equipment(equipment_id)
    if not eq:
        return jsonify({"error": "设备不存在"}), 404

    sensor_data = {
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        "cycle": 0,
        "sensors": data.get("sensors", {}),
        "health_factor": 1.0,
        "fault_type": None,
        "fault_progress": 0.0,
    }

    # 存入数据库
    db.add_sensor_data(equipment_id, sensor_data)

    # 执行 AI 检测
    recent_data = db.get_recent_sensor_data(equipment_id, Config.ANOMALY_WINDOW)
    detection_result = detector.detect(equipment_id, eq["type"], recent_data)

    if detection_result["health_score"] is not None:
        db.update_equipment_health(equipment_id, detection_result["health_score"])

    return jsonify({
        "success": True,
        "health_score": detection_result.get("health_score"),
        "risk_level": detection_result.get("risk_level"),
        "anomalies": detection_result.get("anomalies", []),
    })
```

### 4.2 边缘网关上报脚本示例

```python
# edge_gateway.py — 部署在边缘网关上
"""
边缘网关数据采集脚本
从 Modbus/OPC-UA 读取传感器数据，通过 MQTT 上报
"""
import json
import time
import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient
from datetime import datetime

# 设备配置
DEVICES = {
    "EQ-001": {
        "name": "1号电机",
        "ip": "192.168.1.10",
        "port": 502,
        "registers": {
            "vibration":   {"addr": 0, "count": 1, "scale": 0.01},   # 寄存器0, 缩放0.01
            "temperature": {"addr": 1, "count": 1, "scale": 0.1},
            "current":     {"addr": 2, "count": 1, "scale": 0.1},
            "rpm":         {"addr": 3, "count": 1, "scale": 1.0},
        },
    },
}

MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
SAMPLE_INTERVAL = 3  # 秒


def collect_and_publish():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    while True:
        for eq_id, config in DEVICES.items():
            try:
                modbus = ModbusTcpClient(config["ip"], config["port"])
                modbus.connect()

                readings = {}
                for sensor, reg_config in config["registers"].items():
                    result = modbus.read_holding_registers(
                        reg_config["addr"], reg_config["count"]
                    )
                    if not result.isError():
                        raw = result.registers[0]
                        readings[sensor] = round(raw * reg_config["scale"], 2)

                modbus.close()

                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "sensors": readings,
                }

                topic = f"sensors/{eq_id}/data"
                client.publish(topic, json.dumps(payload), qos=1)
                print(f"[上报] {eq_id}: {readings}")

            except Exception as e:
                print(f"[错误] {eq_id} 采集失败: {e}")

        time.sleep(SAMPLE_INTERVAL)


if __name__ == "__main__":
    collect_and_publish()
```

---

## 五、数据流完整时序

时序图展示了从传感器采集到告警生成的完整 15 步流程：

| 步骤 | 发起方 → 接收方 | 动作 | 说明 |
|------|----------------|------|------|
| 1 | 传感器/PLC → 边缘网关 | Modbus/OPC-UA 采集 | 轮询读取寄存器，获取原始传感器值 |
| 2 | 边缘网关 → 自身 | 数据预处理 | 滤波去噪、异常值剔除、时间戳对齐 |
| 3 | 边缘网关 → MQTT Broker | Publish 上报 | JSON 格式发布到 `sensors/{eq_id}/data` |
| 4 | MQTT Broker → 数据适配器 | Subscribe 推送 | QoS=1 保证消息送达 |
| 5 | 数据适配器 → 自身 | 字段映射 + 单位转换 | 原始字段名 → 平台标准字段，单位转换 |
| 6 | 数据适配器 → 平台(Flask) | POST /api/sensor/upload | 或由 tick_data() 主动从缓冲读取 |
| 7 | 平台 → 自身 | AI 异常检测 | 阈值检测 + Z-score 统计检测 |
| 8 | 平台 → 自身 | 趋势分析 + RUL 预测 | 退化曲线拟合，剩余寿命估算 |
| 9 | 平台 → DB | 写入数据库 + 更新健康度 | sensor_data 表 + equipment 表 |
| 10 | 平台 → 自身 | 健康度判断 | health < 70 触发告警流程 |
| 11 | 平台 → 自身 | 故障诊断 | 征兆-权重矩阵推理，匹配故障类型 |
| 12 | 平台 → DB/告警 | 生成告警 + 自动工单 | 写入 alerts 表 + work_orders 表 |
| 13 | DB → 平台 | 返回分析结果 | 响应数据给 API 调用方 |
| 14 | 平台 → 数据适配器 | HTTP Response | 返回健康度、风险等级、异常列表 |
| 15 | 数据适配器 → MQTT Broker | ACK (QoS=1) | 确认消息消费完成 |

---

## 六、部署方案

### 6.1 单机部署（小型场景）

```
┌─────────────────────────────────────┐
│           单台服务器                │
│                                     │
│  Mosquitto (MQTT Broker)  :1883     │
│  Flask 预测维护平台       :5100     │
│  DataAdapter (MQTT消费者)           │
│  SQLite 数据库                      │
│  Nginx (反向代理)         :80       │
└─────────────────────────────────────┘
        ↑ MQTT
┌───────────────┐
│  边缘网关 x N  │
│  (采集脚本)    │
└───────────────┘
```

### 6.2 分布式部署（生产环境）

```
                    ┌──────────────┐
                    │  负载均衡器   │
                    └──────┬───────┘
               ┌──────────┼──────────┐
               │          │          │
     ┌─────────┴──┐ ┌─────┴────┐ ┌──┴─────────┐
     │ Flask x2  │ │ Flask x2 │ │ Flask x2   │
     │ (Gunicorn) │ │          │ │            │
     └─────────┬──┘ └─────┬────┘ └──┬─────────┘
               │          │          │
     ┌─────────┴──────────┴──────────┴─────────┐
     │          Redis (消息缓冲/共享状态)        │
     └─────────────────────┬───────────────────┘
                           │
     ┌─────────────────────┴───────────────────┐
     │        PostgreSQL / TimescaleDB          │
     │        (时序数据 + 告警 + 工单)           │
     └─────────────────────────────────────────┘
                           ↑ MQTT
     ┌─────────────────────┴───────────────────┐
     │           EMQX 集群 (MQTT Broker)       │
     └─────────────────────┬──────────────────┘
                           ↑
     ┌──────────┬──────────┼──────────┬───────┐
     │ 网关1    │ 网关2   │ 网关3   │ 网关N  │
     │(Modbus)  │(OPC-UA) │(串口)   │(REST) │
     └──────────┴──────────┴──────────┴───────┘
```

### 6.3 依赖安装

```bash
# 安装 MQTT 客户端
pip install paho-mqtt

# 安装 Modbus 客户端（边缘网关用）
pip install pymodbus

# 安装 OPC-UA 客户端（边缘网关用）
pip install asyncua

# 安装 Mosquitto（Broker，如需本地部署）
# macOS:  brew install mosquitto && brew services start mosquitto
# Linux:  apt install mosquitto && systemctl start mosquitto
# Docker: docker run -d -p 1883:1883 eclipse-mosquitto
```

---

## 七、数据质量保障

### 7.1 数据校验规则

| 规则 | 处理方式 |
|------|---------|
| 数值超出物理范围（如温度 > 200°C） | 丢弃，标记为异常 |
| 数据缺失（某传感器未上报） | 用上次值填充，标记 `stale=true` |
| 时间戳跳跃/回退 | 以服务器时间为准，标记 `time_skew` |
| 采样频率不稳定 | 适配器侧做重采样到固定频率 |
| 通信中断 | 边缘网关本地缓存，恢复后批量补传 |

### 7.2 心跳监控

数据适配器定期检查每个设备的数据新鲜度：

```python
# 心跳检测逻辑（添加到 data_adapter.py）
def check_data_freshness(self, max_age_seconds=30):
    """检查设备数据是否新鲜"""
    now = time.time()
    stale_devices = []
    for eq_id, buffer in self.data_buffer.items():
        ts = buffer.get("_timestamp")
        if ts and (now - ts) > max_age_seconds:
            stale_devices.append(eq_id)
    return stale_devices
```

---

## 八、对接清单

| 序号 | 任务 | 负责 | 产出 |
|------|------|------|------|
| 1 | 确认设备清单和传感器类型 | 现场/运维 | 设备台账 |
| 2 | 确认通信协议和地址 | 现场/自动化 | 寄存器映射表 |
| 3 | 部署 MQTT Broker | IT | Mosquitto/EMQX |
| 4 | 编写边缘网关采集脚本 | 自动化 | edge_gateway.py |
| 5 | 配置字段映射 | 开发 | config.py FIELD_MAPPINGS |
| 6 | 切换 DATA_SOURCE = "mqtt" | 开发 | config.py |
| 7 | 部署 data_adapter.py | 开发 | 平台模块 |
| 8 | 新增 /api/sensor/upload 接口 | 开发 | app.py |
| 9 | 联调测试 | 全员 | 测试报告 |
| 10 | 压力测试 + 上线 | 运维 | 生产环境 |
