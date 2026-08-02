"""数据库与质量追溯模块

存储:
  - 检测记录 (含缺陷详情、质量判定、AI分析)
  - 聊天历史
  - 统计聚合 (SPC, 趋势, 缺陷分布)
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS inspection_records (
                record_id TEXT PRIMARY KEY,
                product_name TEXT,
                product_code TEXT,
                batch_no TEXT,
                line TEXT,
                inspector TEXT,
                process TEXT,
                notes TEXT,
                image_filename TEXT,
                detection_result TEXT,
                quality_result TEXT,
                analysis_result TEXT,
                detection_time REAL,
                analysis_time REAL,
                total_time REAL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                response TEXT,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_records_created ON inspection_records(created_at);
            CREATE INDEX IF NOT EXISTS idx_records_batch ON inspection_records(batch_no);
            CREATE INDEX IF NOT EXISTS idx_records_verdict ON inspection_records(
                json_extract(quality_result, '$.verdict')
            );
        """)
        conn.commit()
        conn.close()

    def add_record(self, record: dict):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO inspection_records
            (record_id, product_name, product_code, batch_no, line, inspector,
             process, notes, image_filename, detection_result, quality_result,
             analysis_result, detection_time, analysis_time, total_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["record_id"],
            record.get("product_name", ""),
            record.get("product_code", ""),
            record.get("batch_no", ""),
            record.get("line", ""),
            record.get("inspector", ""),
            record.get("process", ""),
            record.get("notes", ""),
            record.get("image_filename", ""),
            json.dumps(record.get("detection_result", {}), ensure_ascii=False),
            json.dumps(record.get("quality_result", {}), ensure_ascii=False),
            json.dumps(record.get("analysis_result", {}), ensure_ascii=False),
            record.get("detection_time", 0),
            record.get("analysis_time", 0),
            record.get("total_time", 0),
            record.get("created_at", datetime.now().isoformat()),
        ))
        conn.commit()
        conn.close()

    def get_record(self, record_id):
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM inspection_records WHERE record_id = ?",
            (record_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        record = dict(row)
        record["detection_result"] = json.loads(record.get("detection_result") or "{}")
        record["quality_result"] = json.loads(record.get("quality_result") or "{}")
        record["analysis_result"] = json.loads(record.get("analysis_result") or "{}")
        return record

    def get_records(self, page=1, per_page=20, search="", verdict="", batch_no=""):
        conn = self._get_conn()
        cursor = conn.cursor()

        conditions = []
        params = []

        if search:
            conditions.append("(product_name LIKE ? OR product_code LIKE ? OR batch_no LIKE ? OR record_id LIKE ?)")
            pattern = f"%{search}%"
            params.extend([pattern, pattern, pattern, pattern])

        if verdict:
            conditions.append("json_extract(quality_result, '$.verdict') = ?")
            params.append(verdict)

        if batch_no:
            conditions.append("batch_no = ?")
            params.append(batch_no)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        offset = (page - 1) * per_page

        cursor.execute(
            f"SELECT COUNT(*) FROM inspection_records{where_clause}",
            params
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""SELECT record_id, product_name, product_code, batch_no, line, inspector,
                      process, image_filename, detection_result, quality_result,
                      analysis_result, total_time, created_at
               FROM inspection_records{where_clause}
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )
        rows = cursor.fetchall()
        conn.close()

        records = []
        for row in rows:
            r = dict(row)
            quality = json.loads(r.get("quality_result") or "{}")
            detection = json.loads(r.get("detection_result") or "{}")
            r["verdict"] = quality.get("verdict", "UNKNOWN")
            r["verdict_label"] = quality.get("verdict_label", "")
            r["defect_count"] = quality.get("total_defects", 0)
            r["defect_counts"] = quality.get("defect_counts", {})
            r["risk_level"] = ""
            analysis = json.loads(r.get("analysis_result") or "{}")
            risk = analysis.get("risk_assessment", {})
            r["risk_level"] = risk.get("level", "low")
            r["risk_label"] = risk.get("label", "")
            r["detection_result"] = detection
            r["analysis_result"] = analysis
            records.append(r)

        return {"total": total, "page": page, "per_page": per_page, "records": records}

    def delete_record(self, record_id):
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM inspection_records WHERE record_id = ?",
            (record_id,)
        )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_stats(self, days=7):
        """质量统计概览"""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = conn.cursor()

        # 总检测数
        cursor.execute(
            "SELECT COUNT(*) FROM inspection_records WHERE created_at >= ?",
            (since,)
        )
        total = cursor.fetchone()[0]

        # 合格/不合格
        cursor.execute(
            """SELECT json_extract(quality_result, '$.verdict') as verdict, COUNT(*) as cnt
               FROM inspection_records WHERE created_at >= ?
               GROUP BY verdict""",
            (since,)
        )
        verdict_dist = {}
        for row in cursor.fetchall():
            verdict_dist[row["verdict"]] = row["cnt"]

        passed = verdict_dist.get("PASS", 0)
        failed = verdict_dist.get("FAIL", 0)
        pass_rate = round(passed / total * 100, 1) if total else 0

        # 缺陷严重度分布
        cursor.execute(
            """SELECT
                json_extract(quality_result, '$.defect_counts.critical') as critical,
                json_extract(quality_result, '$.defect_counts.major') as major,
                json_extract(quality_result, '$.defect_counts.minor') as minor
               FROM inspection_records WHERE created_at >= ?""",
            (since,)
        )
        severity_totals = {"critical": 0, "major": 0, "minor": 0}
        for row in cursor.fetchall():
            severity_totals["critical"] += row["critical"] or 0
            severity_totals["major"] += row["major"] or 0
            severity_totals["minor"] += row["minor"] or 0

        # 批次统计
        cursor.execute(
            """SELECT batch_no, COUNT(*) as total,
                SUM(CASE WHEN json_extract(quality_result, '$.verdict') = 'PASS' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN json_extract(quality_result, '$.verdict') = 'FAIL' THEN 1 ELSE 0 END) as failed
               FROM inspection_records WHERE created_at >= ?
               GROUP BY batch_no ORDER BY total DESC LIMIT 10""",
            (since,)
        )
        batch_stats = []
        for row in cursor.fetchall():
            batch_stats.append({
                "batch_no": row["batch_no"],
                "total": row["total"],
                "passed": row["passed"],
                "failed": row["failed"],
                "pass_rate": round(row["passed"] / row["total"] * 100, 1) if row["total"] else 0,
            })

        # 产线统计
        cursor.execute(
            """SELECT line, COUNT(*) as total,
                SUM(CASE WHEN json_extract(quality_result, '$.verdict') = 'PASS' THEN 1 ELSE 0 END) as passed
               FROM inspection_records WHERE created_at >= ?
               GROUP BY line ORDER BY total DESC""",
            (since,)
        )
        line_stats = []
        for row in cursor.fetchall():
            line_stats.append({
                "line": row["line"],
                "total": row["total"],
                "passed": row["passed"],
                "pass_rate": round(row["passed"] / row["total"] * 100, 1) if row["total"] else 0,
            })

        conn.close()

        return {
            "days": days,
            "total_inspections": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "verdict_distribution": verdict_dist,
            "severity_totals": severity_totals,
            "batch_stats": batch_stats,
            "line_stats": line_stats,
        }

    def get_defect_distribution(self, days=7):
        """缺陷类型分布"""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = conn.cursor()
        cursor.execute(
            "SELECT detection_result FROM inspection_records WHERE created_at >= ?",
            (since,)
        )

        type_counts = {}
        for row in cursor.fetchall():
            detection = json.loads(row["detection_result"] or "{}")
            tc = detection.get("type_counts", {})
            for code, count in tc.items():
                type_counts[code] = type_counts.get(code, 0) + count

        conn.close()

        # 转为列表并排序
        dist = [{"code": k, "count": v} for k, v in type_counts.items()]
        dist.sort(key=lambda x: x["count"], reverse=True)

        return dist

    def get_spc_data(self, days=7):
        """SPC统计过程控制数据"""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = conn.cursor()
        cursor.execute(
            """SELECT DATE(created_at) as date,
                      COUNT(*) as total,
                      SUM(CASE WHEN json_extract(quality_result, '$.verdict') = 'FAIL' THEN 1 ELSE 0 END) as defects,
                      SUM(json_extract(quality_result, '$.total_defects')) as total_defect_count
               FROM inspection_records
               WHERE created_at >= ?
               GROUP BY DATE(created_at)
               ORDER BY date""",
            (since,)
        )

        daily = []
        for row in cursor.fetchall():
            total = row["total"]
            defects = row["defects"] or 0
            defect_count = row["total_defect_count"] or 0
            daily.append({
                "date": row["date"],
                "total": total,
                "defective": defects,
                "defect_rate": round(defects / total * 100, 2) if total else 0,
                "defect_count": defect_count,
                "dpu": round(defect_count / total, 2) if total else 0,  # defects per unit
            })

        conn.close()

        # 计算控制限
        if daily:
            total_units = sum(d["total"] for d in daily)
            total_defective = sum(d["defective"] for d in daily)
            avg_rate = total_defective / total_units if total_units else 0
            ucl = min(avg_rate + 3 * (avg_rate * (1 - avg_rate) / total_units) ** 0.5, 1.0) if total_units else 0
            lcl = max(avg_rate - 3 * (avg_rate * (1 - avg_rate) / total_units) ** 0.5, 0.0) if total_units else 0
        else:
            avg_rate = 0
            ucl = 0
            lcl = 0

        return {
            "daily": daily,
            "avg_defect_rate": round(avg_rate * 100, 2),
            "ucl": round(ucl * 100, 2),
            "lcl": round(lcl * 100, 2),
            "cl": round(avg_rate * 100, 2),  # center line
        }

    def get_trend(self, days=7):
        """质量趋势"""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = conn.cursor()
        cursor.execute(
            """SELECT DATE(created_at) as date,
                      COUNT(*) as total,
                      SUM(CASE WHEN json_extract(quality_result, '$.verdict') = 'PASS' THEN 1 ELSE 0 END) as passed,
                      SUM(json_extract(quality_result, '$.total_defects')) as defects
               FROM inspection_records
               WHERE created_at >= ?
               GROUP BY DATE(created_at)
               ORDER BY date""",
            (since,)
        )

        trend = []
        for row in cursor.fetchall():
            total = row["total"]
            passed = row["passed"] or 0
            trend.append({
                "date": row["date"],
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": round(passed / total * 100, 1) if total else 0,
                "avg_defects": round((row["defects"] or 0) / total, 2) if total else 0,
            })

        conn.close()
        return trend

    def add_chat_record(self, message, response):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chat_history (message, response, created_at) VALUES (?, ?, ?)",
            (message, json.dumps(response, ensure_ascii=False), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_chat_history(self, limit=50):
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT message, response, created_at FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        records = []
        for row in cursor.fetchall():
            records.append({
                "message": row["message"],
                "response": json.loads(row["response"] or "{}"),
                "created_at": row["created_at"],
            })
        conn.close()
        return records
