#!/usr/bin/env python3
"""
OpenSky Military ADS-B Client & Microservice
Standalone SDK for fetching, filtering, and enriching live military flights
using OpenSky Network OAuth2 API, verified military databases, and FIR Indonesia detection.

Usage:
  1. As a Python Library:
     from client import OpenSkyMilitaryClient
     client = OpenSkyMilitaryClient()
     data = client.get_live_military_flights()

  2. As a CLI Tool:
     python3 client.py --output military_flights.json
     python3 client.py --fir-only

  3. As a REST API Microservice:
     python3 client.py --serve --port 5000
"""

import os
import sys
import gzip
import json
import time
import math
import argparse
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
MILITARY_DB_FILE = os.path.join(BASE_DIR, "data", "military_db.json.gz")
AIRPORTS_DB_FILE = os.path.join(BASE_DIR, "data", "airports.json.gz")
FIR_GEOJSON_FILE = os.path.join(BASE_DIR, "data", "fir_indonesia.geojson")

TACTICAL_CALLSIGNS = (
    "RCH", "REACH", "RRR", "FAF", "GAF", "BAF", "IAM", "ASY", "CFC", 
    "ROFAF", "PLF", "THK", "NAVY", "ARMY", "USAF", "JAKE", "TOPCAT", 
    "DOOM", "VIPER", "COBRA", "BONE", "HAWK", "KNIFE", "TEAL", "IDAF", 
    "FORTE", "HOMER", "SNOOP", "SENTRY", "COWBOY", "EVAC", "AIRFORCE", 
    "SWIFT", "SPAR", "TITAN", "TALON", "VALKYRIE", "RAVEN", "GHOST", 
    "REAPER", "PREDTR", "SHADOW", "DRAGON", "RHINO", "SNIPER", "STRIKE",
    "SPRTN", "ANGEL", "HERC", "PAT", "JASDF"
)

class OpenSkyMilitaryClient:
    def __init__(self, credentials_path=None, data_dir=None):
        self.creds_path = credentials_path or CREDENTIALS_FILE
        self.data_dir = data_dir or os.path.join(BASE_DIR, "data")
        
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.token_expiry = 0
        
        self.mil_db = {}
        self.airports_db = {}
        self.fir_features = []
        self.route_cache = {}
        
        self._load_credentials()
        self._load_databases()

    def _load_credentials(self):
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"Credentials file not found: {self.creds_path}")
        with open(self.creds_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.client_id = data.get("clientId")
            self.client_secret = data.get("clientSecret")
        if not self.client_id or not self.client_secret:
            raise ValueError("Credentials file must contain 'clientId' and 'clientSecret'")

    def _load_databases(self):
        # 1. Military aircraft DB (23,100+ airframes)
        mil_file = os.path.join(self.data_dir, "military_db.json.gz")
        if os.path.exists(mil_file):
            with gzip.open(mil_file, "rt", encoding="utf-8") as f:
                self.mil_db = json.load(f)

        # 2. Airports DB (29,300+ airports/lanud)
        apt_file = os.path.join(self.data_dir, "airports.json.gz")
        if os.path.exists(apt_file):
            with gzip.open(apt_file, "rt", encoding="utf-8") as f:
                self.airports_db = json.load(f)

        # 3. FIR Indonesia boundaries
        fir_file = os.path.join(self.data_dir, "fir_indonesia.geojson")
        if os.path.exists(fir_file):
            with open(fir_file, "r", encoding="utf-8") as f:
                fir_data = json.load(f)
            for feat in fir_data.get("features", []):
                name = feat.get("properties", {}).get("name", "FIR Indonesia")
                coords = feat.get("geometry", {}).get("coordinates", [])
                rings = []
                for ring in coords:
                    if len(ring) > 20:
                        min_x = min(p[0] for p in ring)
                        max_x = max(p[0] for p in ring)
                        min_y = min(p[1] for p in ring)
                        max_y = max(p[1] for p in ring)
                        rings.append({
                            "bbox": (min_x, max_x, min_y, max_y),
                            "points": ring
                        })
                self.fir_features.append({"name": name, "rings": rings})

    def get_token(self):
        """Acquires or reuses OpenSky OAuth2 token (valid for 30m)"""
        now = time.time()
        if self.access_token and now < (self.token_expiry - 60):
            return self.access_token

        url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        payload = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 1800)
            self.token_expiry = now + expires_in
            return self.access_token

    def is_in_fir_indonesia(self, lat, lon):
        """Checks if coordinate is inside Indonesian FIR airspace (Ray-casting)"""
        if lat is None or lon is None or not self.fir_features:
            return False, None
        for fir in self.fir_features:
            for ring in fir["rings"]:
                min_x, max_x, min_y, max_y = ring["bbox"]
                if not (min_x <= lon <= max_x and min_y <= lat <= max_y):
                    continue
                # Ray casting point-in-polygon
                poly = ring["points"]
                inside = False
                n = len(poly)
                p1x, p1y = poly[0]
                for i in range(1, n + 1):
                    p2x, p2y = poly[i % n]
                    if lat > min(p1y, p2y):
                        if lat <= max(p1y, p2y):
                            if lon <= max(p1x, p2x):
                                if p1y != p2y:
                                    xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                                if p1x == p2x or lon <= xints:
                                    inside = not inside
                    p1x, p1y = p2x, p2y
                if inside:
                    return True, fir["name"]
        return False, None

    def resolve_airport(self, code):
        """Translates ICAO airport code (e.g. WARJ) to name, city, and country"""
        if not code:
            return None
        c = code.upper().strip()
        data = self.airports_db.get(c)
        if data:
            return {
                "icao": c,
                "name": data[0],
                "city": data[1],
                "country": data[2],
                "lat": data[3],
                "lon": data[4]
            }
        return {"icao": c, "name": c, "city": "", "country": "", "lat": None, "lon": None}

    def get_live_military_flights(self, fir_only=False):
        """
        Fetches all live global flights from OpenSky Network, filters exclusively
        for military airframes, and enriches with categories, FIR status, and routes.
        """
        token = self.get_token()
        headers = {
            "User-Agent": "OpenSkyMilitarySDK/1.0",
            "Authorization": f"Bearer {token}"
        }

        url = "https://opensky-network.org/api/states/all"
        req = urllib.request.Request(url, headers=headers)

        t0 = time.time()
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))
            states = raw_data.get("states", [])
            server_time = raw_data.get("time", int(time.time()))

        flights = []
        country_counts = {}
        cat_counts = {}
        emergency_count = 0
        fir_indo_count = 0

        for s in states:
            icao = (s[0] or "").strip().lower()
            callsign = (s[1] or "").strip()
            country = s[2] or "Unknown"
            lon = s[5]
            lat = s[6]
            baro_alt = s[7]
            on_ground = bool(s[8])
            velocity = s[9]
            heading = s[10]
            vert_rate = s[11]
            squawk = (s[14] or "").strip()

            is_military = False
            db_entry = self.mil_db.get(icao)
            reg, type_code, desc, operator, category = "", "", "", "", "military_general"

            if db_entry:
                is_military = True
                reg, type_code, desc, operator, category = db_entry
            else:
                if callsign and callsign.upper().startswith(TACTICAL_CALLSIGNS):
                    is_military = True
                    desc = "Tactical Callsign"
                    operator = f"{country} Armed Forces"
                    category = "military_general"
                elif icao.startswith(("ae", "af")):
                    is_military = True
                    desc = "US DoD Allocation"
                    operator = "United States Armed Forces"
                    category = "military_general"

            if not is_military:
                continue

            in_fir_indo, fir_name = self.is_in_fir_indonesia(lat, lon)
            if in_fir_indo:
                fir_indo_count += 1

            if fir_only and not in_fir_indo:
                continue

            alt_ft = int(baro_alt * 3.28084) if baro_alt is not None else None
            speed_kts = int(velocity * 1.94384) if velocity is not None else None
            vert_rate_fpm = int(vert_rate * 196.85) if vert_rate is not None else None

            is_emergency = squawk in ("7700", "7600", "7500")
            if is_emergency:
                emergency_count += 1

            flight_obj = {
                "icao24": icao.upper(),
                "callsign": callsign if callsign else "NO CALL",
                "reg": reg,
                "type_code": type_code,
                "desc": desc,
                "operator": operator if operator else f"{country} Armed Forces",
                "category": category,
                "country": country,
                "lat": lat,
                "lon": lon,
                "alt_m": baro_alt,
                "alt_ft": alt_ft,
                "speed_kts": speed_kts,
                "heading": heading,
                "vert_rate_fpm": vert_rate_fpm,
                "on_ground": on_ground,
                "squawk": squawk,
                "is_emergency": is_emergency,
                "in_fir_indonesia": in_fir_indo,
                "fir_name": fir_name,
                "last_contact": s[4]
            }

            flights.append(flight_obj)
            country_counts[country] = country_counts.get(country, 0) + 1
            cat_counts[category] = cat_counts.get(category, 0) + 1

        flights.sort(key=lambda x: (x["in_fir_indonesia"], not x["on_ground"], x["alt_ft"] or 0), reverse=True)

        return {
            "status": "success",
            "stats": {
                "total_military": len(flights),
                "airborne": sum(1 for f in flights if not f["on_ground"]),
                "on_ground": sum(1 for f in flights if f["on_ground"]),
                "in_fir_indonesia": fir_indo_count,
                "emergencies": emergency_count,
                "top_countries": sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:8],
                "categories": cat_counts,
                "server_time": server_time,
                "fetch_duration_s": round(time.time() - t0, 2)
            },
            "flights": flights
        }

# ================= Microservice Web Server =================
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class StandaloneAPIHandler(BaseHTTPRequestHandler):
    client = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/military-flights", "/api/military-flights"):
            query = urllib.parse.parse_qs(parsed.query)
            fir_only = query.get("fir_only", ["false"])[0].lower() in ("true", "1")
            data = self.client.get_live_military_flights(fir_only=fir_only)
            self._send_json(data)
            return

        elif path in ("/status", "/api/status"):
            self._send_json({
                "status": "online",
                "client_id": self.client.client_id,
                "military_db_size": len(self.client.mil_db),
                "airports_db_size": len(self.client.airports_db),
                "fir_loaded": len(self.client.fir_features) > 0
            })
            return

        self.send_error(404, "Endpoint not found. Use /military-flights or /status")

    def _send_json(self, data, code=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    parser = argparse.ArgumentParser(description="OpenSky Military ADS-B Standalone Client & Microservice")
    parser.add_argument("--output", "-o", help="Save output JSON to specified file path")
    parser.add_argument("--fir-only", action="store_true", help="Filter only flights inside FIR Indonesia")
    parser.add_argument("--serve", action="store_true", help="Run as REST API microservice")
    parser.add_argument("--port", type=int, default=5000, help="Port for REST API microservice (default: 5000)")
    args = parser.parse_args()

    client = OpenSkyMilitaryClient()

    if args.serve:
        StandaloneAPIHandler.client = client
        server = ThreadingHTTPServer(("", args.port), StandaloneAPIHandler)
        print(f"[*] OpenSky Military API Microservice running on http://localhost:{args.port}/military-flights")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down microservice...")
            server.server_close()
        return

    print("[*] Fetching live military flights from OpenSky Network...")
    result = client.get_live_military_flights(fir_only=args.fir_only)
    stats = result["stats"]
    print(f"[+] Retrieved {stats['total_military']} military aircraft ({stats['airborne']} airborne, {stats['in_fir_indonesia']} in FIR Indonesia).")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"[+] Data exported to {args.output}")
    else:
        # Print top 5 samples to console
        print("\n--- SAMPLE LIVE MILITARY FLIGHTS ---")
        for f in result["flights"][:5]:
            fir_tag = f"[{f['fir_name']}]" if f['in_fir_indonesia'] else ""
            print(f"[{f['icao24']}] {f['callsign']:<9} | {f['desc']} | {f['country']} | Alt: {f['alt_ft']} ft | Spd: {f['speed_kts']} kts {fir_tag}")

if __name__ == "__main__":
    main()
