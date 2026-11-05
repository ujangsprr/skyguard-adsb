#!/usr/bin/env python3
"""
SkyGuard Sentinel - Hybrid SQLite Database Manager
Manages:
- Incident & Tactical Alert History (FIR entries, Squawk emergencies, tactical callsigns)
- Persistent Flight Route Cache (saves origin/destination across restarts, saving OpenSky quota)
- Custom Intel Watchlist & Notes for sensitive airframes
- WAL (Write-Ahead Logging) mode for high-concurrency read/write safely
"""

import os
import sqlite3
import time
import datetime

WIB_TZ = datetime.timezone(datetime.timedelta(hours=7))

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._last_logged = {}  # icao -> (lat, lon, alt, timestamp) for debouncing stationary/duplicate points
        self._last_purge_time = 0
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Alerts & Incident History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    datetime_wib TEXT NOT NULL,
                    icao24 TEXT NOT NULL,
                    callsign TEXT,
                    country TEXT,
                    flight_type TEXT,
                    is_military INTEGER DEFAULT 0,
                    severity TEXT NOT NULL,
                    label TEXT,
                    description TEXT,
                    lat REAL,
                    lon REAL,
                    alt_ft INTEGER,
                    speed_kts INTEGER,
                    squawk TEXT,
                    in_fir_indo INTEGER DEFAULT 0,
                    fir_name TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts_history(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_icao ON alerts_history(icao24)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts_history(severity)")

            # 2. Persistent Routes Cache Table (Saves quota permanently across restarts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flight_routes (
                    icao24 TEXT PRIMARY KEY,
                    has_route INTEGER DEFAULT 0,
                    origin_icao TEXT,
                    origin_name TEXT,
                    origin_city TEXT,
                    origin_country TEXT,
                    origin_lat REAL,
                    origin_lon REAL,
                    origin_display TEXT,
                    dest_icao TEXT,
                    dest_name TEXT,
                    dest_city TEXT,
                    dest_country TEXT,
                    dest_lat REAL,
                    dest_lon REAL,
                    dest_display TEXT,
                    updated_at INTEGER NOT NULL
                )
            """)

            # 3. Custom Aircraft Intel Watchlist Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_aircraft (
                    icao24 TEXT PRIMARY KEY,
                    priority TEXT DEFAULT 'normal',
                    tag TEXT,
                    notes TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # 4. Priority Flight Position Logs (Option A: Military + Indonesian FIR + Alerts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flight_position_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    datetime_wib TEXT NOT NULL,
                    icao24 TEXT NOT NULL,
                    callsign TEXT,
                    country TEXT,
                    flight_type TEXT,
                    category TEXT,
                    is_military INTEGER DEFAULT 0,
                    in_fir_indo INTEGER DEFAULT 0,
                    fir_name TEXT,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    alt_ft INTEGER,
                    speed_kts INTEGER,
                    heading REAL,
                    vert_rate_fpm INTEGER,
                    squawk TEXT,
                    has_detection INTEGER DEFAULT 0,
                    detection_label TEXT,
                    log_reason TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpl_time ON flight_position_logs(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpl_icao ON flight_position_logs(icao24, timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpl_fir ON flight_position_logs(in_fir_indo, timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fpl_mil ON flight_position_logs(is_military, timestamp DESC)")

            conn.commit()
            print(f"[SQLITE] Hybrid database initialized with WAL mode at {self.db_path}")

    # ==========================================
    # ALERTS & INCIDENTS LOGGING
    # ==========================================
    def log_alert(self, alert_data):
        """Log an alert or incident with debouncing (prevent logging duplicate within 300s)."""
        icao = (alert_data.get("icao24") or "").upper().strip()
        if not icao:
            return None
        severity = alert_data.get("severity", "warning")
        label = alert_data.get("label", "ALERT")
        now = int(time.time())

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM alerts_history 
                WHERE icao24 = ? AND label = ? AND timestamp > ? 
                LIMIT 1
            """, (icao, label, now - 300))
            if cur.fetchone():
                return None  # Debounced

            wib_now = datetime.datetime.now(WIB_TZ).strftime("%Y-%m-%d %H:%M:%S WIB")
            cur.execute("""
                INSERT INTO alerts_history (
                    timestamp, datetime_wib, icao24, callsign, country, 
                    flight_type, is_military, severity, label, description, 
                    lat, lon, alt_ft, speed_kts, squawk, in_fir_indo, fir_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                wib_now,
                icao,
                alert_data.get("callsign", "NO CALL"),
                alert_data.get("country", "Unknown"),
                alert_data.get("flight_type", "military"),
                1 if alert_data.get("is_military") else 0,
                severity,
                label,
                alert_data.get("desc", ""),
                alert_data.get("lat"),
                alert_data.get("lon"),
                alert_data.get("alt_ft"),
                alert_data.get("speed_kts"),
                alert_data.get("squawk", ""),
                1 if alert_data.get("in_fir_indonesia") else 0,
                alert_data.get("fir_name", "")
            ))
            conn.commit()
            return cur.lastrowid

    def get_recent_alerts(self, limit=50, severity=None, icao24=None):
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM alerts_history WHERE 1=1"
            params = []
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            if icao24:
                query += " AND icao24 = ?"
                params.append(icao24.upper())
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def get_alerts_stats(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total FROM alerts_history")
            total = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) as crit FROM alerts_history WHERE severity = 'critical'")
            critical = cur.fetchone()["crit"]
            cur.execute("SELECT COUNT(*) as fir FROM alerts_history WHERE in_fir_indo = 1")
            fir_count = cur.fetchone()["fir"]
            return {
                "total_logged_alerts": total,
                "critical_alerts": critical,
                "fir_indonesia_alerts": fir_count
            }

    # ==========================================
    # PERSISTENT ROUTE CACHING
    # ==========================================
    def get_route(self, icao24):
        icao = (icao24 or "").upper().strip()
        if not icao:
            return None
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM flight_routes WHERE icao24 = ?", (icao,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            origin = None
            if data.get("origin_name") or data.get("origin_icao"):
                origin = {
                    "icao": data.get("origin_icao"),
                    "name": data.get("origin_name"),
                    "city": data.get("origin_city"),
                    "country": data.get("origin_country"),
                    "lat": data.get("origin_lat"),
                    "lon": data.get("origin_lon")
                }
            dest = None
            if data.get("dest_name") or data.get("dest_icao"):
                dest = {
                    "icao": data.get("dest_icao"),
                    "name": data.get("dest_name"),
                    "city": data.get("dest_city"),
                    "country": data.get("dest_country"),
                    "lat": data.get("dest_lat"),
                    "lon": data.get("dest_lon")
                }
            return {
                "status": "success",
                "icao24": icao,
                "has_route": bool(data.get("has_route")),
                "origin": origin,
                "origin_display": data.get("origin_display") or "Unknown Origin",
                "destination": dest,
                "dest_display": data.get("dest_display") or "In Flight",
                "cached_time": data.get("updated_at"),
                "source": "sqlite_persistent"
            }

    def save_route(self, icao24, route_dict):
        icao = (icao24 or "").upper().strip()
        if not icao:
            return
        origin = route_dict.get("origin") or {}
        dest = route_dict.get("destination") or {}
        now = int(time.time())

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO flight_routes (
                    icao24, has_route, 
                    origin_icao, origin_name, origin_city, origin_country, origin_lat, origin_lon, origin_display,
                    dest_icao, dest_name, dest_city, dest_country, dest_lat, dest_lon, dest_display,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                icao,
                1 if route_dict.get("has_route") else 0,
                origin.get("icao"),
                origin.get("name"),
                origin.get("city"),
                origin.get("country"),
                origin.get("lat"),
                origin.get("lon"),
                route_dict.get("origin_display"),
                dest.get("icao"),
                dest.get("name"),
                dest.get("city"),
                dest.get("country"),
                dest.get("lat"),
                dest.get("lon"),
                route_dict.get("dest_display"),
                now
            ))
            conn.commit()

    # ==========================================
    # CUSTOM AIRCRAFT INTEL & WATCHLIST
    # ==========================================
    def get_custom_aircraft(self, icao24=None):
        with self._get_connection() as conn:
            cur = conn.cursor()
            if icao24:
                cur.execute("SELECT * FROM custom_aircraft WHERE icao24 = ?", (icao24.upper().strip(),))
                row = cur.fetchone()
                return dict(row) if row else None
            else:
                cur.execute("SELECT * FROM custom_aircraft ORDER BY updated_at DESC")
                return [dict(r) for r in cur.fetchall()]

    def set_custom_aircraft(self, icao24, priority="normal", tag="", notes=""):
        icao = (icao24 or "").upper().strip()
        if not icao:
            return False
        now = int(time.time())
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO custom_aircraft (icao24, priority, tag, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(icao24) DO UPDATE SET
                    priority = excluded.priority,
                    tag = excluded.tag,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
            """, (icao, priority, tag, notes, now, now))
            conn.commit()
            return True

    # ==========================================
    # PRIORITY FLIGHT POSITION LOGGING (OPTION A)
    # ==========================================
    def log_flight_positions(self, flight_list):
        """
        Option A: High-priority flight position logging into SQLite.
        Persists Military aircraft, flights within Indonesian FIR, and any aircraft with active alerts/anomalies.
        Debounced to prevent logging stationary or duplicate coordinates within 30s.
        Auto-purges records older than 7 days every 12 hours.
        """
        now = int(time.time())
        wib_now = datetime.datetime.now(WIB_TZ).strftime("%Y-%m-%d %H:%M:%S WIB")

        # Auto-purge logs older than 7 days every 12 hours
        if (now - self._last_purge_time) > 43200:
            self._last_purge_time = now
            try:
                self.cleanup_old_position_logs(retention_days=7)
            except Exception as e:
                print(f"[SQLITE ERROR] Auto-purge failed: {e}")

        rows_to_insert = []
        for f in flight_list:
            lat = f.get("lat")
            lon = f.get("lon")
            if lat is None or lon is None or not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
                continue

            is_mil = bool(f.get("is_military"))
            in_fir = bool(f.get("in_fir_indonesia"))
            has_det = bool(f.get("has_detection"))

            # Option A filter: Military OR Indonesian FIR OR Active Detections
            if not (is_mil or in_fir or has_det):
                continue

            icao = (f.get("icao24") or "").upper().strip()
            if not icao:
                continue

            # Debouncing: skip if plane moved < 0.001 deg (~100m) and < 30s elapsed
            last = self._last_logged.get(icao)
            if last:
                last_lat, last_lon, last_alt, last_t = last
                if (now - last_t) < 30 and abs(lat - last_lat) < 0.001 and abs(lon - last_lon) < 0.001:
                    continue

            reasons = []
            if is_mil: reasons.append("MILITARY")
            if in_fir: reasons.append("FIR_INDONESIA")
            if has_det: reasons.append("ALERT")
            reason_str = "+".join(reasons) or "PRIORITY"

            det_label = ""
            if has_det and f.get("detections"):
                det_label = f["detections"][0].get("label", "")

            rows_to_insert.append((
                now,
                wib_now,
                icao,
                f.get("callsign") or "NO CALL",
                f.get("country") or "Unknown",
                f.get("flight_type") or ("military" if is_mil else "airline"),
                f.get("category") or ("military_general" if is_mil else "airline"),
                1 if is_mil else 0,
                1 if in_fir else 0,
                f.get("fir_name") or "",
                round(float(lat), 5),
                round(float(lon), 5),
                f.get("alt_ft"),
                f.get("speed_kts"),
                round(float(f["heading"]), 1) if f.get("heading") is not None else None,
                f.get("vert_rate_fpm"),
                f.get("squawk") or "",
                1 if has_det else 0,
                det_label,
                reason_str
            ))
            self._last_logged[icao] = (lat, lon, f.get("alt_ft"), now)

        if not rows_to_insert:
            return 0

        # Memory cleanup for debouncer if tracking dictionary grows too large
        if len(self._last_logged) > 3000:
            threshold = now - 3600
            self._last_logged = {k: v for k, v in self._last_logged.items() if v[3] > threshold}

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO flight_position_logs (
                    timestamp, datetime_wib, icao24, callsign, country, flight_type, category,
                    is_military, in_fir_indo, fir_name, lat, lon, alt_ft, speed_kts, heading,
                    vert_rate_fpm, squawk, has_detection, detection_label, log_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows_to_insert)
            conn.commit()

        return len(rows_to_insert)

    def get_flight_history(self, icao24, limit=200, start_time=None, end_time=None):
        """Retrieve historical coordinate points and telemetry for a specific aircraft hex."""
        icao = (icao24 or "").upper().strip()
        if not icao:
            return []
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM flight_position_logs WHERE icao24 = ?"
            params = [icao]
            if start_time:
                query += " AND timestamp >= ?"
                params.append(int(start_time))
            if end_time:
                query += " AND timestamp <= ?"
                params.append(int(end_time))
            query += " ORDER BY timestamp ASC LIMIT ?"
            params.append(min(int(limit), 1000))
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def get_recent_flight_logs(self, limit=100, is_military=None, in_fir=None):
        """Retrieve recent priority position records across all flights."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM flight_position_logs WHERE 1=1"
            params = []
            if is_military is not None:
                query += " AND is_military = ?"
                params.append(1 if is_military else 0)
            if in_fir is not None:
                query += " AND in_fir_indo = ?"
                params.append(1 if in_fir else 0)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(min(int(limit), 500))
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def cleanup_old_position_logs(self, retention_days=7):
        """Purge position records older than retention period to protect VPS disk space."""
        cutoff = int(time.time()) - (retention_days * 86400)
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM flight_position_logs WHERE timestamp < ?", (cutoff,))
            deleted = cur.rowcount
            conn.commit()
            if deleted > 0:
                print(f"[SQLITE] Auto-purged {deleted} historical position records older than {retention_days} days.")
            return deleted

    def get_database_stats(self):
        """Get high-level storage and volume metrics for SQLite database."""
        db_size_bytes = 0
        if os.path.exists(self.db_path):
            db_size_bytes = os.path.getsize(self.db_path)
            wal_path = self.db_path + "-wal"
            if os.path.exists(wal_path):
                db_size_bytes += os.path.getsize(wal_path)

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM flight_position_logs")
            total_positions = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(DISTINCT icao24) as cnt FROM flight_position_logs")
            unique_aircraft = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM alerts_history")
            total_alerts = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM flight_routes")
            total_routes = cur.fetchone()["cnt"]

            cur.execute("SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM flight_position_logs")
            t_row = cur.fetchone()
            oldest_ts = t_row["oldest"] if t_row else None
            newest_ts = t_row["newest"] if t_row else None

            return {
                "db_path": self.db_path,
                "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
                "total_position_logs": total_positions,
                "unique_aircraft_tracked": unique_aircraft,
                "total_alerts_logged": total_alerts,
                "total_cached_routes": total_routes,
                "oldest_log_timestamp": oldest_ts,
                "newest_log_timestamp": newest_ts,
                "retention_policy": "7 days auto-purge (Option A: Military + Indonesian FIR + Alerts)"
            }


