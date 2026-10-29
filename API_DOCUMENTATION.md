# SkyGuard Sentinel — ADSB REST API Documentation
**Versi:** 1.2.0  
**Base URL:** `http://localhost:8080` (atau IP/Domain host server Anda)  
**Format Respon:** JSON (`application/json`)  
**CORS:** Enabled (`Access-Control-Allow-Origin: *`)  
**Kompresi:** HTTP Gzip (`Content-Encoding: gzip` otomatis jika didukung klien)  

---

## 1. Ikhtisar & Arsitektur API

SkyGuard Sentinel menyediakan REST API real-time berlatensi rendah untuk pemantauan data penerbangan sipil dan militer dunia. Data diolah secara terpusat dari OpenSky Network OAuth2 API, kemudian diperkaya dengan:
- **Military Airframe DB (22.500+ unit):** Identifikasi tipe skuadron, peran tempur, dan operator bersenjata.
- **Aircraft Master Database (494.900+ unit):** Tipe ICAO (B77W, A320, B738), registrasi ekor, kategori badan pesawat, dan pabrikan.
- **FIR Indonesia Airspace Engine:** Deteksi instan apakah pesawat berada di dalam FIR Jakarta (WIIF) atau FIR Ujung Pandang (WAAF).
- **Flight Anomaly & Emergency Evaluator:** Deteksi transponder squawk darurat (7700, 7600, 7500, 7777), climbing/descent ekstrim, supersonic, dan penetrasi kecepatan tinggi pada ketinggian rendah.
- **Flight Route Engine:** Resolusi bandara asal (*departure*) dan tujuan (*destination*).
- **Planespotters HD Imagery:** Integrasi thumbnail dan foto asli armada pesawat.

---

## 2. Autentikasi & Batasan (Rate Limits)

Saat ini endpoint publik tidak memerlukan API Key jika diakses melalui jaringan lokal atau gateway server:
* **Autentikasi:** Bebas (No Auth required).
* **Cache TTL:** 15 detik (data transponder diperbarui berkala setiap 15 detik untuk mematuhi rate-limit OpenSky).
* **Metode HTTP:** `GET` (query data) dan `POST` (force scan/refresh).

---

## 3. Daftar Endpoint Lengkap

### 3.1 `GET /api/all-flights` atau `GET /api/flights`
Mengambil data seluruh penerbangan aktif (Komersil + Militer) yang sedang terdeteksi.

#### Query Parameters (Opsional):
| Parameter | Tipe | Contoh | Deskripsi |
| :--- | :--- | :--- | :--- |
| `mode` | String | `military`, `commercial`, `all` | Filter armada (default: `all`) |
| `category` | String | `fighter`, `heavy`, `cargo_commercial`, `turboprop`, `business_jet`, `helicopter`, `airline`, `light_aircraft` | Filter kategori spesifik |
| `in_fir` | Boolean | `true` atau `1` | Hanya pesawat di dalam batas FIR Indonesia |
| `emergency` | Boolean | `true` atau `1` | Hanya pesawat berstatus darurat / squawk 7700 / anomali |
| `country` | String | `Indonesia`, `United States`, `Singapore` | Filter negara pendaftaran pesawat |
| `q` atau `search` | String | `GIA`, `A350`, `RCH`, `PK-GIA` | Pencarian teks pada callsign, ICAO24, reg, operator, atau model |
| `airborne` | Boolean | `true` atau `false` | `true`: hanya yang sedang terbang, `false`: termasuk di darat |
| `limit` | Integer | `50` | Membatasi jumlah record yang dikembalikan (default: tanpa batas) |

#### Contoh Request:
```bash
# Semua pesawat militer di dalam FIR Indonesia:
curl -s "http://localhost:8080/api/all-flights?mode=military&in_fir=true"

# Pesawat komersil widebody (Heavy):
curl -s "http://localhost:8080/api/all-flights?category=heavy&limit=10"

# Pesawat darurat (Emergency Squawk):
curl -s "http://localhost:8080/api/all-flights?emergency=true"
```

#### Struktur Objek JSON Response:
```json
{
  "status": "success",
  "stats": {
    "total_all": 6213,
    "total_military": 119,
    "total_commercial": 6094,
    "airborne": 5553,
    "on_ground": 660,
    "in_fir_indonesia": 69,
    "emergencies": 2,
    "detections_count": 185,
    "detections_critical": 2,
    "detections_warning": 102,
    "military_categories": {
      "fighter": 14,
      "transport": 39,
      "tanker": 11,
      "helicopter": 8
    },
    "commercial_categories": {
      "heavy": 1199,
      "airline": 4252,
      "cargo_commercial": 180,
      "turboprop": 257,
      "business_jet": 171,
      "helicopter": 113,
      "light_aircraft": 133
    }
  },
  "flights": [
    {
      "icao24": "7500DA",
      "callsign": "GIA612",
      "reg": "PK-GIE",
      "type_code": "B77W",
      "desc": "BOEING 777-300ER",
      "operator": "Garuda Indonesia",
      "category": "heavy",
      "flight_type": "heavy",
      "is_military": false,
      "is_commercial": true,
      "country": "Indonesia",
      "lat": -6.1256,
      "lon": 106.6558,
      "alt_ft": 35000,
      "alt_m": 10668,
      "speed_kts": 492,
      "heading": 128.4,
      "vert_rate_fpm": 0,
      "on_ground": false,
      "squawk": "2104",
      "spi": false,
      "is_emergency": false,
      "emergency_type": null,
      "detections": [],
      "has_detection": false,
      "max_severity": "normal",
      "in_fir_indonesia": true,
      "fir_name": "FIR JAKARTA",
      "origin": "WIII - Soekarno Hatta Intl",
      "destination": "WADD - I Gusti Ngurah Rai Intl",
      "last_contact": 1761730000
    }
  ]
}
```

---

### 3.2 `GET /api/military-flights`
Khusus mengambil data pesawat militer dunia yang sedang aktif di udara beserta analitik taktisnya.

#### Contoh Request:
```bash
curl -s "http://localhost:8080/api/military-flights"
```

---

### 3.3 `GET /api/track/{icao24}`
Mengambil riwayat lintasan koordinat (*breadcrumb trails*) dari pesawat tertentu berdasarkan kode heksadesimal ICAO24 transponder.

#### Path Parameter:
* `icao24` (Wajib, 6 karakter hex, contoh: `AE01CE` atau `7500DA`).

#### Contoh Request:
```bash
curl -s "http://localhost:8080/api/track/AE01CE"
```

#### Struktur Respon:
```json
{
  "icao24": "AE01CE",
  "trail": [
    [-6.12, 106.65, 31000, 1761729900],
    [-6.18, 106.72, 31500, 1761729915],
    [-6.24, 106.79, 32000, 1761729930]
  ]
}
```
*Format elemen array:* `[latitude, longitude, altitude_kaki, unix_timestamp]`

---

### 3.4 `GET /api/flight-route/{icao24}`
Mengambil resolusi bandara asal keberangkatan (*origin departure*) dan tujuan (*destination*) beserta nama kota dan negara.

#### Contoh Request:
```bash
curl -s "http://localhost:8080/api/flight-route/7500DA"
```

#### Struktur Respon:
```json
{
  "status": "success",
  "icao24": "7500DA",
  "has_route": true,
  "origin_display": "CGK - Soekarno Hatta Intl",
  "dest_display": "DPS - I Gusti Ngurah Rai Intl",
  "origin": {
    "icao": "WIII",
    "name": "Soekarno Hatta International",
    "city": "Jakarta",
    "country": "Indonesia"
  },
  "destination": {
    "icao": "WADD",
    "name": "I Gusti Ngurah Rai International",
    "city": "Denpasar",
    "country": "Indonesia"
  }
}
```

---

### 3.5 `GET /api/aircraft-photo/{icao24}?reg={reg}`
Mengambil URL foto asli pesawat resolusi tinggi dari database Planespotters.

#### Query Parameters:
* `reg` (Opsional, registrasi ekor, contoh: `PK-GIA`, `N12345`).

#### Contoh Request:
```bash
curl -s "http://localhost:8080/api/aircraft-photo/7500DA?reg=PK-GIE"
```

#### Struktur Respon:
```json
{
  "status": "success",
  "has_photo": true,
  "thumbnail": "https://t.planespotters.net/photo/...",
  "large": "https://s.planespotters.net/photo/...",
  "photographer": "Aviation Spotter",
  "link": "https://www.planespotters.net/airframe/..."
}
```

---

### 3.6 `GET /api/fir/indonesia`
Mengambil batas batas ruang udara (Flight Information Region) Jakarta dan Ujung Pandang dalam format GeoJSON standar (RFC 7946).

#### Contoh Request:
```bash
curl -s "http://localhost:8080/api/fir/indonesia"
```

---

### 3.7 `GET /api/stats`
Mengambil metrik ringkasan penerbangan global secara instan tanpa membebani transfer data daftar pesawat.

---

### 3.8 `GET /api/status`
Pemeriksaan kesehatan (*healthcheck*) server dan status autentikasi token OpenSky Network.

---

### 3.9 `POST /api/refresh-all` atau `POST /api/refresh`
Memaksa pemindaian ulang (*force cache refresh*) seketika ke satelit OpenSky tanpa menunggu interval 15 detik.

---

## 4. Nilai Kamus Data (Enums & Constants)

### Kategori Armada (`category`):
* **Militer:**
  * `fighter` — Jet tempur & serang (F-16, Su-30, F-35, Rafale)
  * `bomber` — Pembom strategis (B-52, B-1B, B-2)
  * `transport` — Angkut taktis & kargo militer (C-130 Hercules, C-17 Globemaster, A400M)
  * `tanker` — Pengisian bahan bakar udara (KC-135, KC-46, A330 MRTT)
  * `recon` — Pesawat intai, AWACS, patroli maritim (E-3 Sentry, P-8 Poseidon)
  * `trainer` — Pesawat latih militer (T-50, KT-1B, Hawk 100)
  * `drone` — UAV / UCAV tanpa awak (MQ-9 Reaper, Global Hawk)
  * `military_general` — Pesawat dinas militer lainnya
* **Sipil & Komersil:**
  * `heavy` — Widebody berbadan lebar lorong ganda (B777, B787, A330, A350, A380)
  * `airline` — Jet penumpang narrowbody lorong tunggal (B737, A320, A220, E190)
  * `cargo_commercial` — Maskapai kargo khusus (FedEx, UPS, DHL, Atlas Air)
  * `turboprop` — Pesawat baling-baling regional (ATR 72, Dash 8 Q400, C208 Caravan)
  * `business_jet` — Jet bisnis VIP (Gulfstream, Bombardier Global, Cessna Citation)
  * `helicopter` — Helikopter rotor sipil & militer (Bell 412, H225M, EC135)
  * `light_aircraft` — Pesawat latih & rekreasi kecil (Cessna 172, Piper Archer)
  * `general_aviation` — Penerbangan pribadi umum lainnya

### Kode Anomali & Deteksi (`detections[].type`):
* `squawk_7700`: General In-Flight Emergency
* `squawk_7600`: Radio Communication Failure (Lost Comms)
* `squawk_7500`: Hijack / Unlawful Interference
* `squawk_7777`: Military Intercept Operation Squawk
* `spi_ident`: ATC Special Position Identification Pulled
* `fir_violation`: Foreign military asset entering national FIR without active civilian callsign
* `rapid_descent`: Penurunan tajam darurat (> 3.500 kaki/menit)
* `rapid_climb`: Pendakian mendadak / scramble (> 3.800 kaki/menit)
* `supersonic`: Kecepatan tinggi / mendekati transonik (> 550 kts)
* `stratospheric`: Ketinggian ekstrim (> 50.000 ft)
* `ghost_callsign`: Pesawat terbang di udara tanpa identitas callsign terdaftar

---

## 5. Contoh Implementasi Klien

### Python (Integrasi Bot / Analisis Data)
```python
import requests

BASE_URL = "http://localhost:8080"

# Mengambil semua pesawat di wilayah udara Indonesia
response = requests.get(f"{BASE_URL}/api/all-flights", params={"in_fir": "true"})
data = response.json()

print(f"Total Pesawat di FIR Indonesia: {len(data['flights'])}")
for f in data['flights']:
    tipe = f['type_code'] or 'Unknown'
    print(f"[{f['category'].upper()}] {f['callsign']:<8} | {f['operator']:<25} | {tipe:<5} | Alt: {f['alt_ft']} ft")
```

### JavaScript / Node.js
```javascript
const fetchFlightsInEmergency = async () => {
  const res = await fetch('http://localhost:8080/api/all-flights?emergency=true');
  const { flights } = await res.json();
  
  if (flights.length > 0) {
    console.warn(`⚠️ TERDETEKSI ${flights.length} PESAWAT DALAM STATUS DARURAT!`);
    flights.forEach(f => console.log(`${f.callsign} (${f.icao24}) - Squawk: ${f.squawk}`));
  } else {
    console.log("Semua penerbangan dalam kondisi normal.");
  }
};

fetchFlightsInEmergency();
```
