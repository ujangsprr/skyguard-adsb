#!/usr/bin/env python3
"""
Build comprehensive aircraft database from tar1090-db (derived from Mictronics readsb DB).
Enriches aircraft with precise airframe categories:
  - Military: fighter, bomber, tanker, transport, recon, helicopter, trainer, drone, military_general
  - Commercial / Civilian: heavy (widebody), narrowbody (airline), cargo_commercial, turboprop, helicopter, business_jet, light_aircraft
Stores them in data/aircraft_db.json.gz for instant server lookup.
"""
import os
import sys
import gzip
import json
import urllib.request
import time

TAR1090_DB_URL = "https://raw.githubusercontent.com/wiedehopf/tar1090-db/csv/aircraft.csv.gz"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "aircraft_db.json.gz")
LEGACY_MIL_FILE = os.path.join(os.path.dirname(__file__), "data", "military_db.json.gz")
LOCAL_CSV_GZ = os.path.join(os.path.dirname(__file__), "data", "aircraft.csv.gz")

CATEGORIES = {
    "fighter": [
        "F15", "F16", "F18", "F22", "F35", "F4", "F5", "EUFI", "RFAL", "M200", 
        "GR4", "TOR", "A10", "AV8B", "HAR", "JAS39", "SU25", "SU27", "SU30", "SU34", 
        "SU35", "SU57", "MG29", "MG31", "MG35", "J10", "J11", "J15", "J16", "J20", "JF17"
    ],
    "bomber": [
        "B52", "B1", "B2", "TU95", "TU22", "TU16", "TU160", "H6"
    ],
    "tanker": [
        "KC35", "K35R", "KC46", "KC10", "K35E", "IL78"
    ],
    "transport": [
        "C130", "C30J", "C17", "C5", "C5M", "A400", "C295", "CN35", "C27J", 
        "IL76", "AN12", "AN26", "AN32", "AN72", "AN70", "AN124", "AN225", "Y20", "C2", "C160", "CV22", "V22"
    ],
    "recon": [
        "E3TF", "E3CF", "E2", "E737", "P8", "P3", "RC135", "U2", "R135", "EP3"
    ],
    "trainer": [
        "T38", "T6", "T45", "PC21", "PC9", "PC7", "KT1", "HAWK", "M346", "T50", 
        "L39", "L159", "G120", "T7", "EMB3", "T1"
    ],
    "drone": [
        "MQ9", "MQ1", "RQ4", "Q4", "MQ4", "MQ25", "WZ7", "TB2"
    ]
}

WIDEBODY_TYPES = {
    "B772", "B773", "B77W", "B77L", "B77F", "B778", "B779",
    "B744", "B748", "B742", "B741", "B74R", "B74S", "B743",
    "B788", "B789", "B78X",
    "B762", "B763", "B764",
    "A332", "A333", "A338", "A339", "A330",
    "A342", "A343", "A345", "A346",
    "A359", "A35K", "A350",
    "A388", "A380",
    "MD11", "DC10", "IL96"
}

TURBOPROP_TYPES = {
    "AT43", "AT45", "AT46", "AT72", "AT73", "AT75", "AT76",
    "DH8A", "DH8B", "DH8C", "DH8D", "Q400",
    "C208", "B350", "BE20", "PC12", "DHC6", "D228", "SW4", "JS31", "JS41", "L410", "SF34"
}

HELICOPTER_TYPES = {
    "H60", "S70", "UH60", "SH60", "H64", "AH64", "H47", "CH47", "H53", "CH53",
    "EC35", "EC45", "EC25", "EC72", "H135", "H145", "H160", "H225", "AS32", "AS55", "AS65", "AS50",
    "B206", "B212", "B412", "B429", "B505", "UH1", "AH1",
    "A109", "A119", "AW13", "AW16", "AW18", "AW10", "AW15",
    "MI8", "MI17", "MI24", "MI28", "MI35", "KA52", "KA27", "S92", "S76",
    "R22", "R44", "R66", "B06", "BK17"
}

BIZJET_TYPES = {
    "GLF4", "GLF5", "GLF6", "GLEX", "GL5T", "GL7T", "GL8T",
    "CL30", "CL35", "CL60", "LJ35", "LJ45", "LJ60", "LJ75",
    "C525", "C560", "C680", "C750", "C25A", "C25B", "C25C",
    "FA7X", "FA8X", "FA50", "F900", "F2TH",
    "E55P", "E50P", "E545", "E550", "HA4T"
}

LIGHT_TYPES = {
    "C150", "C152", "C172", "C182", "C206", "C210",
    "P28A", "PA28", "PA32", "PA34", "PA44", "SR20", "SR22",
    "DA20", "DA40", "DA42", "DA62"
}

def detect_category(type_code, desc, is_mil=False):
    tc = (type_code or "").upper().strip()
    d = (desc or "").upper()

    # Check helicopters first (military or civil)
    if any(tc == h or tc.startswith(h) for h in HELICOPTER_TYPES) or "HELICOPTER" in d:
        return "helicopter"

    # If military aircraft
    if is_mil:
        for cat, types in CATEGORIES.items():
            for t in types:
                if tc == t or tc.startswith(t):
                    return cat

        if any(k in d for k in ["FIGHTER", "INTERCEPTOR", "ATTACK", "RAPTOR", "LIGHTNING", "HORNET", "EAGLE", "VIPER", "FLANKER", "FULCRUM"]):
            return "fighter"
        if any(k in d for k in ["BOMBER", "STRATOFORTRESS", "LANCER", "SPIRIT"]):
            return "bomber"
        if any(k in d for k in ["TANKER", "STRATOTANKER", "PEGASUS", "EXTENDER", "REFUEL"]):
            return "tanker"
        if any(k in d for k in ["TRANSPORT", "HERCULES", "GLOBEMASTER", "GALAXY", "ATLAS", "CARIBOU"]):
            return "transport"
        if any(k in d for k in ["SURVEILLANCE", "RECON", "AWACS", "SENTINEL", "POSEIDON", "ORION", "HAWKEYE"]):
            return "recon"
        if any(k in d for k in ["TRAINER", "TALON", "TEXAN", "PILATUS", "WOONGBI"]):
            return "trainer"
        if any(k in d for k in ["UAV", "DRONE", "REAPER", "PREDATOR", "GLOBAL HAWK"]):
            return "drone"

        return "military_general"

    # Civilian / Commercial Aircraft
    if any(tc == w or tc.startswith(w) for w in WIDEBODY_TYPES):
        return "heavy"
    if any(tc == t or tc.startswith(t) for t in TURBOPROP_TYPES):
        return "turboprop"
    if any(tc == b or tc.startswith(b) for b in BIZJET_TYPES):
        return "business_jet"
    if any(tc == l or tc.startswith(l) for l in LIGHT_TYPES):
        return "light_aircraft"

    # Check keywords in description
    if any(k in d for k in ["777", "787", "747", "A350", "A380", "A330", "A340", "MD-11"]):
        return "heavy"
    if any(k in d for k in ["ATR", "DASH 8", "Q400", "CARAVAN", "TWIN OTTER", "TURBOPROP"]):
        return "turboprop"
    if any(k in d for k in ["GULFSTREAM", "GLOBAL EXPRESS", "CHALLENGER", "CITATION", "LEARJET", "FALCON"]):
        return "business_jet"
    if any(k in d for k in ["CESSNA 1", "PIPER", "CIRRUS", "DIAMOND"]):
        return "light_aircraft"

    return "airline"

def build():
    t0 = time.time()
    full_db = {}
    mil_db = {}

    if os.path.exists(LOCAL_CSV_GZ):
        print(f"Using local aircraft database: {LOCAL_CSV_GZ}")
        import builtins
        ctx = gzip.open(LOCAL_CSV_GZ, "rb")
    else:
        print(f"Downloading aircraft database from {TAR1090_DB_URL}...")
        req = urllib.request.Request(
            TAR1090_DB_URL,
            headers={"User-Agent": "Mozilla/5.0 (SkyGuard ADS-B Tracker)"}
        )
        ctx = gzip.GzipFile(fileobj=urllib.request.urlopen(req, timeout=60))

    with ctx as gz:
            for line in gz:
                try:
                    parts = line.decode("latin1", errors="ignore").strip().split(";")
                    if len(parts) >= 3 and parts[2]:
                        icao = parts[0].strip().lower()
                        if not icao:
                            continue
                        reg = parts[1].strip() if len(parts) > 1 else ""
                        type_code = parts[2].strip()
                        is_mil = (len(parts) >= 4 and len(parts[3]) > 0 and parts[3][0] == "1")
                        desc = parts[4].strip() if len(parts) > 4 else ""
                        operator = parts[6].strip() if len(parts) > 6 else ""

                        cat = detect_category(type_code, desc, is_mil)

                        entry = [reg, type_code, desc, operator, cat, is_mil]
                        full_db[icao] = entry

                        if is_mil:
                            mil_db[icao] = [reg, type_code, desc, operator, cat]
                except Exception:
                    continue

    print(f"Processed in {time.time() - t0:.2f}s. Extracted {len(full_db)} aircraft ({len(mil_db)} military).")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with gzip.open(OUTPUT_FILE, "wt", encoding="utf-8") as f:
        json.dump(full_db, f, separators=(',', ':'))

    with gzip.open(LEGACY_MIL_FILE, "wt", encoding="utf-8") as f:
        json.dump(mil_db, f, separators=(',', ':'))

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Saved compressed aircraft database to {OUTPUT_FILE} ({size_mb:.2f} MB)")
    return len(full_db)

if __name__ == "__main__":
    build()
