#!/bin/bash
# SkyGuard Sentinel - Military Flight Tracker Startup Script
cd "$(dirname "$0")"

echo "======================================================="
echo "  SKYGUARD SENTINEL - MILITARY FLIGHT TRACKER"
echo "  Powered by OpenSky Network OAuth2 & Tar1090 Military DB"
echo "======================================================="

# Check credentials
if [ ! -f "credentials.json" ]; then
    echo "[!] credentials.json not found! Please place your credentials.json in this directory."
    exit 1
fi

# Build military db if missing
if [ ! -f "data/military_db.json.gz" ]; then
    echo "[*] Initializing military aircraft database..."
    python3 build_db.py
fi

echo "[*] Launching SkyGuard Sentinel radar server on http://localhost:8080..."
python3 server.py
