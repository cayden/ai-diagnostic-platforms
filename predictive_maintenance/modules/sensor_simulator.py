"""
传感器数据模拟引擎
模拟生产设备的振动、温度、电流、压力、转速等信号
支持正常 → 退化 → 故障的渐进式演变
"""
import math
import random
import time
from datetime import datetime
from threading import Lock


class SensorSimulator:
    """传感器数据模拟器"""

    def __init__(self, config):
        self.config = config
        self.equipment_states = {}
        self.lock = Lock()
        self.degradation_speed = config.DEGRADATION_SPEED

    def init_equipment_state(self, equipment_id, equipment_type):
        """初始化设备模拟状态"""
        with self.lock:
            eq_config = self.config.EQUIPMENT_TYPES.get(equipment_type, {})
            sensors = eq_config.get("sensors", ["vibration", "temperature", "current"])

            self.equipment_states[equipment_id] = {
                "type": equipment_type,
                "sensors": sensors,
                "running": True,
                "health_factor": 1.0,  # 1.0=完全健康, 0.0=完全故障
                "degradation_rate": 0.0,  # 自然退化速率
                "fault_type": None,
                "fault_severity": 0.0,
                "fault_progress": 0.0,
                "cycle": 0,
                "base_values": self._init_base_values(sensors),
                "noise_seeds": {s: random.random() * 1000 for s in sensors},
                "created_at": datetime.now().isoformat(),
            }

    def _init_base_values(self, sensors):
        """初始化各传感器基线值"""
        base = {}
        defaults = {
            "vibration": 2.5,
            "temperature": 45.0,
            "current": 15.0,
            "pressure": 0.8,
            "rpm": 1500,
            "flow_rate": 100,
            "acoustic": 62.0,
        }
        for s in sensors:
            base[s] = defaults.get(s, 0)
        return base

    def remove_equipment_state(self, equipment_id):
        with self.lock:
            self.equipment_states.pop(equipment_id, None)

    def set_equipment_running(self, equipment_id, running):
        with self.lock:
            if equipment_id in self.equipment_states:
                self.equipment_states[equipment_id]["running"] = running

    def inject_fault(self, equipment_id, fault_type, severity=0.5):
        """注入故障"""
        with self.lock:
            if equipment_id not in self.equipment_states:
                return False
            state = self.equipment_states[equipment_id]
            state["fault_type"] = fault_type
            state["fault_severity"] = severity
            state["fault_progress"] = 0.1  # 从轻微开始
            return True

    def accelerate_degradation(self, equipment_id, speed=3.0):
        """加速退化（用于演示）"""
        with self.lock:
            if equipment_id not in self.equipment_states:
                return False
            state = self.equipment_states[equipment_id]
            state["degradation_rate"] = 0.0008 * speed  # 加速退化
            return True

    def reset_equipment(self, equipment_id):
        """重置设备到健康状态"""
        with self.lock:
            if equipment_id not in self.equipment_states:
                return False
            state = self.equipment_states[equipment_id]
            state["health_factor"] = 1.0
            state["degradation_rate"] = 0.0
            state["fault_type"] = None
            state["fault_severity"] = 0.0
            state["fault_progress"] = 0.0
            state["base_values"] = self._init_base_values(state["sensors"])
            return True

    def generate(self, equipment_id, equipment_type):
        """生成一个采样周期的传感器数据"""
        with self.lock:
            if equipment_id not in self.equipment_states:
                self.init_equipment_state(equipment_id, equipment_type)

            state = self.equipment_states[equipment_id]

            if not state["running"]:
                return self._generate_stopped_data(state)

            state["cycle"] += 1
            cycle = state["cycle"]
            health = state["health_factor"]

            # 自然退化
            if state["degradation_rate"] > 0:
                state["health_factor"] = max(0.1, health - state["degradation_rate"] * self.degradation_speed)
                health = state["health_factor"]

            # 故障进展
            fault_data = {}
            if state["fault_type"] and state["fault_progress"] < 1.0:
                progress_rate = 0.002 * state["fault_severity"] * self.degradation_speed
                state["fault_progress"] = min(1.0, state["fault_progress"] + progress_rate)
                # 故障也降低健康度
                health_impact = state["fault_progress"] * state["fault_severity"] * 0.003
                state["health_factor"] = max(0.05, state["health_factor"] - health_impact)
                health = state["health_factor"]
                fault_data = self._get_fault_effect(state["fault_type"], state["fault_progress"])

            # 生成传感器读数
            readings = {}
            for sensor_type in state["sensors"]:
                base = state["base_values"].get(sensor_type, 0)
                value = self._generate_sensor_value(
                    sensor_type, base, cycle, health, fault_data.get(sensor_type, {})
                )
                readings[sensor_type] = round(value, 2)

            return {
                "timestamp": datetime.now().isoformat(),
                "cycle": cycle,
                "sensors": readings,
                "health_factor": round(health, 4),
                "fault_type": state["fault_type"],
                "fault_progress": round(state["fault_progress"], 3),
            }

    def _generate_stopped_data(self, state):
        """生成停机数据"""
        readings = {}
        for sensor_type in state["sensors"]:
            if sensor_type == "temperature":
                readings[sensor_type] = round(25.0 + random.uniform(-2, 2), 2)
            elif sensor_type == "rpm":
                readings[sensor_type] = 0
            elif sensor_type == "flow_rate":
                readings[sensor_type] = 0
            else:
                readings[sensor_type] = round(random.uniform(0, 0.5), 2)

        return {
            "timestamp": datetime.now().isoformat(),
            "cycle": state["cycle"],
            "sensors": readings,
            "health_factor": round(state["health_factor"], 4),
            "fault_type": state["fault_type"],
            "fault_progress": round(state["fault_progress"], 3),
        }

    def _generate_sensor_value(self, sensor_type, base, cycle, health, fault_effect):
        """生成单个传感器读数"""
        t = cycle * 0.1  # 时间步长

        # 基础波动（正弦 + 噪声）
        noise = random.gauss(0, 1)

        if sensor_type == "vibration":
            # 振动: 基线 + 低频波动 + 噪声
            value = base + math.sin(t * 0.3) * 0.3 + noise * 0.4
            # 健康度下降导致振动增大
            health_factor = (1.0 - health) * 3.5
            value += health_factor
            # 故障影响
            if fault_effect:
                value *= (1 + fault_effect.get("multiplier", 0))
                value += fault_effect.get("offset", 0)

        elif sensor_type == "temperature":
            # 温度: 基线 + 缓慢波动 + 噪声
            value = base + math.sin(t * 0.1) * 1.5 + noise * 0.8
            health_factor = (1.0 - health) * 15
            value += health_factor
            if fault_effect:
                value += fault_effect.get("offset", 0)

        elif sensor_type == "current":
            # 电流: 基线 + 波动 + 噪声
            value = base + math.sin(t * 0.5) * 1.0 + noise * 0.5
            health_factor = (1.0 - health) * 8
            value += health_factor
            if fault_effect:
                value *= (1 + fault_effect.get("multiplier", 0))

        elif sensor_type == "pressure":
            # 压力: 基线 + 小波动
            value = base + math.sin(t * 0.2) * 0.03 + noise * 0.02
            health_factor = (1.0 - health) * 0.15
            value -= health_factor  # 退化导致压力下降
            if fault_effect:
                value += fault_effect.get("offset", 0)

        elif sensor_type == "rpm":
            # 转速: 稳定值 ± 小波动
            value = base + noise * 5
            health_factor = (1.0 - health) * 30
            value -= health_factor
            if fault_effect:
                value += fault_effect.get("offset", 0)

        elif sensor_type == "flow_rate":
            # 流量: 基线 ± 波动
            value = base + math.sin(t * 0.15) * 3 + noise * 2
            health_factor = (1.0 - health) * 20
            value -= health_factor
            if fault_effect:
                value += fault_effect.get("offset", 0)

        elif sensor_type == "acoustic":
            # 声学: 基线 + 波动
            value = base + math.sin(t * 0.25) * 2 + noise * 1.5
            health_factor = (1.0 - health) * 12
            value += health_factor
            if fault_effect:
                value += fault_effect.get("offset", 0)
        else:
            value = base + noise

        return max(0, value)

    def _get_fault_effect(self, fault_type, progress):
        """获取故障对各传感器的影响"""
        effects = {
            "bearing_wear": {
                "vibration": {"multiplier": progress * 2.5, "offset": progress * 3},
                "temperature": {"offset": progress * 12},
                "acoustic": {"offset": progress * 15},
            },
            "imbalance": {
                "vibration": {"multiplier": progress * 3.0, "offset": progress * 4},
                "rpm": {"offset": -progress * 80},
            },
            "misalignment": {
                "vibration": {"multiplier": progress * 2.0, "offset": progress * 2},
                "temperature": {"offset": progress * 8},
            },
            "overload": {
                "current": {"multiplier": progress * 0.8},
                "temperature": {"offset": progress * 18},
            },
            "lubrication_failure": {
                "temperature": {"offset": progress * 15},
                "vibration": {"multiplier": progress * 1.5},
                "acoustic": {"offset": progress * 18},
            },
            "cavitation": {
                "vibration": {"multiplier": progress * 2.0, "offset": progress * 2},
                "pressure": {"offset": -progress * 0.3},
                "flow_rate": {"offset": -progress * 25},
                "acoustic": {"offset": progress * 20},
            },
            "seal_failure": {
                "pressure": {"offset": -progress * 0.25},
                "temperature": {"offset": progress * 5},
            },
            "electrical_fault": {
                "current": {"multiplier": progress * 1.5},
                "temperature": {"offset": progress * 20},
            },
        }
        return effects.get(fault_type, {})
