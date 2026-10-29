# 📡 Dokumentasi Teknis Akses API & Struktur Data SkyGuard Military Radar

Dokumentasi ini menjelaskan secara mendalam arsitektur integrasi API, alur autentikasi OAuth 2.0 OpenSky Network, mekanisme filter pesawat militer, deteksi wilayah udara FIR Indonesia, resolusi rute asal/tujuan (*origin/destination*), serta spesifikasi lengkap seluruh endpoint REST API dan skema data yang dihasilkan.

Hasil ekspor data penerbangan militer terkini disimpan dalam format JSON pada berkas:
👉 **[`exported_military_flights.json`](file:///Volumes/DATA/ADSB/exported_military_flights.json)**

---

## 📑 Daftar Isi

1. [Kredensial API & Alur Autentikasi OAuth 2.0](#1-kredensial-api--alur-autentikasi-oauth-20)
2. [Akses API OpenSky Network Resmi](#2-akses-api-opensky-network-resmi)
3. [Mekanisme Filter Data Pesawat Militer](#3-mekanisme-filter-data-pesawat-militer)
4. [Deteksi Wilayah Udara FIR Indonesia](#4-deteksi-wilayah-udara-fir-indonesia)
5. [Mesin Resolusi Rute Asal & Tujuan](#5-mesin-resolusi-rute-asal--tujuan)
6. [Spesifikasi REST API SkyGuard Sentinel (Local Server)](#6-spesifikasi-rest-api-skyguard-sentinel-local-server)
7. [Contoh Kode Akses API (cURL, Python, Node.js)](#7-contoh-kode-akses-api-curl-python-nodejs)
8. [Struktur Berkas Ekspor Data JSON](#8-struktur-berkas-ekspor-data-json)

---

## 1. Kredensial API & Alur Autentikasi OAuth 2.0

OpenSky Network telah menghentikan metode *HTTP Basic Auth* lama dan mewajibkan autentikasi **OAuth 2.0 Client Credentials Grant Flow**.

### 1.1 Berkas Kredensial
Kredensial disimpan pada berkas [`credentials.json`](file:///Volumes/DATA/ADSB/credentials.json):
```json
{
  "clientId": "aisorutech@gmail.com-api-client",
  "clientSecret": "z3AOahCwxhuZE18tgKcpjgo4y3MNG18N"
}
```

### 1.2 Endpoint Pertukaran Token (Token Exchange)
Untuk mendapatkan Bearer Access Token, kirimkan HTTP POST request ke server Keycloak OpenSky:

- **Method**: `POST`
- **URL**: `https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token`
- **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded
  ```
- **Body / Payload** (form-url-encoded):
  ```text
  grant_type=client_credentials&client_id=aisorutech@gmail.com-api-client&client_secret=z3AOahCwxhuZE18tgKcpjgo4y3MNG18N
  ```

### 1.3 Struktur Data Respons Token
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6...",
  "expires_in": 1800,
  "refresh_expires_in": 0,
  "token_type": "Bearer",
  "not-before-policy": 1649741894,
  "scope": "profile email"
}
```

### 1.4 Penjelasan Field Respons Token
| Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `access_token` | String (JWT) | JSON Web Token yang harus disertakan pada header `Authorization: Bearer <token>` di setiap request data selanjutnya |
| `expires_in` | Integer | Masa aktif token dalam detik (biasanya 1800 detik atau 30 menit) |
| `token_type` | String | Tipe token, yaitu `"Bearer"` |
| `scope` | String | Lingkup hak akses API yang diberikan |

> **Mekanisme Otomatis Backend**: Server [`server.py`](file:///Volumes/DATA/ADSB/server.py) menyimpan token di memori dan secara otomatis merefresh token 60 detik sebelum masa aktif 30 menit berakhir tanpa interupsi pengguna.

---

## 2. Akses API OpenSky Network Resmi

Setelah memiliki token, data lalu lintas penerbangan dunia diambil melalui endpoint utama OpenSky.

### 2.1 Endpoint State Vectors (Live ADS-B Data)
- **Method**: `GET`
- **URL**: `https://opensky-network.org/api/states/all`
- **Headers**:
  ```http
  Authorization: Bearer <access_token>
  User-Agent: SkyGuard-Military-Radar/1.0
  ```

### 2.2 Struktur Respons OpenSky `/api/states/all`
```json
{
  "time": 1793079925,
  "states": [
    [
      "8a0abe",
      "SPRTN07 ",
      "Indonesia",
      1793079916,
      1793079916,
      107.1037,
      -6.5918,
      2514.6,
      false,
      124.0,
      308.1,
      0.0,
      null,
      2610.0,
      null,
      false,
      0
    ]
  ]
}
```

### 2.3 Indeks Array State Vector OpenSky
OpenSky mengembalikan data dalam format array terkompresi per pesawat untuk efisiensi bandwidth:

| Indeks | Nama Field | Tipe Data | Contoh | Keterangan |
| :---: | :--- | :--- | :--- | :--- |
| `[0]` | `icao24` | string | `"8a0abe"` | Alamat 24-bit transponder ICAO dalam notasi heksadesimal |
| `[1]` | `callsign` | string / null | `"SPRTN07 "` | Tanda panggil pesawat (maks. 8 karakter, dapat mengandung spasi) |
| `[2]` | `origin_country` | string | `"Indonesia"` | Negara asal pendaftaran pesawat berdasarkan rentang alokasi ICAO |
| `[3]` | `time_position` | integer / null | `1793079916` | Unix timestamp update koordinat posisi terakhir |
| `[4]` | `last_contact` | integer | `1793079916` | Unix timestamp sinyal terakhir yang diterima dari transponder |
| `[5]` | `longitude` | float / null | `107.1037` | Garis bujur (Longitude WGS-84) dalam derajat desimal |
| `[6]` | `latitude` | float / null | `-6.5918` | Garis lintang (Latitude WGS-84) dalam derajat desimal |
| `[7]` | `baro_altitude` | float / null | `2514.6` | Ketinggian barometrik dalam satuan **meter** |
| `[8]` | `on_ground` | boolean | `false` | Status posisi: `true` di darat, `false` di udara (*airborne*) |
| `[9]` | `velocity` | float / null | `124.0` | Kecepatan darat (*ground speed*) dalam satuan **m/s** |
| `[10]` | `true_track` | float / null | `308.1` | Arah terbang (*heading*) dalam derajat searah jarum jam dari Utara |
| `[11]` | `vertical_rate` | float / null | `0.0` | Laju vertikal naik/turun dalam satuan **m/s** (+ naik, - turun) |
| `[12]` | `sensors` | array / null | `null` | ID sensor penerima ADS-B OpenSky |
| `[13]` | `geo_altitude` | float / null | `2610.0` | Ketinggian geometrik WGS-84 dalam satuan **meter** |
| `[14]` | `squawk` | string / null | `null` | Kode transponder 4 digit (misal: `"7700"` untuk darurat) |
| `[15]` | `spi` | boolean | `false` | Penanda identifikasi khusus (*Special Purpose Indicator*) |
| `[16]` | `position_source` | integer | `0` | Sumber posisi: 0 = ADS-B, 1 = ASTERIX, 2 = MLAT, 3 = FLARM |
| `[17]` | `category` | integer / null | `null` | Kategori kelas kendaraan pesawat jika tersedia |

---

## 3. Mekanisme Filter Data Pesawat Militer

OpenSky Network tidak menyediakan parameter query filter server-side untuk militer. SkyGuard melakukan pemfilteran dan pengayaan secara *real-time* di backend melalui 3 lapisan verifikasi:

```
+-------------------------------------------------------------+
|              OpenSky Live ADS-B Stream                      |
|                 (~6.000+ Pesawat Dunia)                     |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Lapisan 1: Database Pesawat Militer Terverifikasi           |
| Cocokkan ICAO24 dengan 23.109 unit militer (Mictronics DB)  |
+-------------------------------------------------------------+
                               | (Jika tidak cocok)
                               v
+-------------------------------------------------------------+
| Lapisan 2: Deteksi Callsign Taktis / Militer                |
| Awalan: RCH, REACH, RRR, FAF, GAF, USAF, NAVY, ARMY, IDAF,  |
| SPRTN, VIPER, COBRA, FORTE, SENTRY, TITAN, dll.             |
+-------------------------------------------------------------+
                               | (Jika tidak cocok)
                               v
+-------------------------------------------------------------+
| Lapisan 3: Deteksi Blok Heksadesimal Pertahanan             |
| Alokasi US Department of Defense: AE0000 s/d AFFFFF         |
+-------------------------------------------------------------+
                               |
                               v
                 [ Pesawat Militer Terverifikasi ]
```

### Pengkategorian Taktis:
Setiap pesawat dikelompokkan ke dalam kategori militer spesifik:
- `fighter`: Pesawat tempur burgap (F-16, F-15, Su-27/30, Rafale, Eurofighter, F-35, F-22, dll.)
- `bomber`: Pembom strategis (B-52, B-1, B-2, Tu-95, Tu-160)
- `tanker`: Pesawat tanker pengisi bahan bakar udara (KC-135, KC-46, A330 MRTT)
- `transport`: Pesawat angkut militer berat (C-17 Globemaster, C-130 Hercules, A400M, C-295, CN-235)
- `helicopter`: Helikopter serbu dan taktis (AH-64 Apache, UH-60 Black Hawk, CH-47 Chinook, Fennec)
- `recon`: Pesawat intai, patroli maritim & AWACS (P-8 Poseidon, E-3 Sentry, RC-135, Gulfstream Recon)
- `trainer`: Pesawat latih militer (KT-1 Woongbi, T-38 Talon, Pilatus PC-21, Hawk 100/200)
- `drone`: Pesawat tanpa awak / UAV (MQ-9 Reaper, RQ-4 Global Hawk)
- `military_general`: Pesawat angkut VIP militer & operasional umum dinas militer

---

## 4. Deteksi Wilayah Udara FIR Indonesia

Sistem mengintegrasikan batas spasial wilayah informasi penerbangan resmi Indonesia dari berkas [`fir_indonesia.geojson`](file:///Volumes/DATA/ADSB/fir_indonesia.geojson):
- **FIR Jakarta (`WIIF`)**: Meliputi wilayah udara Indonesia bagian Barat dan Tengah (Sumatera, Jawa, Kalimantan Barat/Tengah).
- **FIR Ujung Pandang (`WAAF`)**: Meliputi wilayah udara Indonesia bagian Timur (Sulawesi, Bali, Nusa Tenggara, Maluku, Papua, Kalimantan Timur/Selatan).

### Algoritma Spasial:
Pada setiap siklus pengambilan data, koordinat pesawat (`lat`, `lon`) diperiksa menggunakan algoritma **Ray-Casting Point-in-Polygon**:
1. Pemeriksaan awal menggunakan *Bounding Box (BBox)* untuk efisiensi komputasi mikrodetik.
2. Jika berada dalam rentang BBox, dilakukan kalkulasi perpotongan sinar garis poligon untuk menentukan apakah koordinat berada di dalam poligon FIR Indonesia.
3. Menghasilkan metadata:
   - `in_fir_indonesia`: `true` atau `false`
   - `fir_name`: `"FIR Jakarta"`, `"FIR Ujung Pandang"`, atau `null`

---

## 5. Mesin Resolusi Rute Asal & Tujuan

Untuk menjawab pertanyaan asal keberangkatan (*departure origin*) dan tujuan pendaratan (*arrival destination*):

1. **Pemeriksaan Riwayat Sortie OpenSky**:
   Sistem mengueri endpoint `/api/flights/aircraft?icao24=<hex>&begin=<t-24h>&end=<t>` untuk mengambil `estDepartureAirport` dan `estArrivalAirport`.
2. **Kamus Bandara Global ([`airports.json.gz`](file:///Volumes/DATA/ADSB/data/airports.json.gz))**:
   Sistem memuat 29.311 data bandara dan pangkalan udara (*airbase/lanud*) sipil dan militer di seluruh dunia.
3. **Penerjemahan Kode ICAO**:
   - `WARJ` -> `[WARJ] Lanud Adisutjipto (Yogyakarta, ID)`
   - `WIHH` -> `[WIHH] Lanud Halim Perdanakusuma (Jakarta, ID)`
   - `YPEA` -> `[YPEA] RAAF Base Pearce (Bullsbrook, AU)`
   - `KDOV` -> `[KDOV] Dover Air Force Base (Delaware, US)`
4. **Fallback Spasial Terdekat (Haversine Formula)**:
   Jika pangkalan militer tidak terdaftar dalam jadwal sipil terbuka, sistem menghitung jarak terdekat dari titik koordinat awal penerbangan (*breadcrumb trail*) ke pangkalan udara militer dalam radius 80 km.

---

## 6. Spesifikasi REST API SkyGuard Sentinel (Local Server)

Server lokal [`server.py`](file:///Volumes/DATA/ADSB/server.py) melayani request pada: `http://localhost:8080`.

### 6.1 `GET /api/military-flights`
Mengambil seluruh data penerbangan militer dunia yang sedang aktif saat ini beserta data ringkasan statistik.

- **URL**: `http://localhost:8080/api/military-flights`
- **Method**: `GET`
- **Response Format**: `application/json`

#### Struktur Respons JSON:
```json
{
  "status": "success",
  "stats": {
    "total_military": 71,
    "airborne": 62,
    "on_ground": 9,
    "in_fir_indonesia": 1,
    "emergencies": 0,
    "top_countries": [
      ["United States", 21],
      ["Australia", 13],
      ["Qatar", 8],
      ["Singapore", 5],
      ["Indonesia", 1]
    ],
    "categories": {
      "trainer": 19,
      "recon": 5,
      "bomber": 6,
      "military_general": 18,
      "transport": 17,
      "helicopter": 5,
      "tanker": 1
    },
    "server_time": 1793079925,
    "fetch_duration_s": 1.95,
    "cached_at": 1793079930,
    "next_update": 1793079945
  },
  "flights": [
    {
      "icao24": "8A0ABE",
      "callsign": "SPRTN07",
      "reg": "A-0707",
      "type_code": "FA7X",
      "desc": "DASSAULT Falcon 7X",
      "operator": "Indonesia Armed Forces",
      "category": "military_general",
      "country": "Indonesia",
      "lat": -6.5918,
      "lon": 107.1037,
      "alt_m": 2514.6,
      "alt_ft": 8250,
      "speed_kts": 241,
      "heading": 308.1,
      "vert_rate_fpm": 0,
      "on_ground": false,
      "squawk": "",
      "is_emergency": false,
      "emergency_type": null,
      "in_fir_indonesia": true,
      "fir_name": "FIR Jakarta",
      "origin": "[WIHH] Halim Perdanakusuma International Airport (Jakarta)",
      "destination": "Tactical Sortie / In Flight",
      "last_contact": 1793079916
    }
  ]
}
```

#### Spesifikasi Field Objek `flights[]`:
| Field | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `icao24` | String | Kode heksadesimal 24-bit transponder ICAO (huruf kapital) |
| `callsign` | String | Tanda panggil operasional penerbangan (misal: `"SPRTN07"`, `"RCH842"`) |
| `reg` | String | Nomor registrasi / nomor ekor pesawat (misal: `"A-0707"`) |
| `type_code` | String | Kode tipe pesawat standar ICAO (misal: `"FA7X"`, `"C17"`, `"F16"`) |
| `desc` | String | Nama lengkap pabrikan dan model pesawat |
| `operator` | String | Satuan / angkatan bersenjata pemilik armada (misal: `"Indonesia Armed Forces"`) |
| `category` | String | Klasifikasi taktis: `fighter`, `bomber`, `tanker`, `transport`, `helicopter`, `recon`, `trainer`, `drone`, `military_general` |
| `country` | String | Negara pendaftar transponder |
| `lat` | Float / null | Posisi garis lintang derajat desimal WGS-84 |
| `lon` | Float / null | Posisi garis bujur derajat desimal WGS-84 |
| `alt_m` | Float / null | Ketinggian barometrik dalam meter |
| `alt_ft` | Integer / null | Ketinggian barometrik hasil konversi dalam **feet (kaki)** |
| `speed_kts` | Integer / null | Kecepatan darat hasil konversi dalam **knots** |
| `heading` | Float / null | Arah haluan derajat sejati (*true track*) 0°–360° |
| `vert_rate_fpm` | Integer / null | Kecepatan laju naik/turun dalam **feet per minute (FPM)** |
| `on_ground` | Boolean | `true` jika pesawat berada di landasan, `false` jika sedang terbang |
| `squawk` | String | Kode transponder 4-digit saat ini |
| `is_emergency` | Boolean | `true` jika memancarkan kode darurat internasional (`7700`, `7600`, `7500`) |
| `emergency_type` | String / null | Deskripsi jenis keadaan darurat |
| `in_fir_indonesia`| Boolean | `true` jika posisi koordinat berada di dalam wilayah udara FIR Indonesia |
| `fir_name` | String / null | Nama wilayah FIR (`"FIR Jakarta"` atau `"FIR Ujung Pandang"`) |
| `origin` | String | Nama pangkalan/bandara asal keberangkatan beserta kota & negara |
| `destination` | String | Nama bandara tujuan pendaratan atau status sortie |
| `last_contact` | Integer | Unix epoch timestamp waktu deteksi terakhir |

---

### 6.2 `POST /api/refresh`
Memaksa backend untuk langsung memanggil API OpenSky tanpa menunggu masa kedaluwarsa cache lokal.

- **URL**: `http://localhost:8080/api/refresh`
- **Method**: `POST`
- **Response**: Format JSON yang sama dengan `GET /api/military-flights`.

---

### 6.3 `GET /api/flight-route/<icao24>`
Mengambil rute lengkap asal dan tujuan untuk pesawat tertentu berdasarkan riwayat penerbangan.

- **URL**: `http://localhost:8080/api/flight-route/8A0ABE`
- **Method**: `GET`
- **Contoh Respons JSON**:
```json
{
  "icao24": "8A0ABE",
  "origin": {
    "icao": "WIHH",
    "name": "Halim Perdanakusuma International Airport",
    "city": "Jakarta",
    "country": "ID",
    "lat": -6.2667,
    "lon": 106.8917
  },
  "origin_display": "[WIHH] Halim Perdanakusuma International Airport (Jakarta)",
  "destination": null,
  "dest_display": "Tactical Sortie / In Flight",
  "cached_time": 1793079930
}
```

---

### 6.4 `GET /api/track/<icao24>`
Mengambil riwayat koordinat rekam jejak (*breadcrumb trail*) dari pesawat tertentu.

- **URL**: `http://localhost:8080/api/track/8A0ABE`
- **Method**: `GET`
- **Contoh Respons JSON**:
```json
{
  "icao24": "8a0abe",
  "trail": [
    [-6.6521, 107.1542, 8000, 1793079820],
    [-6.6214, 107.1285, 8150, 1793079860],
    [-6.5918, 107.1037, 8250, 1793079916]
  ]
}
```
*Format elemen array: `[latitude, longitude, altitude_feet, unix_timestamp]`.*

---

### 6.5 `GET /api/fir/indonesia`
Mengambil berkas GeoJSON garis batas wilayah udara FIR Indonesia.

- **URL**: `http://localhost:8080/api/fir/indonesia`
- **Method**: `GET`
- **Response Format**: `application/json` (GeoJSON FeatureCollection)

---

### 6.6 `GET /api/status`
Memeriksa status kesehatan server backend, token OAuth2, dan jumlah database.

- **URL**: `http://localhost:8080/api/status`
- **Method**: `GET`
- **Contoh Respons JSON**:
```json
{
  "status": "online",
  "client_id": "aisorutech@gmail.com-api-client",
  "token_active": true,
  "token_expires_in": 1642,
  "cached_flights_count": 71,
  "military_db_size": 23109,
  "airports_db_size": 29311,
  "fir_loaded": true
}
```

---

## 7. Contoh Kode Akses API (cURL, Python, Node.js)

### 7.1 Menggunakan cURL

#### Ambil Data Penerbangan Militer dari Server Lokal:
```bash
curl -X GET "http://localhost:8080/api/military-flights" \
  -H "Accept: application/json"
```

#### Ambil Token OAuth2 Langsung dari OpenSky:
```bash
curl -X POST "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=aisorutech@gmail.com-api-client" \
  -d "client_secret=z3AOahCwxhuZE18tgKcpjgo4y3MNG18N"
```

---

### 7.2 Menggunakan Python 3

```python
import urllib.request
import json

# 1. Mengambil data penerbangan militer dari server SkyGuard lokal
url = "http://localhost:8080/api/military-flights"
req = urllib.request.Request(url, headers={"Accept": "application/json"})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    
stats = data.get("stats", {})
flights = data.get("flights", [])

print(f"Total Pesawat Militer: {stats.get('total_military')}")
print(f"Pesawat di FIR Indonesia: {stats.get('in_fir_indonesia')}")

for flight in flights[:5]:
    callsign = flight.get("callsign")
    icao = flight.get("icao24")
    model = flight.get("desc")
    origin = flight.get("origin")
    dest = flight.get("destination")
    print(f"[{icao}] {callsign} ({model}) | Asal: {origin} -> Tujuan: {dest}")
```

---

### 7.3 Menggunakan JavaScript / Node.js

```javascript
// Mengambil data menggunakan fetch API
async function getMilitaryFlights() {
  try {
    const response = await fetch("http://localhost:8080/api/military-flights");
    if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
    
    const data = await response.json();
    console.log(`Penerbangan Aktif: ${data.stats.airborne}`);
    console.log(`Di Wilayah Indonesia: ${data.stats.in_fir_indonesia}`);
    
    data.flights.forEach(f => {
      console.log(`${f.callsign} | ${f.desc} | Asal: ${f.origin} -> Tujuan: ${f.destination}`);
    });
  } catch (err) {
    console.error("Gagal mengambil data:", err);
  }
}

getMilitaryFlights();
```

---

## 8. Struktur Berkas Ekspor Data JSON

Data terkini dari panggilan API telah diekspor dan disimpan ke berkas:
👉 [`exported_military_flights.json`](file:///Volumes/DATA/ADSB/exported_military_flights.json)

Berkas JSON ini berisi rekaman data instan snapshot lengkap seluruh pesawat militer aktif di udara, termasuk:
- Seluruh 70+ atribut pesawat militer yang sedang mengudara.
- Deteksi penerbangan militer Indonesia (misal: pesawat VIP/VVIP Dassault Falcon 7X TNI-AU `SPRTN07` di FIR Jakarta).
- Ringkasan statistik sebaran negara dan kategori militer.
