# 📡 Panduan Singkat Akses API OpenSky Network (Data Militer)

Panduan ini ditujukan bagi developer untuk mengakses API OpenSky Network secara langsung, melakukan autentikasi OAuth 2.0, memfilter penerbangan militer, serta memahami struktur data yang dihasilkan.

---

## 📁 Berkas dalam Paket Ini

1. **`credentials.json`** : Kredensial API (`clientId` dan `clientSecret`).
2. **`DOKUMENTASI_API.md`** : Panduan teknis akses API dan penjelasan data (berkas ini).
3. **`sample_data.json`** : Contoh nyata data JSON hasil respons penerbangan militer terkini.

---

## 1. Kredensial API

Kredensial tersimpan di `credentials.json`:
```json
{
  "clientId": "aisorutech@gmail.com-api-client",
  "clientSecret": "z3AOahCwxhuZE18tgKcpjgo4y3MNG18N"
}
```

---

## 2. Langkah 1: Dapatkan Bearer Access Token (OAuth 2.0)

OpenSky Network menggunakan alur **OAuth 2.0 Client Credentials**. Sebelum memanggil data, tukarkan kredensial dengan access token.

- **Method**: `POST`
- **URL**: `https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token`
- **Header**: `Content-Type: application/x-www-form-urlencoded`
- **Body**:
  ```text
  grant_type=client_credentials&client_id=aisorutech@gmail.com-api-client&client_secret=z3AOahCwxhuZE18tgKcpjgo4y3MNG18N
  ```

### Contoh cURL:
```bash
curl -X POST "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=aisorutech@gmail.com-api-client" \
  -d "client_secret=z3AOahCwxhuZE18tgKcpjgo4y3MNG18N"
```

### Format Respons:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "expires_in": 1800,
  "token_type": "Bearer"
}
```
> **Catatan**: Token berlaku selama **1800 detik (30 menit)**. Simpan token di memori aplikasi Anda dan perbarui setiap ~28 menit.

---

## 3. Langkah 2: Ambil Data Penerbangan Live

Gunakan access token yang didapat pada header `Authorization: Bearer <token>`.

- **Method**: `GET`
- **URL**: `https://opensky-network.org/api/states/all`
- **Header**:
  ```http
  Authorization: Bearer <access_token>
  ```

### Contoh cURL:
```bash
curl -X GET "https://opensky-network.org/api/states/all" \
  -H "Authorization: Bearer <access_token>"
```

### Format Respons OpenSky (Array State Vectors):
```json
{
  "time": 1793079925,
  "states": [
    [
      "8a0abe",      // [0]  icao24 (Hex transponder)
      "SPRTN07 ",    // [1]  callsign
      "Indonesia",   // [2]  origin_country
      1793079916,    // [3]  time_position (epoch)
      1793079916,    // [4]  last_contact (epoch)
      107.1037,      // [5]  longitude
      -6.5918,       // [6]  latitude
      2514.6,        // [7]  baro_altitude (meter)
      false,         // [8]  on_ground (true/false)
      124.0,         // [9]  velocity (m/s)
      308.1,         // [10] true_track / heading (derajat)
      0.0,           // [11] vertical_rate (m/s)
      null,          // [12] sensors
      2610.0,        // [13] geo_altitude (meter)
      null,          // [14] squawk code
      false,         // [15] spi
      0              // [16] position_source
    ]
  ]
}
```

---

## 4. Langkah 3: Filter Khusus Pesawat Militer

Data dari OpenSky mencakup ribuan penerbangan sipil dan militer bercampur. Untuk menyaring **hanya penerbangan militer**:

1. **Cocokkan Kode Hex ICAO24 ([0])**:
   - Blok heksadesimal militer khusus (contoh alokasi US DoD: `ae0000` s/d `afffff`).
   - Database transponder militer dunia (Mictronics / Tar1090 military database).
2. **Periksa Awalan Callsign ([1])**:
   - Tanda panggil taktis militer yang umum:
     `RCH` / `REACH` (US Air Mobility Command), `ASY` (Royal Australian Air Force), `RRR` (RAF UK), `FAF` (French Air Force), `GAF` (German Air Force), `IAM` (Italian Air Force), `USAF`, `NAVY`, `ARMY`, `IDAF` / `SPRTN` (TNI AU Indonesia), `VIPER`, `FORTE`, `SENTRY`.

---

## 5. Penjelasan Struktur Data Hasil Olahan (`sample_data.json`)

Berkas `sample_data.json` adalah contoh data penerbangan militer yang telah diolah, dikonversi ke satuan penerbangan standar (kaki & knots), serta dilengkapi informasi wilayah udara Indonesia (FIR) dan rute bandara:

```json
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
  "alt_ft": 8250,
  "speed_kts": 241,
  "heading": 308.1,
  "vert_rate_fpm": 0,
  "on_ground": false,
  "squawk": "",
  "is_emergency": false,
  "in_fir_indonesia": true,
  "fir_name": "FIR Jakarta",
  "origin": "[WIHH] Halim Perdanakusuma International Airport (Jakarta)",
  "destination": "Tactical Sortie / In Flight",
  "last_contact": 1793079916
}
```

### Kamus Field:
| Field | Tipe | Keterangan |
| :--- | :--- | :--- |
| `icao24` | String | Kode unik 24-bit transponder ICAO pesawat |
| `callsign` | String | Tanda panggil operasional penerbangan |
| `reg` | String | Nomor ekor / registrasi pesawat |
| `type_code` | String | Kode tipe pesawat standar ICAO (misal: `FA7X`, `C17`, `F16`) |
| `desc` | String | Nama pabrikan dan model pesawat lengkap |
| `operator` | String | Angkatan bersenjata / dinas militer pemilik armada |
| `category` | String | Kategori: `fighter`, `bomber`, `tanker`, `transport`, `helicopter`, `recon`, `trainer`, `military_general` |
| `country` | String | Negara pendaftar transponder |
| `lat`, `lon` | Float | Koordinat posisi GPS (WGS-84) |
| `alt_ft` | Integer | Ketinggian terbang dalam **kaki (feet)** (`meter * 3.28084`) |
| `speed_kts` | Integer | Kecepatan darat dalam **knots** (`m/s * 1.94384`) |
| `heading` | Float | Arah terbang (derajat sejati) dari Utara (0°–360°) |
| `vert_rate_fpm` | Integer | Kecepatan naik/turun dalam **feet per minute (FPM)** |
| `on_ground` | Boolean | `true` jika di darat, `false` jika mengudara |
| `squawk` | String | Kode transponder 4 digit (misal: `7700` = darurat) |
| `is_emergency` | Boolean | `true` jika terdeteksi darurat (`7700`, `7600`, `7500`) |
| `in_fir_indonesia` | Boolean | `true` jika berada di dalam ruang udara Indonesia |
| `fir_name` | String | Wilayah udara: `"FIR Jakarta"` atau `"FIR Ujung Pandang"` |
| `origin` | String | Bandara / Lanud asal keberangkatan |
| `destination` | String | Bandara tujuan pendaratan atau status sortie |
| `last_contact` | Integer | Unix epoch timestamp sinyal terakhir diterima |

---

## 6. Batasan Rate Limit OpenSky
- Akun terautentikasi memiliki batas pemanggilan yang aman pada interval **10–15 detik sekali**.
- Jangan melakukan polling dalam interval kurang dari 5 detik agar kuota harian *credits* API tidak cepat habis.
