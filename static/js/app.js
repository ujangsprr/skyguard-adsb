/**
 * SkyGuard Sentinel — Professional Aviation ADS-B Tracker
 * Features:
 * - Minimalist Aviation Operations Interface (No Clutter, Clean Data)
 * - Esri World Dark Gray Basemap & Satellite Switcher
 * - FIR Indonesia (Clean Airspace Area Line Only, No Labels)
 * - Auto-Polling ON/OFF Toggle
 * - Route Engine: Origin (Asal) & Destination (Tujuan)
 * - Full Telemetry Inspection & Data Export
 */

(() => {
  // Region presets
  const REGIONS = {
    global: { lat: 20, lon: 0, zoom: 3 },
    fir_indonesia: { lat: -2.5, lon: 118.0, zoom: 5 },
    se_asia: { lat: 10.0, lon: 108.0, zoom: 5 },
    europe: { lat: 50.0, lon: 14.0, zoom: 5 },
    middle_east: { lat: 28.0, lon: 45.0, zoom: 5 },
    north_america: { lat: 38.0, lon: -97.0, zoom: 4 },
    asia_pacific: { lat: 20.0, lon: 130.0, zoom: 4 }
  };

  // Basemap Tile Layers (Free, No Watermarks)
  const BASEMAPS = {
    dark: {
      base: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      ref: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
      maxZoom: 16
    },
    satellite: {
      base: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ref: "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      maxZoom: 18
    },
    osm: {
      base: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      ref: null,
      maxZoom: 19
    }
  };

  // State
  let map;
  let baseTileLayer = null;
  let refTileLayer = null;
  let markerLayer;
  let trailLayer;
  let firLayer;
  let isFirVisible = true;
  let isPollingActive = true;
  let allFlights = [];        // flights matching current mode
  let allFlightsRaw = [];     // military only (from /api/military-flights)
  let allFlightsAll = [];     // all flights (military + commercial)
  let filteredFlights = [];
  let markersMap = new Map(); // icao -> Leaflet Marker
  let selectedIcao = null;
  let isAudioEnabled = true;
  let countdownTimer = null;
  let secondsRemaining = 15;
  const pollIntervalSeconds = 15;

  // Flight display mode: 'all' | 'military' | 'commercial'
  let flightMode = 'military';

  // Active filters
  const filters = {
    search: "",
    category: "all",
    country: "all",
    airborneOnly: true,
    inFirIndoOnly: false
  };

  // Web Audio Synthesizer (Subtle, professional)
  const SoundFX = (() => {
    let ctx = null;

    function getAudioContext() {
      if (!ctx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        ctx = new AudioContext();
      }
      if (ctx.state === "suspended") {
        ctx.resume();
      }
      return ctx;
    }

    function playRadarBeep() {
      if (!isAudioEnabled) return;
      try {
        const audio = getAudioContext();
        const osc = audio.createOscillator();
        const gain = audio.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(1100, audio.currentTime);
        osc.frequency.exponentialRampToValueAtTime(750, audio.currentTime + 0.06);

        gain.gain.setValueAtTime(0.02, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.06);

        osc.connect(gain);
        gain.connect(audio.destination);

        osc.start();
        osc.stop(audio.currentTime + 0.06);
      } catch (e) {}
    }

    function playTargetLock() {
      if (!isAudioEnabled) return;
      try {
        const audio = getAudioContext();
        const osc = audio.createOscillator();
        const gain = audio.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(850, audio.currentTime);
        osc.frequency.setValueAtTime(1300, audio.currentTime + 0.04);

        gain.gain.setValueAtTime(0.03, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.06);

        osc.connect(gain);
        gain.connect(audio.destination);

        osc.start();
        osc.stop(audio.currentTime + 0.06);
      } catch (e) {}
    }

    function playEmergencyAlarm() {
      if (!isAudioEnabled) return;
      try {
        const audio = getAudioContext();
        const osc = audio.createOscillator();
        const gain = audio.createGain();

        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(750, audio.currentTime);
        osc.frequency.setValueAtTime(550, audio.currentTime + 0.08);
        osc.frequency.setValueAtTime(750, audio.currentTime + 0.16);

        gain.gain.setValueAtTime(0.04, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.28);

        osc.connect(gain);
        gain.connect(audio.destination);

        osc.start();
        osc.stop(audio.currentTime + 0.28);
      } catch (e) {}
    }

    return { playRadarBeep, playTargetLock, playEmergencyAlarm };
  })();

  // Initialize Map (Default centered on FIR Indonesia)
  function initMap() {
    map = L.map("radarMap", {
      center: [-2.5, 118.0],
      zoom: 5,
      zoomControl: true,
      attributionControl: false
    });

    setBasemap("dark");

    firLayer = L.layerGroup().addTo(map);
    trailLayer = L.layerGroup().addTo(map);
    markerLayer = L.layerGroup().addTo(map);

    map.on("click", (e) => {
      if (e.originalEvent.target.id === "radarMap" || e.originalEvent.target.classList.contains("leaflet-container")) {
        deselectTarget();
      }
    });

    // Load clean FIR boundaries without any text or labels
    loadFirIndonesia();
  }

  // Switch Basemap Layer
  function setBasemap(type) {
    const cfg = BASEMAPS[type] || BASEMAPS.dark;

    if (baseTileLayer) map.removeLayer(baseTileLayer);
    if (refTileLayer) map.removeLayer(refTileLayer);

    baseTileLayer = L.tileLayer(cfg.base, { maxZoom: cfg.maxZoom }).addTo(map);
    if (cfg.ref) {
      refTileLayer = L.tileLayer(cfg.ref, { maxZoom: cfg.maxZoom, opacity: 0.65 }).addTo(map);
    }
  }

  // Load and Render Clean FIR Indonesia Boundaries (Line only, NO text/labels, NO box)
  async function loadFirIndonesia() {
    try {
      const resp = await fetch("/data/fir_indonesia_clean.geojson");
      if (!resp.ok) return;
      const geojsonData = await resp.json();

      L.geoJSON(geojsonData, {
        style: function (feature) {
          const isUpg = (feature.properties.name || "").includes("Ujung Pandang");
          return {
            color: isUpg ? "#ef4444" : "#f97316",
            weight: 1.8,
            opacity: 0.8,
            dashArray: "5, 5",
            fill: false,
            interactive: false
          };
        }
      }).addTo(firLayer);

    } catch (e) {
      console.warn("Could not load FIR Indonesia GeoJSON:", e);
    }
  }

  // Toggle FIR Indonesia Visibility
  function toggleFirLayer() {
    isFirVisible = !isFirVisible;
    const btn = document.getElementById("btnToggleFir");
    const statusText = document.getElementById("firStatusText");

    if (isFirVisible) {
      map.addLayer(firLayer);
      btn.classList.add("fir-btn-active");
      statusText.textContent = "FIR: ON";
    } else {
      map.removeLayer(firLayer);
      btn.classList.remove("fir-btn-active");
      statusText.textContent = "FIR: OFF";
    }
  }

  // Fetch Live Flights from Backend (mode-aware)
  async function fetchFlights(isManual = false) {
    const statusText = document.getElementById("apiStatusText");
    const refreshBtn = document.getElementById("btnManualRefresh");
    
    if (isManual && refreshBtn) {
      refreshBtn.classList.add("active");
    }

    try {
      // Always fetch all-flights endpoint to get both military+commercial
      const url = isManual ? "/api/refresh-all" : "/api/all-flights";
      const method = isManual ? "POST" : "GET";
      
      const response = await fetch(url, { method });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      const allData = data.flights || [];
      const stats = data.stats || {};

      // Separate military and commercial
      allFlightsRaw = allData.filter(f => f.is_military);
      allFlightsAll = allData;

      // Set allFlights based on current mode
      updateFlightsByMode();

      const totalShown = allFlights.length;
      if (isPollingActive) {
        statusText.textContent = `LIVE (${totalShown})`;
      } else {
        statusText.textContent = `PAUSED (${totalShown})`;
      }

      updateStatsBar(stats);
      updateCountryDropdown(allFlights);
      updateCategoryCounts(stats, allFlights);

      applyFilters();

      SoundFX.playRadarBeep();

      // Emergency & Detection Alerts Banner
      const emergencyBanner = document.getElementById("emergencyBanner");
      const emergencyText = document.getElementById("emergencyBannerText");
      const emergencySub = document.getElementById("emergencyBannerSub");

      const criticalAlerts = (stats.alerts || []).filter(a => a.severity === "critical");
      const totalAlerts = (stats.alerts || []).length;

      if (criticalAlerts.length > 0) {
        const topAlert = criticalAlerts[0];
        if (emergencyBanner) {
          emergencyBanner.style.display = "flex";
          emergencyBanner.style.background = "rgba(220, 38, 38, 0.25)";
          emergencyBanner.style.borderColor = "rgba(239, 68, 68, 0.7)";
          if (emergencyText) emergencyText.textContent = `🚨 ${topAlert.callsign}: ${topAlert.label}`;
          if (emergencySub) emergencySub.textContent = criticalAlerts.length > 1 ? `+${criticalAlerts.length - 1} MORE` : "TRACK";
          emergencyBanner.onclick = () => {
            const target = allFlights.find(f => f.icao24 === topAlert.icao24);
            if (target) selectTarget(target, true);
          };
        }
        SoundFX.playEmergencyAlarm();
      } else if (totalAlerts > 0) {
        const topAlert = stats.alerts[0];
        if (emergencyBanner) {
          emergencyBanner.style.display = "flex";
          emergencyBanner.style.background = "rgba(217, 119, 6, 0.25)";
          emergencyBanner.style.borderColor = "rgba(245, 158, 11, 0.7)";
          if (emergencyText) emergencyText.textContent = `⚡ ${topAlert.callsign}: ${topAlert.label}`;
          if (emergencySub) emergencySub.textContent = "TRACK";
          emergencyBanner.onclick = () => {
            const target = allFlights.find(f => f.icao24 === topAlert.icao24);
            if (target) selectTarget(target, true);
          };
        }
      } else {
        if (emergencyBanner) emergencyBanner.style.display = "none";
      }

      secondsRemaining = pollIntervalSeconds;

    } catch (err) {
      console.error("Flight fetch error:", err);
      statusText.textContent = "RECONNECTING...";
    } finally {
      if (refreshBtn) refreshBtn.classList.remove("active");
    }
  }

  // Update allFlights array based on current flightMode
  function updateFlightsByMode() {
    if (flightMode === 'military') {
      allFlights = allFlightsRaw;
    } else if (flightMode === 'commercial') {
      allFlights = allFlightsAll.filter(f => f.is_commercial);
    } else { // 'all'
      allFlights = allFlightsAll;
    }
  }

  // Update Stats Bar UI
  function updateStatsBar(stats) {
    document.getElementById("statAirborne").textContent = stats.airborne ?? 0;
    document.getElementById("statFirIndo").textContent = stats.in_fir_indonesia ?? 0;
    document.getElementById("statNations").textContent = (stats.top_countries ? stats.top_countries.length : 0);
    
    // Military stats
    const milCats = stats.military_categories || stats.categories || {};
    document.getElementById("statMilitary").textContent = stats.total_military ?? 0;
    document.getElementById("statFighters").textContent = milCats.fighter ?? 0;
    document.getElementById("statCargo").textContent = (milCats.transport || 0) + (milCats.tanker || 0);
    document.getElementById("statHelos").textContent = milCats.helicopter ?? 0;
    document.getElementById("statRecon").textContent = milCats.recon ?? 0;

    // Commercial stats
    const comCats = stats.commercial_categories || {};
    document.getElementById("statCommercial").textContent = stats.total_commercial ?? 0;
    document.getElementById("statAirlines").textContent = comCats.airline ?? 0;
    document.getElementById("statCargoCom").textContent = comCats.cargo_commercial ?? 0;

    // Toggle visibility of stat groups based on mode
    const showMil = (flightMode === 'military' || flightMode === 'all');
    const showCom = (flightMode === 'commercial' || flightMode === 'all');
    document.querySelectorAll('.mil-stat-group').forEach(el => {
      el.style.display = showMil ? '' : 'none';
    });
    document.querySelectorAll('.com-stat-group').forEach(el => {
      el.style.display = showCom ? '' : 'none';
    });
  }

  // Update Category Counts on Pills
  function updateCategoryCounts(stats, currentFlights) {
    const total = currentFlights.length;
    const firIndoCount = currentFlights.filter(f => f.in_fir_indonesia).length;
    const detCount = currentFlights.filter(f => f.has_detection).length;
    const milCats = stats.military_categories || stats.categories || {};
    const comCats = stats.commercial_categories || {};

    // Count commercial cats from live data for "all" mode accuracy
    const liveComCats = {};
    currentFlights.filter(f => f.is_commercial).forEach(f => {
      const cat = f.category || 'airline';
      liveComCats[cat] = (liveComCats[cat] || 0) + 1;
    });

    const pillLabels = {
      // Military
      fighter: '✈ Fighter', bomber: '⬟ Bomber', transport: '▣ Transport',
      tanker: '⛽ Tanker', recon: '◉ Recon', trainer: '◈ Trainer',
      drone: '◎ UAV', military_general: '⊕ Mil Other',
      // Commercial
      heavy: '▲ Heavy', airline: '✈ Airline', cargo_commercial: '▣ Cargo',
      charter: '◆ Charter', turboprop: '⊗ Turboprop', business_jet: '◇ Bizjet',
      light_aircraft: '· Light GA', general_aviation: '⊙ Other GA',
    };

    document.querySelectorAll('.cat-pill').forEach(pill => {
      const cat = pill.dataset.category;
      if (cat === 'all') {
        pill.textContent = `All (${total})`;
      } else if (cat === 'fir_indo') {
        pill.textContent = `In FIR (${firIndoCount})`;
      } else if (cat === 'detections') {
        pill.textContent = `🚨 Alerts (${detCount})`;
      } else if (cat === 'helicopter') {
        // helicopter exists in both mil + com pills
        const isMilPill = pill.classList.contains('mil-cat-pill');
        const count = isMilPill ? (milCats.helicopter || 0) : (liveComCats.helicopter || comCats.helicopter || 0);
        const label = isMilPill ? '⊛ Helo' : '⊛ Helicopter';
        pill.textContent = `${label} (${count})`;
      } else {
        const label = pillLabels[cat] || (cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' '));
        const isMilCat = ['fighter','bomber','transport','tanker','recon','trainer','drone','military_general'].includes(cat);
        const count = isMilCat ? (milCats[cat] || 0) : (liveComCats[cat] || comCats[cat] || 0);
        pill.textContent = `${label} (${count})`;
      }
    });
  }

  // Update Country Filter Dropdown
  function updateCountryDropdown(flights) {
    const select = document.getElementById("countrySelect");
    const currentVal = select.value;
    
    const countryCounts = {};
    flights.forEach(f => {
      if (f.country) countryCounts[f.country] = (countryCounts[f.country] || 0) + 1;
    });

    const sortedCountries = Object.entries(countryCounts).sort((a, b) => b[1] - a[1]);

    select.innerHTML = `<option value="all">All Countries (${flights.length})</option>`;
    sortedCountries.forEach(([country, count]) => {
      const opt = document.createElement("option");
      opt.value = country;
      opt.textContent = `${country} (${count})`;
      if (country === currentVal) opt.selected = true;
      select.appendChild(opt);
    });
  }

  // Apply Search & Filters
  function applyFilters() {
    const q = filters.search.toLowerCase().trim();
    
    filteredFlights = allFlights.filter(f => {
      if (filters.airborneOnly && f.on_ground) return false;
      if (filters.inFirIndoOnly && !f.in_fir_indonesia) return false;

      // Mode-based filtering for category
      if (filters.category === "fir_indo") {
        if (!f.in_fir_indonesia) return false;
      } else if (filters.category === "detections") {
        if (!f.has_detection) return false;
      } else if (filters.category !== "all") {
        // For military mode, category maps directly
        // For commercial mode, category maps to flight_type
        const flightCat = f.category || f.flight_type || "";
        if (flightCat !== filters.category) return false;
      }

      if (filters.country !== "all" && f.country !== filters.country) return false;

      if (q) {
        const matchCall = (f.callsign || "").toLowerCase().includes(q);
        const matchIcao = (f.icao24 || "").toLowerCase().includes(q);
        const matchDesc = (f.desc || "").toLowerCase().includes(q);
        const matchOp = (f.operator || "").toLowerCase().includes(q);
        const matchType = (f.type_code || "").toLowerCase().includes(q);
        const matchCountry = (f.country || "").toLowerCase().includes(q);
        const matchOrigin = (f.origin || "").toLowerCase().includes(q);
        const matchDest = (f.destination || "").toLowerCase().includes(q);

        if (!matchCall && !matchIcao && !matchDesc && !matchOp && !matchType && !matchCountry && !matchOrigin && !matchDest) {
          return false;
        }
      }

      return true;
    });

    renderMarkers();
    renderFlightsList();
    renderTelemetryTable();
  }

  // Render or Update Map Markers efficiently
  function renderMarkers() {
    const currentIcaos = new Set();

    filteredFlights.forEach(flight => {
      if (flight.lat === null || flight.lon === null) return;

      currentIcaos.add(flight.icao24);
      const isSelected = flight.icao24 === selectedIcao;
      const icon = AircraftIcons.createMarkerIcon(flight, isSelected);

      if (markersMap.has(flight.icao24)) {
        const marker = markersMap.get(flight.icao24);
        marker.setLatLng([flight.lat, flight.lon]);
        marker.setIcon(icon);
      } else {
        const marker = L.marker([flight.lat, flight.lon], { icon, zIndexOffset: isSelected ? 1000 : 100 });
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          selectTarget(flight);
        });
        markerLayer.addLayer(marker);
        markersMap.set(flight.icao24, marker);
      }
    });

    markersMap.forEach((marker, icao) => {
      if (!currentIcaos.has(icao)) {
        markerLayer.removeLayer(marker);
        markersMap.delete(icao);
      }
    });
  }  // Render Sidebar Flight Cards
  function renderFlightsList() {
    const container = document.getElementById("flightsListContainer");
    container.innerHTML = "";

    if (filteredFlights.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 30px 16px; color: var(--text-dim); font-size: 0.8rem;">
          <div>No aircraft matching active criteria.</div>
        </div>
      `;
      return;
    }

    filteredFlights.forEach(flight => {
      const isCommercial = flight.is_commercial;
      const hasCritical = flight.is_emergency || flight.max_severity === "critical";
      const hasWarning = flight.max_severity === "warning";

      const card = document.createElement("div");
      card.className = `flight-card ${flight.icao24 === selectedIcao ? "active" : ""} ${hasCritical ? "has-critical" : (hasWarning ? "has-warning" : "")} ${flight.in_fir_indonesia ? "in-fir-indo" : ""} ${isCommercial ? "is-commercial" : ""}`;
      card.dataset.icao = flight.icao24;

      const altDisplay = flight.on_ground ? "ON GROUND" : (flight.alt_ft ? `${flight.alt_ft.toLocaleString()} ft` : "N/A");
      const speedDisplay = flight.speed_kts ? `${flight.speed_kts} kts` : "N/A";
      const modelDisplay = flight.desc || flight.type_code || (isCommercial ? "Commercial Aircraft" : "Tactical Airframe");

      const firBadgeHtml = flight.in_fir_indonesia 
        ? `<span style="background:rgba(249,115,22,0.2); color:#fdba74; font-size:0.62rem; padding:1px 4px; border-radius:2px; margin-left:4px;">${flight.fir_name || 'FIR INDO'}</span>` 
        : "";

      // Mini detection badges
      let miniBadgesHtml = "";
      if (flight.detections && flight.detections.length > 0) {
        miniBadgesHtml = `<div class="card-detections-row">` + 
          flight.detections.slice(0, 3).map(d => `<span class="det-badge ${d.severity}">⚡ ${d.label}</span>`).join("") +
          (flight.detections.length > 3 ? `<span class="det-badge info">+${flight.detections.length - 3}</span>` : "") +
          `</div>`;
      }

      // Category label and color for card badge
      const CAT_LABEL_MAP = {
        heavy: 'WIDEBODY', airline: 'AIRLINE', cargo_commercial: 'CARGO',
        charter: 'CHARTER', turboprop: 'TURBOPROP', business_jet: 'BIZJET',
        light_aircraft: 'LIGHT GA', helicopter: 'HELICOPTER', general_aviation: 'GEN. AVIATION',
        fighter: 'FIGHTER', bomber: 'BOMBER', transport: 'MIL TRANSPORT',
        tanker: 'TANKER', recon: 'ISR/RECON', trainer: 'TRAINER',
        drone: 'UAV/DRONE', military_general: 'MILITARY'
      };
      const CAT_COLOR_MAP = {
        heavy: '#38bdf8', airline: '#60a5fa', cargo_commercial: '#fb923c',
        charter: '#a78bfa', turboprop: '#4ade80', business_jet: '#f0abfc',
        light_aircraft: '#86efac', helicopter: '#fcd34d', general_aviation: '#6ee7b7',
        fighter: '#f87171', bomber: '#c084fc', transport: '#a3e635',
        tanker: '#fb923c', recon: '#67e8f9', trainer: '#fde68a',
        drone: '#e879f9', military_general: '#94a3b8'
      };
      const typeBadgeColor = CAT_COLOR_MAP[flight.category] || (isCommercial ? '#60a5fa' : 'var(--accent-blue)');
      const typeLabel = CAT_LABEL_MAP[flight.category] || (flight.category || 'UNKNOWN').replace(/_/g, ' ').toUpperCase();
      const typeCodePart = flight.type_code ? ` · ${flight.type_code}` : '';


      card.innerHTML = `
        <div class="flight-card-top">
          <div class="card-callsign">
            <span>${flight.callsign}</span>
            <span style="font-size: 0.65rem; color: ${isCommercial ? '#60a5fa' : 'var(--accent-cyan)'}; font-family: var(--font-mono);">#${flight.icao24}</span>
            ${firBadgeHtml}
          </div>
          <div class="card-country-flag">${flight.country || "Unknown"}</div>
        </div>
        <div class="card-model-row">
          <span>${modelDisplay}</span>
          <span style="text-transform: uppercase; font-size: 0.62rem; color: ${typeBadgeColor};">${typeLabel}${typeCodePart}</span>
        </div>
        ${miniBadgesHtml}
        <div class="card-route-row">
          <span>${flight.origin || (isCommercial ? 'Origin' : 'Tactical Origin')}</span>
          <span>➔</span>
          <span>${flight.destination || (isCommercial ? 'Destination' : 'In Flight')}</span>
        </div>
        <div class="card-telemetry-row">
          <div class="telemetry-item">ALT: <span>${altDisplay}</span></div>
          <div class="telemetry-item">SPD: <span>${speedDisplay}</span></div>
          <div class="telemetry-item">SQK: <span>${flight.squawk || "---"}</span></div>
        </div>
      `;

      card.addEventListener("click", () => {
        selectTarget(flight, true);
      });

      container.appendChild(card);
    });
  }

  // Select Target Aircraft & Display HUD Card
  async function selectTarget(flight, shouldFly = true) {
    selectedIcao = flight.icao24;
    SoundFX.playTargetLock();

    const hud = document.getElementById("targetHudSection");
    hud.style.display = "block";

    document.getElementById("targetCallsign").textContent = flight.callsign;
    document.getElementById("targetIcao").textContent = `#${flight.icao24}`;
    document.getElementById("targetDesc").textContent = flight.desc || flight.type_code || "Military Aircraft";
    document.getElementById("targetOperator").textContent = flight.operator || `${flight.country} Armed Forces`;

    const firBadge = document.getElementById("targetFirBadge");
    if (flight.in_fir_indonesia) {
      firBadge.style.display = "flex";
      document.getElementById("targetFirName").textContent = (flight.fir_name || "FIR INDONESIA").toUpperCase();
    } else {
      firBadge.style.display = "none";
    }

    // Render Active Detections & Flight Anomalies in Target HUD
    const detBox = document.getElementById("targetDetectionsBox");
    const detList = document.getElementById("targetDetectionsList");
    if (detBox && detList) {
      if (flight.detections && flight.detections.length > 0) {
        detBox.style.display = "block";
        detList.innerHTML = flight.detections.map(d => `
          <div class="hud-detection-item ${d.severity}">
            <div class="hud-det-top">
              <span class="hud-det-label ${d.severity}">${d.label}</span>
              <span style="font-size:0.58rem; text-transform:uppercase; color:${d.severity === 'critical' ? '#ef4444' : (d.severity === 'warning' ? '#f59e0b' : '#38bdf8')}; font-weight:700;">${d.severity}</span>
            </div>
            <div class="hud-det-desc">${d.desc}</div>
          </div>
        `).join("");
      } else {
        detBox.style.display = "none";
      }
    }

    document.getElementById("targetOrigin").textContent = flight.origin || "Resolving origin departure...";
    document.getElementById("targetDest").textContent = flight.destination || "Resolving destination...";

    document.getElementById("targetAlt").innerHTML = flight.on_ground 
      ? `GROUND <span class="gauge-unit">SFC</span>` 
      : `${(flight.alt_ft ?? 0).toLocaleString()} <span class="gauge-unit">FT</span>`;

    document.getElementById("targetSpeed").innerHTML = `${flight.speed_kts ?? 0} <span class="gauge-unit">KTS</span>`;
    document.getElementById("targetHeading").innerHTML = `${Math.round(flight.heading ?? 0)}° <span class="gauge-unit">TRUE</span>`;
    
    const vr = flight.vert_rate_fpm ?? 0;
    const vrPrefix = vr > 0 ? "+" : "";
    document.getElementById("targetVertRate").innerHTML = `${vrPrefix}${vr} <span class="gauge-unit">FPM</span>`;
    
    document.getElementById("targetSquawk").textContent = flight.squawk || "NONE";
    document.getElementById("targetCountry").textContent = flight.country || "Unknown";

    if (shouldFly && flight.lat !== null && flight.lon !== null) {
      map.flyTo([flight.lat, flight.lon], Math.max(map.getZoom(), 7), {
        duration: 1.0
      });
    }

    renderMarkers();
    document.querySelectorAll(".flight-card").forEach(c => {
      c.classList.toggle("active", c.dataset.icao === selectedIcao);
    });

    loadFlightTrail(flight.icao24);
    fetchFlightRoute(flight.icao24);
    fetchAircraftPhoto(flight.icao24, flight.reg);
  }

  // Fetch and display actual aircraft photo from Planespotters
  async function fetchAircraftPhoto(icao, reg = "") {
    const photoImg = document.getElementById("targetPhotoImg");
    const photoPlaceholder = document.getElementById("targetPhotoPlaceholder");
    const photoStatus = document.getElementById("targetPhotoStatus");
    const photoFooter = document.getElementById("targetPhotoFooter");
    const photographer = document.getElementById("targetPhotographer");
    const photoLink = document.getElementById("targetPhotoLink");

    if (!photoImg || !photoPlaceholder) return;

    // Reset to searching state
    photoImg.style.display = "none";
    photoImg.src = "";
    photoPlaceholder.style.display = "flex";
    if (photoStatus) photoStatus.textContent = "Searching aircraft photo...";
    if (photoFooter) photoFooter.style.display = "none";

    try {
      const regParam = reg ? `?reg=${encodeURIComponent(reg)}` : "";
      const resp = await fetch(`/api/aircraft-photo/${icao}${regParam}`);
      if (!resp.ok) {
        if (photoStatus) photoStatus.textContent = "Classified / Wireframe Profile";
        return;
      }
      const data = await resp.json();
      if (data.has_photo && data.large) {
        photoImg.onload = () => {
          photoPlaceholder.style.display = "none";
          photoImg.style.display = "block";
          if (photoFooter) photoFooter.style.display = "flex";
          if (photographer) photographer.textContent = `Photo © ${data.photographer || 'Planespotters'}`;
          if (photoLink) photoLink.href = data.link || data.large;
        };
        photoImg.onerror = () => {
          photoPlaceholder.style.display = "flex";
          if (photoStatus) photoStatus.textContent = "Classified / Wireframe Profile";
          photoImg.style.display = "none";
        };
        photoImg.src = data.large;
      } else {
        photoPlaceholder.style.display = "flex";
        if (photoStatus) photoStatus.textContent = "Classified Sortie / No Photo on Record";
      }
    } catch (err) {
      photoPlaceholder.style.display = "flex";
      if (photoStatus) photoStatus.textContent = "Photo service unavailable";
    }
  }

  // Fetch Origin and Destination Route
  async function fetchFlightRoute(icao) {
    try {
      const resp = await fetch(`/api/flight-route/${icao}`);
      if (!resp.ok) return;
      const data = await resp.json();

      if (data.origin_display) {
        document.getElementById("targetOrigin").textContent = data.origin_display;
      }
      if (data.dest_display) {
        document.getElementById("targetDest").textContent = data.dest_display;
      }

      const flight = allFlights.find(f => f.icao24 === icao);
      if (flight) {
        flight.origin = data.origin_display;
        flight.destination = data.dest_display;
        renderFlightsList();
      }
    } catch (e) {
      console.warn("Route resolution error:", e);
    }
  }

  // Load and render flight trail breadcrumbs
  async function loadFlightTrail(icao) {
    trailLayer.clearLayers();
    try {
      const resp = await fetch(`/api/track/${icao}`);
      if (!resp.ok) return;
      const data = await resp.json();
      const trail = data.trail || [];

      if (trail.length > 1) {
        const latLngs = trail.map(pt => [pt[0], pt[1]]);
        
        const polyline = L.polyline(latLngs, {
          color: "#38bdf8",
          weight: 2,
          opacity: 0.9,
          dashArray: "4, 6"
        });
        trailLayer.addLayer(polyline);

        trail.forEach(pt => {
          const circle = L.circleMarker([pt[0], pt[1]], {
            radius: 2.5,
            fillColor: "#38bdf8",
            fillOpacity: 0.9,
            color: "#0f1319",
            weight: 1
          });
          trailLayer.addLayer(circle);
        });
      }
    } catch (e) {
      console.error("Trail load error:", e);
    }
  }

  // Deselect Target Aircraft
  function deselectTarget() {
    selectedIcao = null;
    document.getElementById("targetHudSection").style.display = "none";
    trailLayer.clearLayers();
    renderMarkers();
    document.querySelectorAll(".flight-card").forEach(c => c.classList.remove("active"));
  }

  // Populate Telemetry Drawer Table
  function renderTelemetryTable() {
    const tbody = document.getElementById("telemetryTableBody");
    tbody.innerHTML = "";

    filteredFlights.forEach(f => {
      const tr = document.createElement("tr");
      const firTag = f.in_fir_indonesia ? `<span style="color:#fdba74; font-weight:600;">${f.fir_name || 'FIR INDO'}</span>` : "International";

      tr.innerHTML = `
        <td style="font-weight:700; color:var(--accent-cyan); font-family:var(--font-mono);">${f.callsign}</td>
        <td style="font-family:var(--font-mono);">${f.icao24}</td>
        <td>${f.type_code || "---"}</td>
        <td>${f.desc || "---"}</td>
        <td style="color:#38bdf8;">${f.origin || 'Tactical'}</td>
        <td style="color:#c084fc;">${f.destination || 'En Route'}</td>
        <td>${firTag}</td>
        <td>${f.operator || "---"}</td>
        <td>${f.country}</td>
        <td>${f.on_ground ? "GND" : (f.alt_ft ? f.alt_ft.toLocaleString() + " ft" : "N/A")}</td>
        <td>${f.speed_kts ? f.speed_kts + " kts" : "N/A"}</td>
        <td>${f.heading !== null ? Math.round(f.heading) + "°" : "N/A"}</td>
        <td>${f.squawk || "---"}</td>
        <td>${f.on_ground ? "On Ground" : "Airborne"}</td>
      `;

      tr.addEventListener("click", () => {
        document.getElementById("telemetryDrawer").classList.remove("open");
        selectTarget(f, true);
      });

      tbody.appendChild(tr);
    });
  }

  // Export to CSV
  function exportCsv() {
    const headers = ["Callsign", "ICAO24", "Type", "Description", "Asal_Origin", "Tujuan_Destination", "In_FIR_Indo", "FIR_Name", "Operator", "Country", "Latitude", "Longitude", "Altitude_FT", "Speed_KTS", "Heading", "Squawk", "OnGround"];
    const rows = filteredFlights.map(f => [
      `"${f.callsign}"`,
      `"${f.icao24}"`,
      `"${f.type_code || ""}"`,
      `"${(f.desc || "").replace(/"/g, '""')}"`,
      `"${(f.origin || "").replace(/"/g, '""')}"`,
      `"${(f.destination || "").replace(/"/g, '""')}"`,
      f.in_fir_indonesia ? "1" : "0",
      `"${f.fir_name || ""}"`,
      `"${(f.operator || "").replace(/"/g, '""')}"`,
      `"${f.country || ""}"`,
      f.lat ?? "",
      f.lon ?? "",
      f.alt_ft ?? "",
      f.speed_kts ?? "",
      f.heading ?? "",
      `"${f.squawk || ""}"`,
      f.on_ground ? "1" : "0"
    ]);

    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `SkyGuard_Military_Flights_${new Date().toISOString().replace(/[:.]/g, "-")}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  // Export to JSON
  function exportJson() {
    const blob = new Blob([JSON.stringify(filteredFlights, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `SkyGuard_Military_Flights_${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  // Setup Event Listeners
  function setupEvents() {
    const pollingToggle = document.getElementById("pollingToggle");
    const pollingStatusText = document.getElementById("pollingStatusText");
    const livePulseDot = document.getElementById("livePulseDot");
    const countdownVal = document.getElementById("countdownVal");
    const apiStatusText = document.getElementById("apiStatusText");

    pollingToggle.addEventListener("change", (e) => {
      isPollingActive = e.target.checked;
      if (isPollingActive) {
        pollingStatusText.textContent = "ON";
        pollingStatusText.className = "switch-status-text on";
        livePulseDot.classList.remove("paused");
        apiStatusText.textContent = `LIVE (${allFlights.length})`;
        secondsRemaining = pollIntervalSeconds;
        countdownVal.textContent = `${secondsRemaining}s`;
        fetchFlights();
      } else {
        pollingStatusText.textContent = "OFF";
        pollingStatusText.className = "switch-status-text off";
        livePulseDot.classList.add("paused");
        apiStatusText.textContent = "PAUSED (OFF)";
        countdownVal.textContent = "PAUSED";
      }
    });

    document.querySelectorAll(".basemap-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".basemap-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        setBasemap(btn.dataset.basemap);
      });
    });

    document.getElementById("btnToggleFir").addEventListener("click", toggleFirLayer);

    const searchInput = document.getElementById("searchInput");
    searchInput.addEventListener("input", (e) => {
      filters.search = e.target.value;
      applyFilters();
    });

    document.querySelectorAll(".cat-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        filters.category = pill.dataset.category;
        applyFilters();
      });
    });

    // Flight Mode Toggle
    document.querySelectorAll(".mode-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        flightMode = btn.dataset.mode;
        switchFlightMode(flightMode);
      });
    });

    document.getElementById("statFirIndoItem").addEventListener("click", () => {
      const firPill = document.querySelector(".cat-pill[data-category='fir_indo']");
      if (firPill) {
        document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
        firPill.classList.add("active");
        filters.category = "fir_indo";
        applyFilters();

        map.flyTo([-2.5, 118.0], 5, { duration: 1.0 });
      }
    });

    const countrySelect = document.getElementById("countrySelect");
    countrySelect.addEventListener("change", (e) => {
      filters.country = e.target.value;
      applyFilters();
    });

    const airborneCheck = document.getElementById("checkAirborneOnly");
    airborneCheck.addEventListener("change", (e) => {
      filters.airborneOnly = e.target.checked;
      applyFilters();
    });

    document.getElementById("btnManualRefresh").addEventListener("click", () => {
      fetchFlights(true);
    });

    const audioBtn = document.getElementById("btnAudioToggle");
    audioBtn.addEventListener("click", () => {
      isAudioEnabled = !isAudioEnabled;
      document.getElementById("audioStatusText").textContent = isAudioEnabled ? "Audio" : "Muted";
      audioBtn.classList.toggle("active", isAudioEnabled);
    });

    document.querySelectorAll(".nav-pill-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-pill-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const reg = REGIONS[btn.dataset.region];
        if (reg) {
          map.flyTo([reg.lat, reg.lon], reg.zoom, { duration: 1.2 });
        }
      });
    });

    document.getElementById("btnCloseTarget").addEventListener("click", deselectTarget);

    document.getElementById("btnFocusTarget").addEventListener("click", () => {
      if (!selectedIcao) return;
      const f = allFlights.find(x => x.icao24 === selectedIcao);
      if (f && f.lat && f.lon) {
        map.flyTo([f.lat, f.lon], 9, { duration: 1 });
      }
    });

    document.getElementById("btnCopyTelemetry").addEventListener("click", () => {
      if (!selectedIcao) return;
      const f = allFlights.find(x => x.icao24 === selectedIcao);
      if (!f) return;
      const telemetryText = `[MILITARY TELEMETRY]\nCallsign: ${f.callsign}\nICAO: ${f.icao24}\nModel: ${f.desc}\nAsal: ${f.origin}\nTujuan: ${f.destination}\nAirspace: ${f.fir_name || 'International'}\nOperator: ${f.operator}\nCountry: ${f.country}\nAlt: ${f.alt_ft} ft\nSpeed: ${f.speed_kts} kts\nHeading: ${f.heading}°\nSquawk: ${f.squawk}\nCoordinates: ${f.lat}, ${f.lon}`;
      navigator.clipboard.writeText(telemetryText).then(() => {
        const btn = document.getElementById("btnCopyTelemetry");
        const prev = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = prev; }, 1800);
      });
    });

    const drawer = document.getElementById("telemetryDrawer");
    document.getElementById("btnOpenTable").addEventListener("click", () => {
      drawer.classList.add("open");
    });
    document.getElementById("btnCloseDrawer").addEventListener("click", () => {
      drawer.classList.remove("open");
    });
    document.getElementById("btnExportCsv").addEventListener("click", exportCsv);
    document.getElementById("btnExportJson").addEventListener("click", exportJson);

    countdownTimer = setInterval(() => {
      if (!isPollingActive) return;

      secondsRemaining--;
      if (secondsRemaining <= 0) {
        secondsRemaining = pollIntervalSeconds;
        fetchFlights();
      }
      const cdEl = document.getElementById("countdownVal");
      if (cdEl) cdEl.textContent = `${secondsRemaining}s`;
    }, 1000);
  }

  // Switch flight display mode and update UI accordingly
  function switchFlightMode(mode) {
    flightMode = mode;

    // Update header tag
    const modeTag = document.getElementById("headerModeTag");
    const drawerTitle = document.getElementById("drawerTitle");
    if (mode === 'military') {
      if (modeTag) { modeTag.textContent = 'MILITARY ADS-B'; modeTag.style.background = '#b91c1c'; }
      if (drawerTitle) drawerTitle.textContent = 'MILITARY FLIGHT TELEMETRY DATA MATRIX';
    } else if (mode === 'commercial') {
      if (modeTag) { modeTag.textContent = 'COMMERCIAL ADS-B'; modeTag.style.background = '#1d4ed8'; }
      if (drawerTitle) drawerTitle.textContent = 'COMMERCIAL FLIGHT TELEMETRY DATA MATRIX';
    } else {
      if (modeTag) { modeTag.textContent = 'ALL FLIGHTS ADS-B'; modeTag.style.background = '#065f46'; }
      if (drawerTitle) drawerTitle.textContent = 'ALL FLIGHTS TELEMETRY DATA MATRIX';
    }

    // Show/hide category pills based on mode
    document.querySelectorAll('.mil-cat-pill').forEach(p => {
      p.style.display = (mode === 'military' || mode === 'all') ? '' : 'none';
    });
    document.querySelectorAll('.com-cat-pill').forEach(p => {
      p.style.display = (mode === 'commercial' || mode === 'all') ? '' : 'none';
    });

    // Reset category filter to "all" on mode switch
    filters.category = 'all';
    document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
    const allPill = document.querySelector('.cat-pill[data-category="all"]');
    if (allPill) allPill.classList.add('active');

    // Update flights array and re-render
    updateFlightsByMode();
    updateCountryDropdown(allFlights);
    applyFilters();
  }

  // App Initialization
  document.addEventListener("DOMContentLoaded", () => {
    initMap();
    setupEvents();
    fetchFlights();
  });
})();
