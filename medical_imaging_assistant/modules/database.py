"""
数据库模块 - SQLite
存储分析记录、诊断报告、问答历史
"""
import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        # 影像分析记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imaging_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                patient_name TEXT,
                patient_age TEXT,
                patient_gender TEXT,
                exam_type TEXT,
                clinical_info TEXT,
                image_filename TEXT NOT NULL,
                detection_result TEXT NOT NULL,
                analysis_result TEXT NOT NULL,
                report TEXT NOT NULL,
                detection_time REAL DEFAULT 0,
                analysis_time REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI问答记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # ==================== 影像记录 ====================

    def add_record(self, record_id, **kwargs):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO imaging_records
                (record_id, patient_name, patient_age, patient_gender,
                 exam_type, clinical_info, image_filename,
                 detection_result, analysis_result, report,
                 detection_time, analysis_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            kwargs.get("patient_name", ""),
            kwargs.get("patient_age", ""),
            kwargs.get("patient_gender", ""),
            kwargs.get("exam_type", ""),
            kwargs.get("clinical_info", ""),
            kwargs.get("image_filename", ""),
            json.dumps(kwargs.get("detection_result", {}), ensure_ascii=False),
            json.dumps(kwargs.get("analysis_result", {}), ensure_ascii=False),
            json.dumps(kwargs.get("report", {}), ensure_ascii=False),
            kwargs.get("detection_time", 0),
            kwargs.get("analysis_time", 0),
        ))
        conn.commit()
        conn.close()

    def get_records(self, page=1, per_page=20, search=""):
        conn = self._get_conn()
        cursor = conn.cursor()
        offset = (page - 1) * per_page

        if search:
            search_pattern = f"%{search}%"
            cursor.execute("""
                SELECT record_id, patient_name, patient_age, patient_gender,
                       exam_type, image_filename, detection_result, analysis_result,
                       created_at
                FROM imaging_records
                WHERE patient_name LIKE ? OR exam_type LIKE ? OR record_id LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (search_pattern, search_pattern, search_pattern, per_page, offset))
            rows = cursor.fetchall()
            cursor.execute("""
                SELECT COUNT(*) FROM imaging_records
                WHERE patient_name LIKE ? OR exam_type LIKE ? OR record_id LIKE ?
            """, (search_pattern, search_pattern, search_pattern))
            total = cursor.fetchone()[0]
        else:
            cursor.execute("""
                SELECT record_id, patient_name, patient_age, patient_gender,
                       exam_type, image_filename, detection_result, analysis_result,
                       created_at
                FROM imaging_records
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            rows = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM imaging_records")
            total = cursor.fetchone()[0]

        records = []

        for row in rows:
            record = dict(row)
            analysis = json.loads(record.get("analysis_result", "{}"))
            detection = json.loads(record.get("detection_result", "{}"))
            record["risk_level"] = analysis.get("risk_level", "未知")
            record["risk_score"] = analysis.get("risk_score", 0)
            record["findings_count"] = len(detection.get("detections", []))
            record["detection_result"] = detection
            record["analysis_result"] = analysis
            records.append(record)

        conn.close()
        return records, total

    def get_record(self, record_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM imaging_records WHERE record_id = ?
        """, (record_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        record = dict(row)
        record["detection_result"] = json.loads(record.get("detection_result", "{}"))
        record["analysis_result"] = json.loads(record.get("analysis_result", "{}"))
        record["report"] = json.loads(record.get("report", "{}"))
        return record

    def delete_record(self, record_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM imaging_records WHERE record_id = ?", (record_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def get_stats(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM imaging_records")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT analysis_result FROM imaging_records
        """)
        rows = cursor.fetchall()

        risk_counts = {"低风险": 0, "中风险": 0, "高风险": 0}
        benign_counts = {"良性": 0, "良性可能性大": 0, "不确定": 0, "恶性可能性大": 0}
        class_counts = {}

        for row in rows:
            analysis = json.loads(row[0])
            risk = analysis.get("risk_level", "")
            if risk in risk_counts:
                risk_counts[risk] += 1
            for finding in analysis.get("findings", []):
                bm = finding.get("benign_malignant", "")
                if bm in benign_counts:
                    benign_counts[bm] += 1
                region = finding.get("region", "")
                if region:
                    class_counts[region] = class_counts.get(region, 0) + 1

        cursor.execute("SELECT COUNT(*) FROM chat_records")
        chat_total = cursor.fetchone()[0]

        conn.close()

        return {
            "total_records": total,
            "risk_distribution": risk_counts,
            "benign_distribution": benign_counts,
            "class_distribution": class_counts,
            "total_chats": chat_total,
        }

    # ==================== 问答记录 ====================

    def add_chat_record(self, user_message, assistant_response):
        conn = self._get_conn()
        cursor = conn.cursor()

        # 如果response是dict，提取content
        if isinstance(assistant_response, dict):
            response_text = assistant_response.get("content", json.dumps(assistant_response, ensure_ascii=False))
            mode = assistant_response.get("mode", "unknown")
        else:
            response_text = str(assistant_response)
            mode = "unknown"

        cursor.execute("""
            INSERT INTO chat_records (user_message, assistant_response)
            VALUES (?, ?)
        """, (user_message, response_text))
        conn.commit()
        conn.close()

    def get_chat_records(self, limit=100):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_message, assistant_response, created_at
            FROM chat_records
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        records = [
            {
                "user_message": row[0],
                "assistant_response": row[1],
                "created_at": row[2],
            }
            for row in reversed(rows)
        ]
        conn.close()
        return records

    def clear_chat_records(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_records")
        conn.commit()
        conn.close()
