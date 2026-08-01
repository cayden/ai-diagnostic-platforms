"""
主 Flask 应用
智能影像辅助诊断系统 - 后端服务
"""
import os
import sys
import uuid
import time
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

from config import Config
from modules.database import Database
from modules.yolo_detector import YOLODetector
from modules.llm_analyzer import LLMAnalyzer
from modules.knowledge_graph import KnowledgeGraph
from modules.report_generator import ReportGenerator

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
CORS(app)

# 初始化各模块
db = Database(Config.DB_PATH)
detector = YOLODetector(Config)
analyzer = LLMAnalyzer(Config)
kg = KnowledgeGraph(Config.KG_DATA_PATH)
report_gen = ReportGenerator()

# 确保目录存在
os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
os.makedirs(Config.REPORT_DIR, exist_ok=True)


# ==================== 页面路由 ====================

@app.route("/")
def index():
    return render_template("index.html")


# ==================== 影像分析 API ====================

@app.route("/api/analyze", methods=["POST"])
def analyze_image():
    """上传影像并执行分析：YOLO检测 + LLM分析"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "未找到影像文件"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "未选择文件"}), 400

        # 保存文件
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in Config.ALLOWED_EXTENSIONS:
            return jsonify({"error": f"不支持的文件格式: {ext}"}), 400

        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(Config.UPLOAD_DIR, filename)
        file.save(filepath)

        # 获取元数据
        patient_name = request.form.get("patient_name", "未知患者")
        patient_age = request.form.get("patient_age", "")
        patient_gender = request.form.get("patient_gender", "")
        exam_type = request.form.get("exam_type", "胸部CT")
        clinical_info = request.form.get("clinical_info", "")

        # Step 1: YOLO 目标检测
        t0 = time.time()
        detection_result = detector.detect(filepath)
        detection_time = round(time.time() - t0, 3)

        # 读取图像为base64
        with open(filepath, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Step 2: LLM 智能分析
        t1 = time.time()
        analysis_result = analyzer.analyze(
            detection_result=detection_result,
            patient_info={
                "name": patient_name,
                "age": patient_age,
                "gender": patient_gender,
                "exam_type": exam_type,
                "clinical_info": clinical_info,
            },
        )
        analysis_time = round(time.time() - t1, 3)

        # Step 3: 生成诊断报告
        record_id = str(uuid.uuid4())[:8]
        report = report_gen.generate(
            record_id=record_id,
            patient_info={
                "name": patient_name,
                "age": patient_age,
                "gender": patient_gender,
                "exam_type": exam_type,
                "clinical_info": clinical_info,
            },
            detection_result=detection_result,
            analysis_result=analysis_result,
            image_filename=filename,
        )

        # Step 4: 存入数据库
        db.add_record(
            record_id=record_id,
            patient_name=patient_name,
            patient_age=patient_age,
            patient_gender=patient_gender,
            exam_type=exam_type,
            clinical_info=clinical_info,
            image_filename=filename,
            detection_result=detection_result,
            analysis_result=analysis_result,
            report=report,
            detection_time=detection_time,
            analysis_time=analysis_time,
        )

        return jsonify({
            "success": True,
            "record_id": record_id,
            "image_base64": f"data:image/{ext};base64,{img_base64}",
            "detection": detection_result,
            "analysis": analysis_result,
            "report": report,
            "timing": {
                "detection": detection_time,
                "analysis": analysis_time,
                "total": round(detection_time + analysis_time, 3),
            },
        })

    except Exception as e:
        return jsonify({"error": f"分析失败: {str(e)}"}), 500


# ==================== 历史记录 API ====================

@app.route("/api/history", methods=["GET"])
def get_history():
    """获取历史记录列表"""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    search = request.args.get("search", "")

    records, total = db.get_records(page=page, per_page=per_page, search=search)
    return jsonify({
        "success": True,
        "records": records,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/history/<record_id>", methods=["GET"])
def get_record(record_id):
    """获取单条历史记录详情"""
    record = db.get_record(record_id)
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    return jsonify({"success": True, "record": record})


@app.route("/api/history/<record_id>", methods=["DELETE"])
def delete_record(record_id):
    """删除历史记录"""
    success = db.delete_record(record_id)
    if success:
        return jsonify({"success": True, "message": "记录已删除"})
    return jsonify({"error": "删除失败"}), 400


@app.route("/api/history/stats", methods=["GET"])
def get_stats():
    """获取统计数据"""
    stats = db.get_stats()
    return jsonify({"success": True, "stats": stats})


# ==================== AI 问答 API ====================

@app.route("/api/chat", methods=["POST"])
def chat():
    """AI问答助手"""
    data = request.json
    message = data.get("message", "")
    context = data.get("context", "")  # 可附带当前影像分析上下文

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    response = analyzer.chat(message, context)

    # 保存对话记录
    db.add_chat_record(message, response)

    return jsonify({"success": True, "response": response})


@app.route("/api/chat/history", methods=["GET"])
def get_chat_history():
    """获取问答历史"""
    records = db.get_chat_records(limit=100)
    return jsonify({"success": True, "records": records})


@app.route("/api/chat/clear", methods=["DELETE"])
def clear_chat():
    """清空问答历史"""
    db.clear_chat_records()
    return jsonify({"success": True, "message": "问答历史已清空"})


# ==================== 知识图谱 API ====================

@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    """获取知识图谱数据"""
    return jsonify(kg.get_graph_data())


@app.route("/api/knowledge-graph/search", methods=["GET"])
def search_knowledge():
    """知识图谱查询"""
    keyword = request.args.get("q", "")
    result = kg.search(keyword)
    return jsonify({"success": True, "result": result})


@app.route("/api/knowledge-graph/node/<node_id>", methods=["GET"])
def get_node_detail(node_id):
    """获取节点详情"""
    detail = kg.get_node_detail(node_id)
    if detail:
        return jsonify({"success": True, "node": detail})
    return jsonify({"error": "节点不存在"}), 404


# ==================== 静态资源 ====================

@app.route("/api/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_DIR, filename)


# ==================== 系统状态 ====================

@app.route("/api/system/status", methods=["GET"])
def system_status():
    """系统状态"""
    return jsonify({
        "success": True,
        "status": {
            "yolo_mode": "simulation" if Config.YOLO_USE_SIMULATION else "model",
            "llm_mode": "simulation" if Config.LLM_USE_SIMULATION else "api",
            "llm_configured": bool(Config.DEEPSEEK_API_KEY),
            "version": "1.0.0",
            "detection_classes": Config.DETECTION_CLASSES,
        },
    })


@app.route("/api/system/config", methods=["POST"])
def update_config():
    """更新系统配置（API Key等）"""
    data = request.json
    if "deepseek_api_key" in data:
        Config.DEEPSEEK_API_KEY = data["deepseek_api_key"]
        analyzer.update_api_key(data["deepseek_api_key"])
    if "yolo_use_simulation" in data:
        Config.YOLO_USE_SIMULATION = data["yolo_use_simulation"]
        detector.use_simulation = data["yolo_use_simulation"]
    if "llm_use_simulation" in data:
        Config.LLM_USE_SIMULATION = data["llm_use_simulation"]
        analyzer.use_simulation = data["llm_use_simulation"]
    return jsonify({"success": True, "message": "配置已更新"})


if __name__ == "__main__":
    print("=" * 60)
    print("  智能影像辅助诊断系统 v1.0")
    print("  YOLO + Deepseek LLM 融合架构")
    print(f"  访问地址: http://127.0.0.1:{Config.PORT}")
    print("=" * 60)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
