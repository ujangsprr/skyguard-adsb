/**
 * Contoh Konsumsi REST API OpenSky Military untuk Developer Node.js / Frontend
 * Mendukung port 5000 (Microservice standalone) atau port 8080 (Server utama)
 */

async function fetchMilitaryFlights() {
  const ports = [5000, 8080];
  let response = null;
  let activeUrl = "";

  for (const port of ports) {
    const testUrl = port === 5000 ? `http://localhost:${port}/military-flights` : `http://localhost:${port}/api/military-flights`;
    try {
      response = await fetch(testUrl);
      if (response.ok) {
        activeUrl = testUrl;
        break;
      }
    } catch (e) {
      // try next
    }
  }

  if (!response || !response.ok) {
    console.error("Gagal terhubung ke API service.");
    console.log("Pastikan service sudah berjalan:");
    console.log("  Opsi 1: python3 client.py --serve --port 5000");
    console.log("  Opsi 2: python3 ../server.py");
    return;
  }

  try {
    console.log(`Berhasil terhubung ke: ${activeUrl}`);
    const data = await response.json();
    const stats = data.stats;
    const flights = data.flights;

    console.log(`\nStatus: ${data.status}`);
    console.log(`Total Pesawat Militer: ${stats.total_military}`);
    console.log(`Sedang Mengudara: ${stats.airborne}`);
    console.log(`Di Ruang Udara Indonesia: ${stats.in_fir_indonesia}`);

    console.log("\n--- Sample Pesawat Militer Terdeteksi ---");
    flights.slice(0, 5).forEach((f, i) => {
      const firTag = f.in_fir_indonesia ? `[${f.fir_name}]` : "";
      console.log(`${i + 1}. [${f.icao24}] ${f.callsign} | ${f.desc || 'Tactical'} | ${f.country} | Alt: ${f.alt_ft} ft ${firTag}`);
    });

  } catch (error) {
    console.error("Gagal memproses data:", error.message);
  }
}

fetchMilitaryFlights();
