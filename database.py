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
