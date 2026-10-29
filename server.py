#!/usr/bin/env python3
"""
SkyGuard Sentinel - Military & Commercial Flight Tracker Backend
Features:
- OpenSky Network OAuth2 Authentication & Token Cache
- Tar1090 Military Aircraft Database (23,100+ military airframes)
- Commercial Flight Detection (ICAO airline prefix database)
- FIR Indonesia Airspace Boundary Checker (Jakarta WIIF & Ujung Pandang WAAF)
- Flight Route Engine: Origin (Asal) & Destination (Tujuan) airport resolution
- REST API & Tactical Web App Server
"""

import os
import sys
import gzip
import json
import time
import math
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
MILITARY_DB_FILE = os.path.join(BASE_DIR, "data", "military_db.json.gz")
AIRCRAFT_DB_FILE = os.path.join(BASE_DIR, "data", "aircraft_db.json.gz")
AIRPORTS_DB_FILE = os.path.join(BASE_DIR, "data", "airports.json.gz")
FIR_GEOJSON_FILE = os.path.join(BASE_DIR, "fir_indonesia.geojson")
STATIC_DIR = os.path.join(BASE_DIR, "static")

PORT = 8080
CACHE_TTL_SECONDS = 15

TACTICAL_CALLSIGNS = (
    "RCH", "REACH", "RRR", "FAF", "GAF", "BAF", "IAM", "ASY", "CFC", 
    "ROFAF", "PLF", "THK", "NAVY", "ARMY", "USAF", "JAKE", "TOPCAT", 
    "DOOM", "VIPER", "COBRA", "BONE", "HAWK", "KNIFE", "TEAL", "IDAF", 
    "FORTE", "HOMER", "SNOOP", "SENTRY", "COWBOY", "EVAC", "AIRFORCE", 
    "SWIFT", "SPAR", "TITAN", "TALON", "VALKYRIE", "RAVEN", "GHOST", 
    "REAPER", "PREDTR", "SHADOW", "DRAGON", "RHINO", "SNIPER", "STRIKE"
)

# Major commercial airline ICAO callsign prefixes (3-letter)
# Used for commercial flight identification
AIRLINE_CALLSIGN_PREFIXES = {
    # Indonesian Airlines
    "GIA": "Garuda Indonesia", "BTK": "Batik Air", "LNI": "Lion Air",
    "SJY": "Sriwijaya Air", "AWQ": "Wings Air", "CTV": "Citilink",
    "IDX": "Indonesia AirAsia", "TGX": "TransNusa",
    # Asian Major Airlines
    "SIA": "Singapore Airlines", "MAS": "Malaysia Airlines", "MXD": "Malindo Air",
    "THA": "Thai Airways", "TVJ": "Thai VietJet", "AIQ": "AirAsia",
    "PAL": "Philippine Airlines", "CPA": "Cathay Pacific", "KAL": "Korean Air",
    "AAR": "Asiana Airlines", "JAL": "Japan Airlines", "ANA": "All Nippon Airways",
    "CSN": "China Southern", "CCA": "Air China", "CES": "China Eastern",
    "VNA": "Vietnam Airlines", "VJC": "VietJet Air", "BAV": "Bamboo Airways",
    "HVN": "Vietnam Airlines",
    # Middle East
    "UAE": "Emirates", "QTR": "Qatar Airways", "ETD": "Etihad Airways",
    "SVA": "Saudi Arabian Airlines", "GFA": "Gulf Air", "FLY": "Flydubai",
    "ABY": "Air Arabia", "KAC": "Kuwait Airways", "OMA": "Oman Air",
    # European
    "BAW": "British Airways", "DLH": "Lufthansa", "AFR": "Air France",
    "KLM": "KLM Royal Dutch", "IBE": "Iberia", "AZA": "ITA Airways",
    "SWR": "SWISS", "AUA": "Austrian Airlines", "SAS": "Scandinavian Airlines",
    "FIN": "Finnair", "LOT": "LOT Polish", "CSA": "Czech Airlines",
    "THY": "Turkish Airlines", "VKO": "Vnukovo Airlines", "AFL": "Aeroflot",
    # North America
    "AAL": "American Airlines", "UAL": "United Airlines", "DAL": "Delta Air Lines",
    "SWA": "Southwest Airlines", "SKW": "SkyWest Airlines", "FFT": "Frontier Airlines",
    "JBU": "JetBlue", "ASA": "Alaska Airlines", "ACA": "Air Canada",
    "WJA": "WestJet",
    # Cargo Airlines
    "FDX": "FedEx", "UPS": "UPS Airlines", "CLX": "Cargolux",
    "GTI": "Atlas Air", "CAO": "Air China Cargo", "CKK": "China Cargo Airlines",
    "MPH": "Martinair", "TPA": "Tampa Cargo", "EIN": "Aer Lingus",
    "MSR": "EgyptAir", "ETH": "Ethiopian Airlines", "KQA": "Kenya Airways",
    # Low Cost
    "RYR": "Ryanair", "EZY": "easyJet", "VLG": "Vueling", "NOZ": "Norwegian",
    "WZZ": "Wizz Air", "TOM": "TUI Airways",
    # Pacific / Oceania
    "QFA": "Qantas", "ANZ": "Air New Zealand", "FJI": "Fiji Airways",
}

# Known cargo airline ICAO callsign prefixes
CARGO_CALLSIGNS = {
    "FDX", "UPS", "CLX", "GTI", "CAO", "CKK", "MPH", "TPA", "ABX", "MAS",
    "PAC", "SOO", "KGA", "SHQ", "VRD"
}

def classify_commercial_flight(icao, callsign, country):
    """Classify a non-military flight into commercial categories.
    Returns (is_commercial, flight_type, operator)
    flight_type: 'airline', 'cargo_commercial', 'charter', 'general_aviation'
    """
    if not callsign:
        return False, "general_aviation", None

    cs = callsign.upper().strip()
    prefix3 = cs[:3] if len(cs) >= 3 else ""
    
    # Check if it's a known cargo airline
    if prefix3 in CARGO_CALLSIGNS:
        return True, "cargo_commercial", f"{prefix3} Cargo"
    
    # Check if it's a known passenger airline
    if prefix3 in AIRLINE_CALLSIGN_PREFIXES:
        return True, "airline", AIRLINE_CALLSIGN_PREFIXES[prefix3]
    
    # Callsign looks like airline format: 3 letters + digits (e.g. ABC123)
    import re
    if re.match(r'^[A-Z]{2,3}\d{1,4}[A-Z]{0,2}$', cs) and len(cs) <= 8:
        return True, "airline", f"{prefix3} Operator"

    # Possibly general aviation (short callsign, registration-style)
    return False, "general_aviation", None

def detect_flight_anomalies(squawk, vert_rate_fpm, speed_kts, alt_ft, on_ground, spi, callsign, is_military, country, in_fir_indo):
    """
    Comprehensive flight detection & anomaly evaluator.
    Evaluates:
      1. Transponder Emergency Squawks (7700, 7600, 7500, 7777)
      2. ATC Special Position Identification (SPI Ident)
      3. Airspace Security (Foreign military aircraft within Indonesian FIR)
      4. Kinematic: Emergency Rapid Descent (<= -3500 fpm)
      5. Kinematic: High Climb Rate / Tactical Scramble (>= +3800 fpm)
      6. Kinematic: High Speed / Supersonic / Overspeed (>= 550 kts)
      7. Tactical: Low-Altitude High-Speed Penetration (<5000 ft @ >320 kts)
      8. Reconnaissance: Stratospheric Flight Level (>= 50,000 ft)
      9. Identity: Ghost Transponder / Anonymous Flight (No callsign airborne)
    Returns: (detections_list, max_severity, is_emergency, primary_label)
    """
    detections = []
    
    # 1. Transponder Squawk Emergency Codes
    if squawk == "7700":
        detections.append({
            "type": "squawk_7700",
            "severity": "critical",
            "label": "EMERGENCY 7700",
            "desc": "General emergency / distress declared via transponder"
        })
    elif squawk == "7600":
        detections.append({
            "type": "squawk_7600",
            "severity": "critical",
            "label": "LOST COMMS 7600",
            "desc": "Radio failure / lost two-way ATC communications"
        })
    elif squawk == "7500":
        detections.append({
            "type": "squawk_7500",
            "severity": "critical",
            "label": "HIJACK 7500",
            "desc": "Unlawful interference / aircraft hijacking reported"
        })
    elif squawk == "7777":
        detections.append({
            "type": "squawk_7777",
            "severity": "warning",
            "label": "MIL INTERCEPT 7777",
            "desc": "Military interception / Air defense radar mission"
        })

    # 2. ATC SPI (Special Position Identification) Pulse
    if spi:
        detections.append({
            "type": "spi_ident",
            "severity": "info",
            "label": "SQUAWK IDENT",
            "desc": "Pilot pulsed transponder IDENT on ATC controller request"
        })

    # 3. Airspace Security: Foreign Military inside Indonesian FIR
    if is_military and in_fir_indo and country and country != "Indonesia":
        detections.append({
            "type": "foreign_mil_fir",
            "severity": "critical",
            "label": "FOREIGN MIL IN FIR",
            "desc": f"Foreign military aircraft ({country}) operating within Indonesian FIR"
        })

    # 4. Kinematic: Emergency / Rapid Descent
    if not on_ground and vert_rate_fpm is not None and (alt_ft or 0) > 4000:
        if vert_rate_fpm <= -4500:
            detections.append({
                "type": "rapid_descent",
                "severity": "critical",
                "label": "RAPID DESCENT",
                "desc": f"Extreme sink rate ({vert_rate_fpm:+,} fpm) - Possible depressurization / emergency dive"
            })
        elif vert_rate_fpm <= -3200:
            detections.append({
                "type": "steep_descent",
                "severity": "warning",
                "label": "STEEP DESCENT",
                "desc": f"Steep sink rate ({vert_rate_fpm:+,} fpm)"
            })

    # 5. Kinematic: High Climb Rate / Tactical Scramble
    if not on_ground and vert_rate_fpm is not None:
        if vert_rate_fpm >= 3800:
            detections.append({
                "type": "rapid_climb",
                "severity": "info" if is_military else "warning",
                "label": "HIGH CLIMB RATE",
                "desc": f"Rapid vertical climb ({vert_rate_fpm:+,} fpm)"
            })

    # 6. Kinematic: High Speed / Supersonic / Overspeed
    if speed_kts is not None and not on_ground:
        if speed_kts >= 550:
            detections.append({
                "type": "supersonic",
                "severity": "warning",
                "label": "HIGH SPEED / MACH",
                "desc": f"High ground speed ({speed_kts} kts)"
            })

    # 7. Low-Altitude High-Speed Penetration Profile (Military Tactical Profile)
    if not on_ground and alt_ft is not None and speed_kts is not None:
        if 500 < alt_ft < 5000 and speed_kts >= 320:
            detections.append({
                "type": "low_high_speed",
                "severity": "warning",
                "label": "LOW-ALT FAST",
                "desc": f"Low-altitude high-speed profile ({alt_ft:,} ft @ {speed_kts} kts)"
            })

    # 8. Stratospheric / High-Altitude Reconnaissance (FL500+)
    if not on_ground and alt_ft is not None and alt_ft >= 50000:
        detections.append({
            "type": "stratospheric",
            "severity": "info",
            "label": "STRATOSPHERIC",
            "desc": f"Stratospheric altitude ({alt_ft:,} ft / FL{alt_ft//100})"
        })

    # 9. Ghost / Anonymous Transponder (No Callsign Airborne)
    clean_call = (callsign or "").strip()
    if not on_ground and (not clean_call or clean_call in ("NO CALL", "NONE", "-------")):
        detections.append({
            "type": "ghost_callsign",
            "severity": "warning" if is_military else "info",
            "label": "NO CALLSIGN",
            "desc": "Airborne transponder active with hidden/missing callsign"
        })

    # Determine max severity
    max_severity = None
    for d in detections:
        if d["severity"] == "critical":
            max_severity = "critical"
            break
        elif d["severity"] == "warning" and max_severity != "critical":
            max_severity = "warning"
        elif d["severity"] == "info" and max_severity is None:
            max_severity = "info"

    is_emergency = (max_severity == "critical")
    primary_label = next((d["label"] for d in detections if d["severity"] == "critical"), None)
    if not primary_label and detections:
        primary_label = detections[0]["label"]

    return detections, max_severity, is_emergency, primary_label


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class OpenSkyAuth:
    def __init__(self, creds_path):
        self.creds_path = creds_path
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.token_expiry = 0
        self.lock = threading.Lock()
        self.load_credentials()

    def load_credentials(self):
        if not os.path.exists(self.creds_path):
            print(f"[AUTH ERROR] {self.creds_path} not found!")
            return
        try:
            with open(self.creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.client_id = data.get("clientId")
                self.client_secret = data.get("clientSecret")
                print(f"[AUTH] Loaded credentials for client: {self.client_id}")
        except Exception as e:
            print(f"[AUTH ERROR] Failed reading credentials: {e}")

    def get_token(self):
        with self.lock:
            now = time.time()
            if self.access_token and now < (self.token_expiry - 60):
                return self.access_token

            print("[AUTH] Requesting new OAuth2 token from OpenSky Network...")
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

            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.access_token = data["access_token"]
                    expires_in = data.get("expires_in", 1800)
                    self.token_expiry = now + expires_in
                    print(f"[AUTH] Successfully acquired token. Valid for {expires_in}s.")
                    return self.access_token
            except Exception as e:
                print(f"[AUTH ERROR] Failed to fetch token: {e}")
                return self.access_token

class FIRChecker:
    """Checks if a point (lat, lon) is within Indonesian Flight Information Regions (FIR)"""
    def __init__(self, geojson_path):
        self.geojson_path = geojson_path
        self.fir_features = []
        self.load_fir()

    def load_fir(self):
        if not os.path.exists(self.geojson_path):
            print(f"[FIR WARN] {self.geojson_path} not found!")
            return
        try:
            with open(self.geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for feat in data.get("features", []):
                name = feat.get("properties", {}).get("name", "FIR Indonesia")
                coords = feat.get("geometry", {}).get("coordinates", [])
                rings = []
                for ring in coords:
                    if len(ring) > 20: # keep meaningful polygons
                        min_x = min(p[0] for p in ring)
                        max_x = max(p[0] for p in ring)
                        min_y = min(p[1] for p in ring)
                        max_y = max(p[1] for p in ring)
                        rings.append({
                            "bbox": (min_x, max_x, min_y, max_y),
                            "points": ring
                        })
                self.fir_features.append({
                    "name": name,
                    "rings": rings
                })
            print(f"[FIR] Loaded {len(self.fir_features)} FIR boundaries (Jakarta & Ujung Pandang).")
        except Exception as e:
            print(f"[FIR ERROR] Failed loading FIR: {e}")

    def check_point(self, lat, lon):
        if lat is None or lon is None or not self.fir_features:
            return False, None

        for fir in self.fir_features:
            for ring in fir["rings"]:
                min_x, max_x, min_y, max_y = ring["bbox"]
                if not (min_x <= lon <= max_x and min_y <= lat <= max_y):
                    continue
                if self._point_in_poly(lon, lat, ring["points"]):
                    return True, fir["name"]
        return False, None

    @staticmethod
    def _point_in_poly(x, y, poly):
        inside = False
        n = len(poly)
        p1x, p1y = poly[0]
        for i in range(1, n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xints:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

class AirportService:
    """Manages 29,000+ airports/airbases and resolves origin/destination"""
    def __init__(self, airports_file):
        self.airports_file = airports_file
        self.airports = {}
        self.load_airports()

    def load_airports(self):
        if not os.path.exists(self.airports_file):
            print(f"[AIRPORT WARN] {self.airports_file} not found!")
            return
        try:
            with gzip.open(self.airports_file, "rt", encoding="utf-8") as f:
                self.airports = json.load(f)
            print(f"[AIRPORT] Loaded {len(self.airports)} airports & airbases.")
        except Exception as e:
            print(f"[AIRPORT ERROR] Failed loading airports: {e}")

    def get_airport(self, code):
        if not code:
            return None
        c = code.upper().strip()
        data = self.airports.get(c)
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

    def find_nearest(self, lat, lon, max_km=80):
        if lat is None or lon is None:
            return None
        closest = None
        min_dist = float("inf")
        # Rough filter within 1 degree first
        for icao, data in self.airports.items():
            alat, alon = data[3], data[4]
            if abs(alat - lat) > 1.0 or abs(alon - lon) > 1.0:
                continue
            dist = self.haversine_km(lat, lon, alat, alon)
            if dist < min_dist and dist <= max_km:
                min_dist = dist
                closest = {
                    "icao": icao,
                    "name": data[0],
                    "city": data[1],
                    "country": data[2],
                    "distance_km": round(min_dist, 1)
                }
        return closest

    @staticmethod
    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        return 2 * R * math.asin(math.sqrt(a))

class MilitaryFlightService:
    def __init__(self, auth: OpenSkyAuth, fir_checker: FIRChecker, airport_service: AirportService):
        self.auth = auth
        self.fir_checker = fir_checker
        self.airport_service = airport_service
        self.mil_db = {}
        self.full_db = {}   # all aircraft (military + civilian) from aircraft_db.json.gz
        self.cached_flights = []       # military only
        self.cached_all_flights = []   # military + commercial
        self.cached_stats = {}
        self.cached_all_stats = {}
        self.last_fetch_time = 0
        self.lock = threading.Lock()
        self.trails = {}  # icao24 -> list of [lat, lon, alt_ft, timestamp]
        self.route_cache = {}  # icao24 -> route info dict
        self.photo_cache = {}  # icao24 -> aircraft photo dict
        self.load_military_db()
        self.load_full_aircraft_db()

    def load_military_db(self):
        if not os.path.exists(MILITARY_DB_FILE):
            print("[DB] Military database not found locally. Running builder...")
            try:
                import build_db
                build_db.build()
            except Exception as e:
                print(f"[DB ERROR] Failed to build database: {e}")

        if os.path.exists(MILITARY_DB_FILE):
            try:
                t0 = time.time()
                with gzip.open(MILITARY_DB_FILE, "rt", encoding="utf-8") as f:
                    self.mil_db = json.load(f)
                print(f"[DB] Loaded {len(self.mil_db)} military aircraft in {time.time() - t0:.2f}s.")
            except Exception as e:
                print(f"[DB ERROR] Failed to read database: {e}")

    def load_full_aircraft_db(self):
        """Load the full aircraft DB (all airframes including civilian) if available."""
        if os.path.exists(AIRCRAFT_DB_FILE):
            try:
                t0 = time.time()
                with gzip.open(AIRCRAFT_DB_FILE, "rt", encoding="utf-8") as f:
                    self.full_db = json.load(f)
                print(f"[DB] Loaded {len(self.full_db)} total aircraft (full DB) in {time.time() - t0:.2f}s.")
            except Exception as e:
                print(f"[DB WARN] Full aircraft DB not ready: {e}")
        else:
            print("[DB] Full aircraft DB not found, will use callsign-based commercial classification.")

    def _process_states(self, states, server_time, now, include_commercial=False):
        """Process OpenSky state vectors and return (flights, stats). 
        If include_commercial=True, include all flights (military + commercial)."""
        mil_flights = []
        com_flights = []
        country_counts = {}
        cat_counts = {}
        com_cat_counts = {}
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
            spi = bool(s[15]) if len(s) > 15 and s[15] is not None else False

            # Classify military
            is_military = False
            db_entry = self.mil_db.get(icao)
            reg, type_code, desc, operator, category = "", "", "", "", "military_general"

            if db_entry:
                is_military = True
                reg, type_code, desc, operator, category = db_entry
            else:
                if callsign and callsign.upper().startswith(TACTICAL_CALLSIGNS):
                    is_military = True
                    desc = "Tactical Military Callsign"
                    operator = f"{country} Armed Forces"
                    category = self._infer_category_from_callsign(callsign)
                elif icao.startswith(("ae", "af")):
                    is_military = True
                    desc = "US DoD Allocation"
                    operator = "United States Armed Forces"
                    category = "military_general"

            # Units conversion
            alt_ft = int(baro_alt * 3.28084) if baro_alt is not None else None
            speed_kts = int(velocity * 1.94384) if velocity is not None else None
            vert_rate_fpm = int(vert_rate * 196.85) if vert_rate is not None else None

            # Check FIR Indonesia boundary
            in_fir_indo, fir_name = self.fir_checker.check_point(lat, lon)

            # Comprehensive Flight Anomalies & Emergency Detection
            detections, max_severity, is_emergency, emergency_type = detect_flight_anomalies(
                squawk=squawk,
                vert_rate_fpm=vert_rate_fpm,
                speed_kts=speed_kts,
                alt_ft=alt_ft,
                on_ground=on_ground,
                spi=spi,
                callsign=callsign,
                is_military=is_military,
                country=country,
                in_fir_indo=in_fir_indo
            )

            if is_emergency:
                emergency_count += 1

            # Route lookup (cached or basic)
            route_info = self.route_cache.get(icao)

            if is_military:
                if in_fir_indo:
                    fir_indo_count += 1

                origin_str = route_info.get("origin_display", "Classified Sortie") if route_info else "Classified Sortie"
                dest_str = route_info.get("dest_display", "In Flight") if route_info else "In Flight"

                flight_obj = {
                    "icao24": icao.upper(),
                    "callsign": callsign if callsign else "NO CALL",
                    "reg": reg,
                    "type_code": type_code,
                    "desc": desc,
                    "operator": operator if operator else f"{country} Armed Forces",
                    "category": category,
                    "flight_type": "military",
                    "is_military": True,
                    "is_commercial": False,
                    "country": country,
                    "lat": lat, "lon": lon,
                    "alt_m": baro_alt, "alt_ft": alt_ft,
                    "speed_kts": speed_kts, "heading": heading,
                    "vert_rate_fpm": vert_rate_fpm,
                    "on_ground": on_ground,
                    "squawk": squawk,
                    "spi": spi,
                    "is_emergency": is_emergency, "emergency_type": emergency_type,
                    "detections": detections,
                    "has_detection": len(detections) > 0,
                    "max_severity": max_severity,
                    "in_fir_indonesia": in_fir_indo, "fir_name": fir_name,
                    "origin": origin_str, "destination": dest_str,
                    "last_contact": s[4]
                }
                mil_flights.append(flight_obj)
                country_counts[country] = country_counts.get(country, 0) + 1
                cat_counts[category] = cat_counts.get(category, 0) + 1

                # Update flight trails
                if lat is not None and lon is not None:
                    if icao not in self.trails:
                        self.trails[icao] = []
                    self.trails[icao].append([lat, lon, alt_ft, int(now)])
                    if len(self.trails[icao]) > 30:
                        self.trails[icao].pop(0)

            elif include_commercial:
                # Try to enrich from full aircraft DB first
                full_entry = self.full_db.get(icao)
                db_reg, db_type, db_desc, db_op, db_cat, db_is_mil = "", "", "", "", "", False
                if full_entry and len(full_entry) >= 6:
                    db_reg, db_type, db_desc, db_op, db_cat, db_is_mil = full_entry
                elif full_entry and len(full_entry) >= 5:
                    db_reg, db_type, db_desc, db_op, db_cat = full_entry

                # Use callsign-based classification as fallback
                is_com, flight_type, com_operator = classify_commercial_flight(icao, callsign, country)

                # If we have DB entry, use its category (unless military)
                if full_entry and not db_is_mil:
                    # If identified as cargo flight, preserve cargo_commercial category
                    if flight_type == "cargo_commercial":
                        category_final = "cargo_commercial"
                    else:
                        category_final = db_cat if db_cat else flight_type
                    reg_final = db_reg or ""
                    type_final = db_type or ""
                    desc_final = db_desc or com_operator or f"{country} Commercial"
                    op_final = db_op or com_operator or f"{country} Commercial"
                    # It's commercial if DB category is not military_general or empty
                    is_com = category_final not in ("military_general", "")
                else:
                    category_final = flight_type
                    reg_final = ""
                    type_final = ""
                    desc_final = com_operator or f"{country} Commercial"
                    op_final = com_operator or f"{country} Commercial"

                if not is_com:
                    continue  # Skip unclassified general aviation

                if in_fir_indo:
                    fir_indo_count += 1

                origin_str = route_info.get("origin_display", "Commercial Route") if route_info else "Commercial Route"
                dest_str = route_info.get("dest_display", "En Route") if route_info else "En Route"

                flight_obj = {
                    "icao24": icao.upper(),
                    "callsign": callsign if callsign else "NO CALL",
                    "reg": reg_final,
                    "type_code": type_final,
                    "desc": desc_final,
                    "operator": op_final,
                    "category": category_final,
                    "flight_type": category_final,
                    "is_military": False,
                    "is_commercial": True,
                    "country": country,
                    "lat": lat, "lon": lon,
                    "alt_m": baro_alt, "alt_ft": alt_ft,
                    "speed_kts": speed_kts, "heading": heading,
                    "vert_rate_fpm": vert_rate_fpm,
                    "on_ground": on_ground,
                    "squawk": squawk,
                    "spi": spi,
                    "is_emergency": is_emergency, "emergency_type": emergency_type,
                    "detections": detections,
                    "has_detection": len(detections) > 0,
                    "max_severity": max_severity,
                    "in_fir_indonesia": in_fir_indo, "fir_name": fir_name,
                    "origin": origin_str, "destination": dest_str,
                    "last_contact": s[4]
                }
                com_flights.append(flight_obj)
                com_cat_counts[category_final] = com_cat_counts.get(category_final, 0) + 1

        return mil_flights, com_flights, country_counts, cat_counts, com_cat_counts, emergency_count, fir_indo_count


    def fetch_live_flights(self, force=False):
        with self.lock:
            now = time.time()
            if not force and (now - self.last_fetch_time) < CACHE_TTL_SECONDS:
                return self.cached_flights, self.cached_stats

            token = self.auth.get_token()
            headers = {
                "User-Agent": "SkyGuard-Military-Radar/1.0",
                "Accept-Encoding": "gzip, deflate"
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            url = "https://opensky-network.org/api/states/all"
            req = urllib.request.Request(url, headers=headers)

            try:
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=35) as resp:
                    raw_bytes = resp.read()
                    encoding = resp.info().get("Content-Encoding", "").lower()
                    if encoding == "gzip":
                        raw_text = gzip.decompress(raw_bytes).decode("utf-8")
                    elif encoding == "deflate":
                        import zlib
                        raw_text = zlib.decompress(raw_bytes).decode("utf-8")
                    else:
                        raw_text = raw_bytes.decode("utf-8")

                    raw_data = json.loads(raw_text)
                    states = raw_data.get("states", [])
                    server_time = raw_data.get("time", int(now))

                mil_flights, com_flights, country_counts, cat_counts, com_cat_counts, emergency_count, fir_indo_count = \
                    self._process_states(states, server_time, now, include_commercial=True)

                # Sort military: FIR first, airborne, altitude desc
                mil_flights.sort(key=lambda x: (x["in_fir_indonesia"], not x["on_ground"], x["alt_ft"] or 0), reverse=True)
                com_flights.sort(key=lambda x: (x["in_fir_indonesia"], not x["on_ground"], x["alt_ft"] or 0), reverse=True)

                all_flights = mil_flights + com_flights

                # Summarize detections & anomalies
                def summarize_detections(flight_list):
                    total_detections = 0
                    critical_count = 0
                    warning_count = 0
                    breakdown = {}
                    alerts = []

                    for f in flight_list:
                        if f.get("has_detection"):
                            total_detections += 1
                            sev = f.get("max_severity")
                            if sev == "critical":
                                critical_count += 1
                            elif sev == "warning":
                                warning_count += 1

                            for d in f.get("detections", []):
                                dtype = d["type"]
                                breakdown[dtype] = breakdown.get(dtype, 0) + 1

                            if sev in ("critical", "warning"):
                                alerts.append({
                                    "icao24": f["icao24"],
                                    "callsign": f["callsign"],
                                    "country": f["country"],
                                    "flight_type": f["flight_type"],
                                    "is_military": f["is_military"],
                                    "severity": sev,
                                    "label": f.get("emergency_type") or (f["detections"][0]["label"] if f["detections"] else "ALERT"),
                                    "desc": f["detections"][0]["desc"] if f["detections"] else "",
                                    "lat": f["lat"],
                                    "lon": f["lon"],
                                    "alt_ft": f["alt_ft"],
                                    "speed_kts": f["speed_kts"],
                                    "squawk": f["squawk"]
                                })

                    alerts.sort(key=lambda x: (x["severity"] == "critical"), reverse=True)
                    return total_detections, critical_count, warning_count, breakdown, alerts[:25]

                mil_det_total, mil_det_crit, mil_det_warn, mil_det_breakdown, mil_alerts = summarize_detections(mil_flights)
                all_det_total, all_det_crit, all_det_warn, all_det_breakdown, all_alerts = summarize_detections(all_flights)

                # Military stats
                stats = {
                    "total_military": len(mil_flights),
                    "airborne": sum(1 for f in mil_flights if not f["on_ground"]),
                    "on_ground": sum(1 for f in mil_flights if f["on_ground"]),
                    "in_fir_indonesia": sum(1 for f in mil_flights if f["in_fir_indonesia"]),
                    "emergencies": mil_det_crit,
                    "detections_count": mil_det_total,
                    "detections_critical": mil_det_crit,
                    "detections_warning": mil_det_warn,
                    "detections_breakdown": mil_det_breakdown,
                    "alerts": mil_alerts,
                    "top_countries": sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:8],
                    "categories": cat_counts,
                    "server_time": server_time,
                    "fetch_duration_s": round(time.time() - t0, 2),
                    "cached_at": int(now),
                    "next_update": int(now) + CACHE_TTL_SECONDS
                }

                # All flights stats
                all_country_counts = {}
                for f in all_flights:
                    all_country_counts[f["country"]] = all_country_counts.get(f["country"], 0) + 1

                all_stats = {
                    "total_military": len(mil_flights),
                    "total_commercial": len(com_flights),
                    "total_all": len(all_flights),
                    "airborne": sum(1 for f in all_flights if not f["on_ground"]),
                    "on_ground": sum(1 for f in all_flights if f["on_ground"]),
                    "in_fir_indonesia": sum(1 for f in all_flights if f["in_fir_indonesia"]),
                    "emergencies": all_det_crit,
                    "detections_count": all_det_total,
                    "detections_critical": all_det_crit,
                    "detections_warning": all_det_warn,
                    "detections_breakdown": all_det_breakdown,
                    "alerts": all_alerts,
                    "top_countries": sorted(all_country_counts.items(), key=lambda x: x[1], reverse=True)[:8],
                    "military_categories": cat_counts,
                    "commercial_categories": com_cat_counts,
                    "server_time": server_time,
                    "fetch_duration_s": round(time.time() - t0, 2),
                    "cached_at": int(now),
                    "next_update": int(now) + CACHE_TTL_SECONDS
                }

                self.cached_flights = mil_flights
                self.cached_all_flights = all_flights
                self.cached_stats = stats
                self.cached_all_stats = all_stats
                self.last_fetch_time = now

                # Clean up old trails
                active_icaos = {f["icao24"].lower() for f in mil_flights}
                for old_icao in list(self.trails.keys()):
                    if old_icao not in active_icaos:
                        del self.trails[old_icao]

                print(f"[API] Updated: {len(mil_flights)} military + {len(com_flights)} commercial flights (FIR Indo: {sum(1 for f in all_flights if f['in_fir_indonesia'])}).")

                return self.cached_flights, self.cached_stats

            except Exception as e:
                # Set backoff so server doesn't freeze or hammer OpenSky on consecutive polls
                self.last_fetch_time = now - CACHE_TTL_SECONDS + 20
                print(f"[API WARN] OpenSky fetch timeout/error ({e}). Serving cached data.")
                return self.cached_flights, self.cached_stats

    def fetch_all_flights(self, force=False):
        """Returns all flights (military + commercial)"""
        self.fetch_live_flights(force=force)
        return self.cached_all_flights, self.cached_all_stats

    def fetch_route_for_aircraft(self, icao):
        """Fetch historical flight schedule/airports from OpenSky for origin and destination"""
        icao_clean = icao.lower().strip()
        now = int(time.time())

        # Check cache (10 min TTL for routes)
        cached = self.route_cache.get(icao_clean)
        if cached and (now - cached.get("cached_time", 0)) < 600:
            return cached

        token = self.auth.get_token()
        headers = {"User-Agent": "SkyGuard-Military-Radar/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        begin = now - 86400  # past 24h
        url = f"https://opensky-network.org/api/flights/aircraft?icao24={icao_clean}&begin={begin}&end={now}"
        req = urllib.request.Request(url, headers=headers)

        origin_airport = None
        dest_airport = None
        origin_display = "Tactical / Unknown Origin"
        dest_display = "Tactical Sortie / In Flight"

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                flights_history = json.loads(resp.read().decode("utf-8"))
                if flights_history:
                    # Pick latest flight
                    latest = flights_history[-1]
                    dep_code = latest.get("estDepartureAirport")
                    arr_code = latest.get("estArrivalAirport")

                    if dep_code:
                        origin_airport = self.airport_service.get_airport(dep_code)
                        origin_display = f"[{dep_code}] {origin_airport['name']} ({origin_airport['city'] or origin_airport['country']})"
                    if arr_code:
                        dest_airport = self.airport_service.get_airport(arr_code)
                        dest_display = f"[{arr_code}] {dest_airport['name']} ({dest_airport['city'] or dest_airport['country']})"
        except Exception as e:
            print(f"[ROUTE WARN] OpenSky flight history lookup failed for {icao_clean}: {e}")

        # If origin still unknown, estimate from initial trail point
        trail = self.trails.get(icao_clean, [])
        if not origin_airport and trail:
            init_lat, init_lon = trail[0][0], trail[0][1]
            nearest = self.airport_service.find_nearest(init_lat, init_lon, max_km=80)
            if nearest:
                origin_airport = nearest
                origin_display = f"Near [{nearest['icao']}] {nearest['name']} (~{nearest['distance_km']}km)"

        route_result = {
            "icao24": icao.upper(),
            "origin": origin_airport,
            "origin_display": origin_display,
            "destination": dest_airport,
            "dest_display": dest_display,
            "cached_time": now
        }

        self.route_cache[icao_clean] = route_result

        # Update in cached_flights list if present
        for f in self.cached_flights:
            if f["icao24"].lower() == icao_clean:
                f["origin"] = origin_display
                f["destination"] = dest_display
                break

        return route_result

    def _infer_category_from_callsign(self, callsign):
        cs = callsign.upper()
        if cs.startswith(("RCH", "REACH", "CFC", "ASY")):
            return "transport"
        if cs.startswith(("VIPER", "COBRA", "HAWK", "TOPCAT", "BONE", "DOOM")):
            return "fighter"
        if cs.startswith(("FORTE", "SENTRY", "SNOOP", "HOMER")):
            return "recon"
        if cs.startswith(("REAPER", "PREDTR")):
            return "drone"
        return "military_general"

    def get_trail(self, icao):
        return self.trails.get(icao.lower(), [])

    def fetch_aircraft_photo(self, icao, reg=""):
        """Fetch actual aircraft photo from Planespotters.net API with caching (hex + reg fallback)"""
        icao_clean = (icao or "").lower().strip()
        reg_clean = (reg or "").strip().upper()
        cache_key = f"{icao_clean}_{reg_clean}"
        if not icao_clean and not reg_clean:
            return {"has_photo": False}

        # Check in-memory cache
        if cache_key in self.photo_cache:
            return self.photo_cache[cache_key]

        headers = {
            "User-Agent": "SkyGuard-Flight-Tracker/1.0 (+aisorutech@gmail.com)"
        }

        # 1. Try lookup by hex
        if icao_clean:
            url = f"https://api.planespotters.net/pub/photos/hex/{icao_clean}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    photos = data.get("photos", [])
                    if photos:
                        p = photos[0]
                        result = {
                            "status": "success",
                            "has_photo": True,
                            "thumbnail": p.get("thumbnail", {}).get("src"),
                            "large": p.get("thumbnail_large", {}).get("src"),
                            "photographer": p.get("photographer", "Planespotters"),
                            "link": p.get("link")
                        }
                        self.photo_cache[cache_key] = result
                        return result
            except Exception:
                pass

        # 2. Try lookup by registration if available
        if reg_clean:
            url = f"https://api.planespotters.net/pub/photos/reg/{urllib.parse.quote(reg_clean)}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    photos = data.get("photos", [])
                    if photos:
                        p = photos[0]
                        result = {
                            "status": "success",
                            "has_photo": True,
                            "thumbnail": p.get("thumbnail", {}).get("src"),
                            "large": p.get("thumbnail_large", {}).get("src"),
                            "photographer": p.get("photographer", "Planespotters"),
                            "link": p.get("link")
                        }
                        self.photo_cache[cache_key] = result
                        return result
            except Exception:
                pass

        result = {"status": "success", "has_photo": False}
        self.photo_cache[cache_key] = result
        return result

def apply_flight_query_filters(flights, query_params):
    """Filter flight list based on query parameters."""
    if not query_params:
        return flights

    cat = query_params.get("category", [None])[0]
    mode = query_params.get("mode", [None])[0]
    in_fir = query_params.get("in_fir", [None])[0]
    emergency = query_params.get("emergency", [None])[0]
    country = query_params.get("country", [None])[0]
    q = query_params.get("q", query_params.get("search", [None]))[0]
    airborne = query_params.get("airborne", [None])[0]
    limit_str = query_params.get("limit", [None])[0]

    filtered = flights
    if mode == "military":
        filtered = [f for f in filtered if f.get("is_military")]
    elif mode == "commercial":
        filtered = [f for f in filtered if f.get("is_commercial")]

    if cat:
        c_low = cat.lower().strip()
        filtered = [f for f in filtered if (f.get("category") or "").lower() == c_low]

    if in_fir in ("true", "1", "yes"):
        filtered = [f for f in filtered if f.get("in_fir_indonesia")]

    if emergency in ("true", "1", "yes"):
        filtered = [f for f in filtered if f.get("is_emergency") or f.get("max_severity") in ("critical", "warning")]

    if country:
        c_low = country.lower().strip()
        filtered = [f for f in filtered if (f.get("country") or "").lower() == c_low]

    if airborne in ("true", "1"):
        filtered = [f for f in filtered if not f.get("on_ground")]
    elif airborne in ("false", "0"):
        filtered = [f for f in filtered if f.get("on_ground")]

    if q:
        q_low = q.lower().strip()
        filtered = [f for f in filtered if (
            q_low in (f.get("callsign") or "").lower() or
            q_low in (f.get("icao24") or "").lower() or
            q_low in (f.get("type_code") or "").lower() or
            q_low in (f.get("reg") or "").lower() or
            q_low in (f.get("operator") or "").lower() or
            q_low in (f.get("desc") or "").lower()
        )]

    if limit_str and limit_str.isdigit():
        filtered = filtered[:int(limit_str)]

    return filtered

class MilitaryRadarHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def finish(self):
        try:
            super().finish()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Interactive API Documentation Portal
        if path in ("/docs", "/api/docs"):
            docs_path = os.path.join(STATIC_DIR, "docs.html")
            if os.path.exists(docs_path):
                with open(docs_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if path == "/api/military-flights":
            flights, stats = flight_service.fetch_live_flights()
            query_params = urllib.parse.parse_qs(parsed.query)
            if query_params:
                flights = apply_flight_query_filters(flights, query_params)
            self._send_json({
                "status": "success",
                "stats": stats,
                "count": len(flights),
                "flights": flights
            })
            return

        elif path in ("/api/all-flights", "/api/flights"):
            flights, stats = flight_service.fetch_all_flights()
            query_params = urllib.parse.parse_qs(parsed.query)
            if query_params:
                flights = apply_flight_query_filters(flights, query_params)
            self._send_json({
                "status": "success",
                "stats": stats,
                "count": len(flights),
                "flights": flights
            })
            return

        elif path.startswith("/api/flight-route/"):
            icao = path.split("/api/flight-route/")[-1]
            route = flight_service.fetch_route_for_aircraft(icao)
            self._send_json(route)
            return

        elif path.startswith("/api/aircraft-photo/"):
            icao = path.split("/api/aircraft-photo/")[-1]
            query_params = urllib.parse.parse_qs(parsed.query)
            reg = query_params.get("reg", [""])[0]
            photo = flight_service.fetch_aircraft_photo(icao, reg)
            self._send_json(photo)
            return

        elif path.startswith("/api/track/"):
            icao = path.split("/api/track/")[-1]
            trail = flight_service.get_trail(icao)
            self._send_json({"icao24": icao, "trail": trail})
            return

        elif path == "/api/fir/indonesia":
            if os.path.exists(FIR_GEOJSON_FILE):
                with open(FIR_GEOJSON_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
                return
            self.send_error(404, "FIR GeoJSON not found")
            return

        elif path == "/api/stats":
            _, stats = flight_service.fetch_live_flights()
            self._send_json(stats)
            return

        elif path == "/api/status":
            self._send_json({
                "status": "online",
                "client_id": auth.client_id,
                "token_active": bool(auth.access_token and time.time() < auth.token_expiry),
                "token_expires_in": max(0, int(auth.token_expiry - time.time())),
                "cached_flights_count": len(flight_service.cached_flights),
                "military_db_size": len(flight_service.mil_db),
                "airports_db_size": len(airport_service.airports),
                "fir_loaded": len(fir_checker.fir_features) > 0
            })
            return

        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Serve static files
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/refresh":
            flights, stats = flight_service.fetch_live_flights(force=True)
            self._send_json({
                "status": "refreshed",
                "stats": stats,
                "flights": flights
            })
            return
        elif self.path == "/api/refresh-all":
            flights, stats = flight_service.fetch_all_flights(force=True)
            self._send_json({
                "status": "refreshed",
                "stats": stats,
                "flights": flights
            })
            return
        self.send_error(404, "Endpoint not found")

    def _send_json(self, data, status_code=200):
        try:
            body = json.dumps(data).encode("utf-8")
            accept_encoding = self.headers.get("Accept-Encoding", "") if self.headers else ""
            use_gzip = "gzip" in accept_encoding and len(body) > 1024

            if use_gzip:
                body = gzip.compress(body, compresslevel=5)

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            if use_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Client closed connection before response was completely transferred (e.g. reload/tab close)
            pass

    def log_message(self, format, *args):
        if args and isinstance(args[0], str) and "/api/" in args[0]:
            sys.stderr.write(f"[HTTP] {args[0]} - {args[1] if len(args) > 1 else ''}\n")

auth = OpenSkyAuth(CREDENTIALS_FILE)
fir_checker = FIRChecker(FIR_GEOJSON_FILE)
airport_service = AirportService(AIRPORTS_DB_FILE)
flight_service = MilitaryFlightService(auth, fir_checker, airport_service)

def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, MilitaryRadarHandler)
    print(f"\n=======================================================")
    print(f"  SKYGUARD MILITARY RADAR - ADSB TRACKER")
    print(f"  Local Radar Server running on: http://localhost:{PORT}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down SkyGuard radar server...")
        httpd.server_close()

if __name__ == "__main__":
    flight_service.fetch_live_flights(force=True)
    run_server()
