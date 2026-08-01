"""
主 Flask 应用 - 生产设备预测性维护与智能运维平台
"""
import os
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import Config
from modules.database import Database
from modules.sensor_simulator import SensorSimulator
from modules.anomaly_detector import AnomalyDetector
from modules.fault_diagnosis import FaultDiagnosis
from modules.knowledge_graph import FaultKnowledgeGraph

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
CORS(app)

# 初始化模块
db = Database(Config.DB_PATH)
simulator = SensorSimulator(Config)
detector = AnomalyDetector(Config)
diagnosis = FaultDiagnosis(Config)
kg = FaultKnowledgeGraph()

# 确保目录存在
os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

# ========== 初始化设备 ==========
def init_equipment():
    """初始化默认设备"""
    existing = db.get_all_equipment()
    if not existing:
        default_equipment = [
        {
            "equipment_id": "EQ-001",
            "name": "A线主电机",
            "type": "motor",
            "location": "A车间-1号产线",
            "manufacturer": "西门子",
            "model": "1LE0003",
            "install_date": "2023-06-15",
            "rated_power": "55kW",
            "rated_speed": "1500RPM",
            "status": "running",
        },
        {
            "equipment_id": "EQ-002",
            "name": "B线循环水泵",
            "type": "pump",
            "location": "B车间-冷却系统",
            "manufacturer": "格兰富",
            "model": "NK200-400",
            "install_date": "2022-11-20",
            "rated_power": "37kW",
            "rated_speed": "1480RPM",
            "status": "running",
        },
        {
            "equipment_id": "EQ-003",
            "name": "C线主轴轴承",
            "type": "bearing",
            "location": "C车间-精密加工中心",
            "manufacturer": "SKF",
            "model": "NU2330ECMA",
            "install_date": "2024-01-10",
            "rated_power": "-",
            "rated_speed": "2400RPM",
            "status": "running",
        },
        {
            "equipment_id": "EQ-004",
            "name": "D线空压机",
            "type": "compressor",
            "location": "D车间-气源系统",
            "manufacturer": "阿特拉斯",
            "model": "GA75VSD+",
            "install_date": "2023-03-08",
            "rated_power": "75kW",
            "rated_speed": "2950RPM",
            "status": "running",
        },
        {
            "equipment_id": "EQ-005",
            "name": "E线减速齿轮箱",
            "type": "gearbox",
            "location": "E车间-传动系统",
            "manufacturer": "SEW",
            "model": "K107",
            "install_date": "2023-09-01",
            "rated_power": "22kW",
            "rated_speed": "1450RPM",
            "status": "running",
        },
        ]

        for eq_data in default_equipment:
            db.add_equipment(eq_data)

    # 始终初始化模拟器状态
    for eq in db.get_all_equipment():
        simulator.init_equipment_state(eq["equipment_id"], eq["type"])

    print(f"[初始化] 已加载 {len(db.get_all_equipment())} 台设备")


init_equipment()


# ========== 按需数据采集 ==========
import time as _time_module
_last_data_tick = 0.0


def tick_data():
    """按需生成数据采集周期（补齐丢失的周期）"""
    global _last_data_tick
    now = _time_module.time()
    if _last_data_tick == 0.0:
        _last_data_tick = now - Config.SENSOR_INTERVAL

    elapsed = now - _last_data_tick
    cycles_to_run = int(elapsed / Config.SENSOR_INTERVAL)
    if cycles_to_run < 1:
        return

    _last_data_tick = now
    # 限制单次最多生成10个周期，避免请求超时
    cycles_to_run = min(cycles_to_run, 10)

    for _ in range(cycles_to_run):
        _run_one_data_cycle()


def _run_one_data_cycle():
    """执行一个数据采集周期"""
    try:
        equipment_list = db.get_all_equipment()
        for eq in equipment_list:
            if eq["status"] != "running":
                continue

            eq_id = eq["equipment_id"]
            eq_type = eq["type"]

            sensor_data = simulator.generate(eq_id, eq_type)
            db.add_sensor_data(eq_id, sensor_data)

            recent_data = db.get_recent_sensor_data(eq_id, Config.ANOMALY_WINDOW)
            detection_result = detector.detect(eq_id, eq_type, recent_data)

            if detection_result["health_score"] is not None:
                db.update_equipment_health(eq_id, detection_result["health_score"])

                health = detection_result["health_score"]
                if health < Config.HEALTH_THRESHOLD_WARN:
                    last_alert = db.get_last_alert_time(eq_id)
                    if last_alert:
                        cooldown_passed = (datetime.now() - last_alert).total_seconds() > Config.ALERT_COOLDOWN
                    else:
                        cooldown_passed = True

                    if cooldown_passed:
                        fault_result = diagnosis.diagnose(
                            equipment_type=eq_type,
                            sensor_data=sensor_data,
                            detection_result=detection_result,
                        )

                        alert_level = "warning"
                        if health < Config.HEALTH_THRESHOLD_CRIT:
                            alert_level = "critical"
                        if health < Config.HEALTH_THRESHOLD_FAIL:
                            alert_level = "emergency"

                        db.add_alert(
                            equipment_id=eq_id,
                            equipment_name=eq["name"],
                            level=alert_level,
                            health_score=health,
                            fault_type=fault_result.get("fault_type", "unknown"),
                            fault_name=fault_result.get("fault_name", "未知故障"),
                            description=fault_result.get("description", ""),
                            recommendations=fault_result.get("recommendations", []),
                            sensor_snapshot=sensor_data,
                            rul_hours=detection_result.get("rul_hours"),
                            rul_confidence=detection_result.get("rul_confidence"),
                        )

                        if health < Config.HEALTH_THRESHOLD_CRIT:
                            existing_orders = db.get_open_work_orders(eq_id)
                            if not existing_orders:
                                db.create_work_order(
                                    equipment_id=eq_id,
                                    equipment_name=eq["name"],
                                    fault_type=fault_result.get("fault_type", "unknown"),
                                    fault_name=fault_result.get("fault_name", "未知故障"),
                                    priority="urgent" if health < Config.HEALTH_THRESHOLD_FAIL else "high",
                                    description=fault_result.get("description", ""),
                                    recommendations=fault_result.get("recommendations", []),
                                )
    except Exception as e:
        print(f"[数据采集错误] {e}")


print("[初始化] 按需数据采集模式已启用")


# ==================== 页面路由 ====================

@app.route("/")
def index():
    return render_template("index.html")


# ==================== 设备管理 API ====================

@app.route("/api/equipment", methods=["GET"])
def get_equipment():
    tick_data()  # 按需生成数据
    equipment = db.get_all_equipment()
    # 附带最新传感器数据和健康度趋势
    for eq in equipment:
        latest = db.get_latest_sensor_data(eq["equipment_id"])
        eq["latest_data"] = latest
        health_trend = db.get_health_trend(eq["equipment_id"], points=30)
        eq["health_trend"] = health_trend
    return jsonify({"success": True, "equipment": equipment})


@app.route("/api/equipment/<equipment_id>", methods=["GET"])
def get_equipment_detail(equipment_id):
    tick_data()  # 按需生成数据
    eq = db.get_equipment(equipment_id)
    if not eq:
        return jsonify({"error": "设备不存在"}), 404

    # 获取传感器历史数据
    sensor_history = db.get_sensor_history(equipment_id, points=Config.HISTORY_RETENTION)
    # 获取健康度趋势
    health_trend = db.get_health_trend(equipment_id, points=100)
    # 获取最新告警
    alerts = db.get_alerts_by_equipment(equipment_id, limit=5)
    # 获取工单
    work_orders = db.get_work_orders_by_equipment(equipment_id, limit=5)
    # AI 检测结果
    recent_data = db.get_recent_sensor_data(equipment_id, Config.ANOMALY_WINDOW)
    detection = detector.detect(equipment_id, eq["type"], recent_data)

    return jsonify({
        "success": True,
        "equipment": eq,
        "sensor_history": sensor_history,
        "health_trend": health_trend,
        "recent_alerts": alerts,
        "work_orders": work_orders,
        "detection": detection,
    })


@app.route("/api/equipment", methods=["POST"])
def add_equipment():
    data = request.json
    equipment_id = data.get("equipment_id", f"EQ-{datetime.now().strftime('%H%M%S')}")
    data["equipment_id"] = equipment_id
    data.setdefault("status", "running")

    success = db.add_equipment(data)
    if success:
        simulator.init_equipment_state(equipment_id, data["type"])
        return jsonify({"success": True, "equipment_id": equipment_id})
    return jsonify({"error": "添加失败"}), 400


@app.route("/api/equipment/<equipment_id>", methods=["DELETE"])
def delete_equipment(equipment_id):
    success = db.delete_equipment(equipment_id)
    if success:
        simulator.remove_equipment_state(equipment_id)
        return jsonify({"success": True})
    return jsonify({"error": "删除失败"}), 400


@app.route("/api/equipment/<equipment_id>/control", methods=["POST"])
def control_equipment(equipment_id):
    """控制设备状态：启动/停止/维护"""
    action = request.json.get("action")
    eq = db.get_equipment(equipment_id)
    if not eq:
        return jsonify({"error": "设备不存在"}), 404

    if action == "start":
        db.update_equipment_status(equipment_id, "running")
        simulator.set_equipment_running(eq["equipment_id"], True)
    elif action == "stop":
        db.update_equipment_status(equipment_id, "stopped")
        simulator.set_equipment_running(equipment_id, False)
    elif action == "maintenance":
        db.update_equipment_status(equipment_id, "maintenance")
        simulator.set_equipment_running(equipment_id, False)

    return jsonify({"success": True, "status": action})


# ==================== 传感器数据 API ====================

@app.route("/api/sensor/<equipment_id>/latest", methods=["GET"])
def get_latest_sensor(equipment_id):
    data = db.get_latest_sensor_data(equipment_id)
    return jsonify({"success": True, "data": data})


@app.route("/api/sensor/<equipment_id>/history", methods=["GET"])
def get_sensor_history(equipment_id):
    points = int(request.args.get("points", 100))
    history = db.get_sensor_history(equipment_id, points=points)
    return jsonify({"success": True, "history": history})


# ==================== 告警 API ====================

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    level = request.args.get("level", "")
    equipment_id = request.args.get("equipment_id", "")
    acknowledged = request.args.get("acknowledged", "")

    alerts, total = db.get_alerts(
        page=page, per_page=per_page, level=level,
        equipment_id=equipment_id, acknowledged=acknowledged,
    )
    return jsonify({
        "success": True, "alerts": alerts, "total": total,
        "page": page, "per_page": per_page,
    })


@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    handler = request.json.get("handler", "")
    success = db.acknowledge_alert(alert_id, handler)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "操作失败"}), 400


# ==================== 工单 API ====================

@app.route("/api/work-orders", methods=["GET"])
def get_work_orders():
    status = request.args.get("status", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    orders, total = db.get_work_orders(status=status, page=page, per_page=per_page)
    return jsonify({
        "success": True, "orders": orders, "total": total,
        "page": page, "per_page": per_page,
    })


@app.route("/api/work-orders", methods=["POST"])
def create_work_order():
    data = request.json
    order_id = db.create_work_order(
        equipment_id=data["equipment_id"],
        equipment_name=data["equipment_name"],
        fault_type=data.get("fault_type", ""),
        fault_name=data.get("fault_name", ""),
        priority=data.get("priority", "medium"),
        description=data.get("description", ""),
        recommendations=data.get("recommendations", []),
    )
    return jsonify({"success": True, "order_id": order_id})


@app.route("/api/work-orders/<order_id>/update", methods=["POST"])
def update_work_order(order_id):
    data = request.json
    status = data.get("status")
    result = data.get("result", "")
    technician = data.get("technician", "")
    success = db.update_work_order(order_id, status, result, technician)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "更新失败"}), 400


# ==================== AI 分析 API ====================

@app.route("/api/analysis/<equipment_id>", methods=["GET"])
def get_analysis(equipment_id):
    tick_data()  # 按需生成数据
    eq = db.get_equipment(equipment_id)
    if not eq:
        return jsonify({"error": "设备不存在"}), 404

    recent_data = db.get_recent_sensor_data(equipment_id, Config.ANOMALY_WINDOW)
    detection = detector.detect(equipment_id, eq["type"], recent_data)

    # 故障诊断
    latest = db.get_latest_sensor_data(equipment_id)
    fault_result = diagnosis.diagnose(eq["type"], latest, detection)

    # RUL 预测
    health_trend = db.get_health_trend(equipment_id, points=50)
    rul_prediction = detector.predict_rul(health_trend, eq["type"])

    return jsonify({
        "success": True,
        "detection": detection,
        "fault_diagnosis": fault_result,
        "rul_prediction": rul_prediction,
    })


@app.route("/api/analysis/overview", methods=["GET"])
def get_overview():
    """全局概览：设备状态统计、告警统计、健康度分布"""
    tick_data()  # 按需生成数据
    equipment = db.get_all_equipment()
    alerts = db.get_recent_alerts(limit=50)
    stats = db.get_system_stats()

    # 健康度分布
    health_dist = {"excellent": 0, "good": 0, "warning": 0, "critical": 0, "failed": 0}
    for eq in equipment:
        h = eq.get("health_score", 100)
        if h >= 85:
            health_dist["excellent"] += 1
        elif h >= 70:
            health_dist["good"] += 1
        elif h >= 50:
            health_dist["warning"] += 1
        elif h >= 30:
            health_dist["critical"] += 1
        else:
            health_dist["failed"] += 1

    # 告警级别统计
    alert_stats = {"emergency": 0, "critical": 0, "warning": 0, "info": 0}
    for a in alerts:
        level = a.get("level", "info")
        if level in alert_stats:
            alert_stats[level] += 1

    # 工单统计
    work_order_stats = db.get_work_order_stats()

    return jsonify({
        "success": True,
        "overview": {
            "total_equipment": len(equipment),
            "running_equipment": sum(1 for e in equipment if e["status"] == "running"),
            "maintenance_equipment": sum(1 for e in equipment if e["status"] == "maintenance"),
            "stopped_equipment": sum(1 for e in equipment if e["status"] == "stopped"),
            "avg_health": sum(e.get("health_score", 100) for e in equipment) / max(len(equipment), 1),
            "health_distribution": health_dist,
            "alert_stats": alert_stats,
            "recent_alerts": alerts[:10],
            "work_order_stats": work_order_stats,
            "system_stats": stats,
        },
    })


# ==================== 故障诊断 API ====================

@app.route("/api/diagnosis/<equipment_id>", methods=["GET"])
def get_diagnosis(equipment_id):
    eq = db.get_equipment(equipment_id)
    if not eq:
        return jsonify({"error": "设备不存在"}), 404

    recent_data = db.get_recent_sensor_data(equipment_id, Config.ANOMALY_WINDOW)
    detection = detector.detect(equipment_id, eq["type"], recent_data)
    latest = db.get_latest_sensor_data(equipment_id)
    fault_result = diagnosis.diagnose(eq["type"], latest, detection)

    return jsonify({"success": True, "diagnosis": fault_result})


@app.route("/api/diagnosis/query", methods=["POST"])
def query_diagnosis():
    """故障诊断查询：根据症状查询可能的故障"""
    data = request.json
    symptoms = data.get("symptoms", [])
    equipment_type = data.get("equipment_type", "motor")
    result = diagnosis.query_by_symptoms(equipment_type, symptoms)
    return jsonify({"success": True, "result": result})


# ==================== 知识图谱 API ====================

@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    data = kg.get_graph_data()
    return jsonify({"success": True, "nodes": data["nodes"], "edges": data["edges"]})


@app.route("/api/knowledge-graph/search", methods=["GET"])
def search_kg():
    keyword = request.args.get("q", "")
    result = kg.search(keyword)
    return jsonify({"success": True, "result": result})


@app.route("/api/knowledge-graph/node/<node_id>", methods=["GET"])
def get_kg_node(node_id):
    detail = kg.get_node_detail(node_id)
    if detail:
        return jsonify({"success": True, **detail})
    return jsonify({"error": "节点不存在"}), 404


# ==================== 系统控制 API ====================

@app.route("/api/system/status", methods=["GET"])
def system_status():
    return jsonify({
        "success": True,
        "status": {
            "version": "1.0.0",
            "sensor_interval": Config.SENSOR_INTERVAL,
            "total_equipment": len(db.get_all_equipment()),
            "data_thread_running": True,  # 按需模式始终可用
        },
    })


@app.route("/api/system/config", methods=["POST"])
def update_config():
    data = request.json
    if "sensor_interval" in data:
        Config.SENSOR_INTERVAL = data["sensor_interval"]
    if "degradation_speed" in data:
        Config.DEGRADATION_SPEED = data["degradation_speed"]
        simulator.degradation_speed = data["degradation_speed"]
    return jsonify({"success": True, "message": "配置已更新"})


@app.route("/api/system/inject-fault", methods=["POST"])
def inject_fault():
    """注入故障（用于演示/测试）"""
    data = request.json
    equipment_id = data.get("equipment_id")
    fault_type = data.get("fault_type")
    severity = data.get("severity", 0.5)

    success = simulator.inject_fault(equipment_id, fault_type, severity)
    if success:
        return jsonify({"success": True, "message": f"已注入故障: {fault_type}"})
    return jsonify({"error": "注入失败"}), 400


@app.route("/api/system/reset-equipment/<equipment_id>", methods=["POST"])
def reset_equipment(equipment_id):
    """重置设备到健康状态（模拟维修后恢复）"""
    simulator.reset_equipment(equipment_id)
    db.update_equipment_health(equipment_id, 100.0)
    db.update_equipment_status(equipment_id, "running")
    simulator.set_equipment_running(equipment_id, True)
    return jsonify({"success": True, "message": "设备已重置为健康状态"})


@app.route("/api/system/degrade", methods=["POST"])
def trigger_degradation():
    """手动触发设备退化（用于演示预警能力）"""
    data = request.json
    equipment_id = data.get("equipment_id")
    speed = data.get("speed", 3.0)
    simulator.accelerate_degradation(equipment_id, speed)
    return jsonify({"success": True, "message": f"设备 {equipment_id} 退化已加速"})


if __name__ == "__main__":
    print("=" * 60)
    print("  生产设备预测性维护与智能运维平台 v1.0")
    print("  AI 异常检测 + RUL 预测 + 故障诊断")
    print(f"  访问地址: http://127.0.0.1:{Config.PORT}")
    print("=" * 60)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, threaded=True)
