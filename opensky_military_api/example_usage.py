#!/usr/bin/env python3
"""
Contoh Penggunaan Library OpenSkyMilitaryClient untuk Developer Backend Python
"""

from client import OpenSkyMilitaryClient
import json

def main():
    print("Menginisialisasi OpenSky Military Client...")
    client = OpenSkyMilitaryClient()

    # 1. Ambil data semua penerbangan militer aktif dunia
    print("Mengambil data penerbangan militer...")
    result = client.get_live_military_flights()

    stats = result["stats"]
    flights = result["flights"]

    print(f"\nTotal Pesawat Militer Aktif: {stats['total_military']}")
    print(f"Sedang Mengudara: {stats['airborne']}")
    print(f"Di Wilayah Udara Indonesia (FIR): {stats['in_fir_indonesia']}")

    print("\n--- 5 Pesawat Militer Teratas ---")
    for f in flights[:5]:
        fir_info = f" | Wilayah: {f['fir_name']}" if f['in_fir_indonesia'] else ""
        print(f"ICAO: {f['icao24']} | Callsign: {f['callsign']:<8} | Model: {f['desc']} | Negara: {f['country']}{fir_info}")

    # 2. Filter khusus pesawat yang ada di wilayah FIR Indonesia
    print("\n--- Pesawat Militer di Wilayah Udara Indonesia ---")
    indo_flights = client.get_live_military_flights(fir_only=True)
    for f in indo_flights["flights"]:
        print(f"- [{f['fir_name']}] {f['callsign']} ({f['desc']}) - Ketinggian: {f['alt_ft']} ft, Kecepatan: {f['speed_kts']} kts")

if __name__ == "__main__":
    main()
