# 📦 OpenSky Military ADS-B Standalone API & SDK

Paket mandiri (*standalone module*) ini dibuat khusus untuk developer lain agar dapat langsung mengakses, memfilter, dan mengintegrasikan data penerbangan militer dunia dari **OpenSky Network API** ke dalam sistem atau aplikasi backend mereka sendiri **tanpa ketergantungan frontend, UI, atau pustaka eksternal**.

---

## 📁 Struktur Berkas Paket Ini

```text
opensky_military_api/
├── credentials.json        # Kredensial OAuth 2.0 OpenSky Network (Client ID & Secret)
├── client.py               # Modul Python utama, CLI, dan REST API microservice
├── example_usage.py        # Contoh skrip Python untuk integrasi langsung
├── example_usage.js        # Contoh skrip JavaScript/Node.js untuk konsumsi API
├── API_DOCUMENTATION.md    # Dokumentasi teknis mendalam spesifikasi data & token
├── sample_output.json      # Contoh rekaman hasil ekspor data penerbangan asli
└── data/
    ├── military_db.json.gz # Database 23.100+ kode ICAO24 pesawat militer terverifikasi
    ├── airports.json.gz    # Database 29.300+ bandara sipil & pangkalan militer dunia
    └── fir_indonesia.geojson # Batas geografis FIR Jakarta & FIR Ujung Pandang
```

---

## ⚡ 3 Cara Menggunakan Paket Ini

### Cara 1: Menggunakan Sebagai Library Python (Import Langsung)
Cocok jika aplikasi Anda dibangun menggunakan Python (Django, Flask, FastAPI, Celery, dll.):

```python
from client import OpenSkyMilitaryClient

client = OpenSkyMilitaryClient()

# Ambil seluruh penerbangan militer aktif dunia:
data = client.get_live_military_flights()
print(f"Total pesawat militer aktif: {data['stats']['total_military']}")

# Atau filter khusus pesawat yang ada di wilayah Indonesia (FIR Jakarta / Ujung Pandang):
indo_flights = client.get_live_military_flights(fir_only=True)
for f in indo_flights["flights"]:
    print(f"[{f['icao24']}] {f['callsign']} ({f['desc']}) - Alt: {f['alt_ft']} ft")
```

Jalankan contoh:
```bash
python3 example_usage.py
```

---

### Cara 2: Menjalankan Sebagai CLI Tool (Export JSON)
Cocok untuk cronjob, skrip otomatisasi, atau pipelines:

```bash
# Cetak ringkasan live militer ke terminal:
python3 client.py

# Simpan hasil ekspor ke berkas JSON:
python3 client.py --output hasil_penerbangan.json

# Hanya ambil data penerbangan di wilayah udara Indonesia:
python3 client.py --fir-only --output militer_indonesia.json
```

---

### Cara 3: Menjalankan Sebagai REST API Microservice
Cocok jika aplikasi backend Anda menggunakan bahasa lain (Node.js, Go, PHP, Java, Ruby, C#):

```bash
# Jalankan microservice pada port 5000:
python3 client.py --serve --port 5000
```

Setelah aktif, aplikasi Anda cukup memanggil HTTP GET:
- `GET http://localhost:5000/military-flights` — Mengambil data seluruh militer dunia
- `GET http://localhost:5000/military-flights?fir_only=true` — Filter khusus FIR Indonesia
- `GET http://localhost:5000/status` — Cek status koneksi dan database

Contoh konsumsi di Node.js:
```bash
node example_usage.js
```

---

## 🔑 Kredensial API OpenSky
Kredensial sudah terkonfigurasi pada berkas `credentials.json`:
- **clientId**: `aisorutech@gmail.com-api-client`
- **clientSecret**: `z3AOahCwxhuZE18tgKcpjgo4y3MNG18N`

*Modul `client.py` menangani seluruh alur pertukaran token OAuth 2.0 dan auto-refresh token secara otomatis.*

---

## 📖 Dokumentasi Lengkap
Untuk spesifikasi seluruh field JSON, struktur data array OpenSky, dan skema respons, silakan baca berkas:
👉 **[`API_DOCUMENTATION.md`](API_DOCUMENTATION.md)**
