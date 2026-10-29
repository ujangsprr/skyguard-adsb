# SkyGuard Sentinel — ADSB Real-Time Flight Tracker

**SkyGuard Sentinel** (`skyguard-adsb`) is a high-performance, real-time ADS-B flight surveillance radar and REST API backend. It tracks both military sorties and global commercial aviation using the **OpenSky Network OAuth2 API**, integrated with a 494,900+ aircraft master database (tar1090), Indonesian Flight Information Region (**FIR Jakarta & Ujung Pandang**) airspace surveillance, and in-flight emergency squawk detection.

---

## Features

### 1. Dual Sector Tracking (Military & Commercial)
- **Military Fleet Categorization:** Dedicated silhouettes and tactical identifiers for fighters, bombers, strategic transports, aerial tankers, ISR/AWACS recon, trainers, and UAV/drones.
- **Commercial Fleet Categorization:** Distinct top-down icons and color palettes for widebody heavy airliners (B777, B787, A350, A380), narrowbody passenger airlines (B737, A320), cargo freighters (FedEx, UPS, DHL, Atlas), regional turboprops (ATR 72, Dash 8), business jets (Gulfstream, Citation), civil helicopters, and light GA.
- **Enriched Airframe DB:** 494,976 aircraft indexed with tail registration, ICAO type code, manufacturer description, and operator.

### 2. Indonesian FIR Airspace Surveillance (`fir_indonesia.geojson`)
- Vector polygons for **FIR Jakarta (WIIF)** and **FIR Ujung Pandang (WAAF)** rendered on canvas.
- Instant Point-in-Polygon (PIP) checks marking flights located inside sovereign Indonesian airspace with badges and dedicated filter pills.

### 3. Emergency & Anomaly Detection Engine
- Automated transponder squawk evaluation for **7700** (General Emergency), **7600** (Radio Failure), **7500** (Hijack), and **7777** (Military Intercept).
- Kinematic anomaly evaluation: rapid descent (&le; -3,500 fpm), rapid scramble climb (&ge; +3,800 fpm), supersonic ground speed (&ge; 550 kts), and low-altitude penetration.

### 4. Built-in REST API & Interactive Documentation Portal
- CORS-enabled (`Access-Control-Allow-Origin: *`) REST API with automatic HTTP Gzip compression (reducing payload sizes by over 85%).
- Filter queries supported directly via URL (`?mode=`, `?category=`, `?in_fir=true`, `?emergency=true`, `?country=`, `?q=`, `?limit=`).
- Interactive developer documentation portal available at **`/docs.html`** or **`/docs`**.

---

## Directory Structure

```text
.
├── credentials.example.json   # Template for OpenSky Network OAuth2 credentials
├── fir_indonesia.geojson      # Geospatial boundaries for Jakarta & Ujung Pandang FIR
├── server.py                  # Backend HTTP/REST API server (Zero external pip dependencies)
├── build_db.py                # Database compiler for tar1090 aircraft airframes
├── API_DOCUMENTATION.md       # Comprehensive offline REST API specification
├── data/
│   ├── aircraft_db.json.gz    # Precompiled 494,900+ aircraft master database
│   ├── military_db.json.gz    # Precompiled 22,500+ defense aircraft database
│   └── airports.json.gz       # Global airport & airbase database (29,300+ entries)
├── static/
│   ├── index.html             # Radar tactical dashboard interface
│   ├── docs.html              # Interactive developer API documentation portal
│   ├── css/style.css          # Glassmorphism dark aviation UI theme
│   └── js/
│       ├── app.js             # Client application logic, Leaflet map, and filters
│       └── icons.js           # Directional aircraft SVG silhouette renderer
├── run.sh                     # Launch script
└── package.json               # NPM scripts configuration
```

---

## Quick Start

### 1. Prerequisites
- Python 3.9+ (Built entirely with standard library modules — **no `pip install` required**).
- OpenSky Network API credentials.

### 2. Configure Credentials
Copy the example credentials file:
```bash
cp credentials.example.json credentials.json
```
Edit `credentials.json` with your OpenSky Network OAuth2 Client ID and Client Secret:
```json
{
    "clientId": "your-account-client",
    "clientSecret": "your_client_secret_here"
}
```

### 3. Launch Server

Using Python directly:
```bash
python3 server.py
```

Or using npm:
```bash
npm start
```

Or using the bash script:
```bash
./run.sh
```

### 4. Access the Application
- **Live Radar Map:** [http://localhost:8080](http://localhost:8080)
- **API Documentation Portal:** [http://localhost:8080/docs.html](http://localhost:8080/docs.html)

---

## License
MIT License.
