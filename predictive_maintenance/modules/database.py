"""
数据库模块 - SQLite
存储设备信息、传感器数据、告警、工单
"""
import json
import sqlite3
from datetime import datetime, timedelta


class Database:
    """数据库管理"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        # 设备表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                location TEXT,
                manufacturer TEXT,
                model TEXT,
                install_date TEXT,
                rated_power TEXT,
                rated_speed TEXT,
                status TEXT DEFAULT 'running',
                health_score REAL DEFAULT 100.0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 传感器数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cycle INTEGER,
                sensors_json TEXT NOT NULL,
                health_factor REAL,
                fault_type TEXT,
                fault_progress REAL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
            )
        """)

        # 告警表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                equipment_id TEXT NOT NULL,
                equipment_name TEXT,
                level TEXT NOT NULL,
                health_score REAL,
                fault_type TEXT,
                fault_name TEXT,
                description TEXT,
                recommendations_json TEXT,
                sensor_snapshot_json TEXT,
                rul_hours REAL,
                rul_confidence REAL,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
            )
        """)

        # 维修工单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                equipment_id TEXT NOT NULL,
                equipment_name TEXT,
                fault_type TEXT,
                fault_name TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                description TEXT,
                recommendations_json TEXT,
                technician TEXT,
                result TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                completed_at TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
            )
        """)

        # 健康度历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT NOT NULL,
                health_score REAL NOT NULL,
                timestamp TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_eq ON sensor_data(equipment_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_eq ON alerts(equipment_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON work_orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_eq ON health_history(equipment_id, timestamp)")

        conn.commit()
        conn.close()

    # ==================== 设备管理 ====================

    def add_equipment(self, eq_data):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO equipment
                (equipment_id, name, type, location, manufacturer, model,
                 install_date, rated_power, rated_speed, status, health_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eq_data.get("equipment_id"),
                eq_data.get("name", ""),
                eq_data.get("type", "motor"),
                eq_data.get("location", ""),
                eq_data.get("manufacturer", ""),
                eq_data.get("model", ""),
                eq_data.get("install_date", ""),
                eq_data.get("rated_power", ""),
                eq_data.get("rated_speed", ""),
                eq_data.get("status", "running"),
                100.0,
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] add_equipment error: {e}")
            return False
        finally:
            conn.close()

    def get_all_equipment(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipment ORDER BY equipment_id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_equipment(self, equipment_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_equipment(self, equipment_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM equipment WHERE equipment_id = ?", (equipment_id,))
        cursor.execute("DELETE FROM sensor_data WHERE equipment_id = ?", (equipment_id,))
        cursor.execute("DELETE FROM alerts WHERE equipment_id = ?", (equipment_id,))
        cursor.execute("DELETE FROM work_orders WHERE equipment_id = ?", (equipment_id,))
        cursor.execute("DELETE FROM health_history WHERE equipment_id = ?", (equipment_id,))
        conn.commit()
        conn.close()
        return True

    def update_equipment_status(self, equipment_id, status):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE equipment SET status = ?, updated_at = datetime('now', 'localtime') WHERE equipment_id = ?",
            (status, equipment_id),
        )
        conn.commit()
        conn.close()

    def update_equipment_health(self, equipment_id, health_score):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE equipment SET health_score = ?, updated_at = datetime('now', 'localtime') WHERE equipment_id = ?",
            (health_score, equipment_id),
        )
        cursor.execute(
            "INSERT INTO health_history (equipment_id, health_score) VALUES (?, ?)",
            (equipment_id, health_score),
        )
        conn.commit()
        conn.close()

    # ==================== 传感器数据 ====================

    def add_sensor_data(self, equipment_id, data):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_data (equipment_id, timestamp, cycle, sensors_json, health_factor, fault_type, fault_progress)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            equipment_id,
            data.get("timestamp", datetime.now().isoformat()),
            data.get("cycle", 0),
            json.dumps(data.get("sensors", {})),
            data.get("health_factor"),
            data.get("fault_type"),
            data.get("fault_progress"),
        ))
        # 清理旧数据
        cursor.execute("""
            DELETE FROM sensor_data WHERE equipment_id = ?
            AND id NOT IN (
                SELECT id FROM sensor_data WHERE equipment_id = ?
                ORDER BY id DESC LIMIT ?
            )
        """, (equipment_id, equipment_id, self.HISTORY_RETENTION_LIMIT if hasattr(self, 'HISTORY_RETENTION_LIMIT') else 2000))
        conn.commit()
        conn.close()

    def get_latest_sensor_data(self, equipment_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data WHERE equipment_id = ?
            ORDER BY id DESC LIMIT 1
        """, (equipment_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["sensors"] = json.loads(d.get("sensors_json", "{}"))
            return d
        return None

    def get_recent_sensor_data(self, equipment_id, count=30):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data WHERE equipment_id = ?
            ORDER BY id DESC LIMIT ?
        """, (equipment_id, count))
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in reversed(rows):
            d = dict(row)
            d["sensors"] = json.loads(d.get("sensors_json", "{}"))
            result.append(d)
        return result

    def get_sensor_history(self, equipment_id, points=100):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data WHERE equipment_id = ?
            ORDER BY id DESC LIMIT ?
        """, (equipment_id, points))
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in reversed(rows):
            d = dict(row)
            d["sensors"] = json.loads(d.get("sensors_json", "{}"))
            result.append(d)
        return result

    # ==================== 告警管理 ====================

    def add_alert(self, equipment_id, equipment_name, level, health_score,
                  fault_type, fault_name, description, recommendations,
                  sensor_snapshot, rul_hours, rul_confidence):
        conn = self._get_conn()
        cursor = conn.cursor()
        alert_id = f"ALR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{equipment_id}"
        cursor.execute("""
            INSERT INTO alerts (alert_id, equipment_id, equipment_name, level, health_score,
                fault_type, fault_name, description, recommendations_json, sensor_snapshot_json,
                rul_hours, rul_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_id, equipment_id, equipment_name, level, health_score,
            fault_type, fault_name, description,
            json.dumps(recommendations, ensure_ascii=False),
            json.dumps(sensor_snapshot, ensure_ascii=False),
            rul_hours, rul_confidence,
        ))
        conn.commit()
        conn.close()
        return alert_id

    def get_alerts(self, page=1, per_page=20, level="", equipment_id="", acknowledged=""):
        conn = self._get_conn()
        cursor = conn.cursor()
        offset = (page - 1) * per_page

        conditions = []
        params = []
        if level:
            conditions.append("level = ?")
            params.append(level)
        if equipment_id:
            conditions.append("equipment_id = ?")
            params.append(equipment_id)
        if acknowledged != "":
            conditions.append("acknowledged = ?")
            params.append(int(acknowledged))

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        cursor.execute(f"SELECT COUNT(*) FROM alerts{where_clause}", params)
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT * FROM alerts{where_clause}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        rows = cursor.fetchall()
        conn.close()

        alerts = []
        for row in rows:
            a = dict(row)
            a["recommendations"] = json.loads(a.get("recommendations_json", "[]"))
            a["sensor_snapshot"] = json.loads(a.get("sensor_snapshot_json", "{}"))
            alerts.append(a)
        return alerts, total

    def get_recent_alerts(self, limit=20):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        alerts = []
        for row in rows:
            a = dict(row)
            a["recommendations"] = json.loads(a.get("recommendations_json", "[]"))
            alerts.append(a)
        return alerts

    def get_alerts_by_equipment(self, equipment_id, limit=10):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE equipment_id = ? ORDER BY created_at DESC LIMIT ?",
            (equipment_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        alerts = []
        for row in rows:
            a = dict(row)
            a["recommendations"] = json.loads(a.get("recommendations_json", "[]"))
            alerts.append(a)
        return alerts

    def get_last_alert_time(self, equipment_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT created_at FROM alerts WHERE equipment_id = ? ORDER BY created_at DESC LIMIT 1",
            (equipment_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return None
        return None

    def acknowledge_alert(self, alert_id, handler=""):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alerts SET acknowledged = 1, acknowledged_by = ?,
            acknowledged_at = datetime('now', 'localtime')
            WHERE alert_id = ?
        """, (handler, alert_id))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # ==================== 工单管理 ====================

    def create_work_order(self, equipment_id, equipment_name, fault_type, fault_name,
                          priority, description, recommendations):
        conn = self._get_conn()
        cursor = conn.cursor()
        order_id = f"WO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute("""
            INSERT INTO work_orders (order_id, equipment_id, equipment_name, fault_type,
                fault_name, priority, status, description, recommendations_json)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            order_id, equipment_id, equipment_name, fault_type, fault_name,
            priority, description,
            json.dumps(recommendations, ensure_ascii=False),
        ))
        conn.commit()
        conn.close()
        return order_id

    def get_work_orders(self, status="", page=1, per_page=20):
        conn = self._get_conn()
        cursor = conn.cursor()
        offset = (page - 1) * per_page

        if status:
            cursor.execute("SELECT COUNT(*) FROM work_orders WHERE status = ?", (status,))
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT * FROM work_orders WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, per_page, offset),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM work_orders")
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            )

        rows = cursor.fetchall()
        conn.close()
        orders = []
        for row in rows:
            o = dict(row)
            o["recommendations"] = json.loads(o.get("recommendations_json", "[]"))
            orders.append(o)
        return orders, total

    def get_work_orders_by_equipment(self, equipment_id, limit=10):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM work_orders WHERE equipment_id = ? ORDER BY created_at DESC LIMIT ?",
            (equipment_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        orders = []
        for row in rows:
            o = dict(row)
            o["recommendations"] = json.loads(o.get("recommendations_json", "[]"))
            orders.append(o)
        return orders

    def get_open_work_orders(self, equipment_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM work_orders WHERE equipment_id = ? AND status IN ('pending', 'in_progress')",
            (equipment_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_work_order(self, order_id, status, result="", technician=""):
        conn = self._get_conn()
        cursor = conn.cursor()
        completed_at = ""
        if status in ("completed", "cancelled"):
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "UPDATE work_orders SET status = ?, result = ?, technician = ?, completed_at = ? WHERE order_id = ?",
                (status, result, technician, completed_at, order_id),
            )
        else:
            cursor.execute(
                "UPDATE work_orders SET status = ?, result = ?, technician = ? WHERE order_id = ?",
                (status, result, technician, order_id),
            )
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def get_work_order_stats(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        stats = {"pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
        cursor.execute("SELECT status, COUNT(*) as count FROM work_orders GROUP BY status")
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        conn.close()
        return stats

    # ==================== 健康度历史 ====================

    def get_health_trend(self, equipment_id, points=100):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT health_score, timestamp FROM health_history
            WHERE equipment_id = ? ORDER BY id DESC LIMIT ?
        """, (equipment_id, points))
        rows = cursor.fetchall()
        conn.close()
        return [{"health": r[0], "timestamp": r[1]} for r in reversed(rows)]

    # ==================== 统计 ====================

    def get_system_stats(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM equipment")
        total_eq = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        total_readings = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
        unack_alerts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM work_orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()[0]

        conn.close()
        return {
            "total_equipment": total_eq,
            "total_sensor_readings": total_readings,
            "unacknowledged_alerts": unack_alerts,
            "pending_work_orders": pending_orders,
        }
