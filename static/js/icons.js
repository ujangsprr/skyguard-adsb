/**
 * SkyGuard Sentinel — Aircraft SVG Silhouette Generator
 * Military + Commercial Aviation Markers (Directional, ADS-B Exchange Style)
 * Distinct icons per category: heavy, airline, cargo, turboprop, bizjet, light, helicopter + all military
 */

const AircraftIcons = (() => {
  // SVG paths per category — top-down silhouettes, nose pointing up (north = 0 deg)
  const SVG_PATHS = {
    // Military
    fighter:          "M12 2 L13.5 7 L21 11 L21 13 L13.5 12 L14 19 L17 21 L17 22 L12 21 L7 22 L7 21 L10 19 L10.5 12 L3 13 L3 11 L10.5 7 Z",
    bomber:           "M12 2 L14 6 L23 10 L23 13 L15 13 L14 20 L18 22 L18 23 L12 22 L6 23 L6 22 L10 20 L9 13 L1 13 L1 10 L10 6 Z",
    transport:        "M12 1 L14 5 L22 9 L22 14 L14 13 L14 21 L18 23 L18 24 L12 23 L6 24 L6 23 L10 21 L10 13 L2 14 L2 9 L10 5 Z",
    tanker:           "M12 1 L14 5 L23 10 L23 13 L14 13 L14 21 L17 23 L17 24 L12 23 L7 24 L7 23 L10 21 L10 13 L1 13 L1 10 L10 5 Z",
    recon:            "M12 3 L13 7 L23 10 L23 12 L13 12 L13 16 A3 3 0 0 0 13 20 L16 22 L16 23 L12 22 L8 23 L8 22 L11 20 A3 3 0 0 0 11 16 L11 12 L1 12 L1 10 L11 7 Z",
    trainer:          "M12 3 L13.5 7 L19 11 L19 13 L13 13 L13 18 L15 20 L15 21 L12 20 L9 21 L9 20 L11 18 L11 13 L5 13 L5 11 L10.5 7 Z",
    drone:            "M12 4 L13 8 L23 8 L23 10 L13 11 L13 19 L16 21 L16 22 L12 21 L8 22 L8 21 L11 19 L11 11 L1 10 L1 8 L11 8 Z",
    military_general: "M12 2 L14 6 L21 11 L21 13 L14 13 L14 19 L17 21 L17 22 L12 21 L7 22 L7 21 L10 19 L10 13 L3 13 L3 11 L10 6 Z",
    // Commercial / Civilian
    heavy:            "M12 1 L14 4 L23 8 L23 12 L14.5 11 L14.5 20 L18 22 L18 23 L12 22 L6 23 L6 22 L9.5 20 L9.5 11 L1 12 L1 8 L10 4 Z",
    airline:          "M12 2 L13.5 5 L20 9 L20 13 L13.5 12 L13.5 20 L16 22 L16 23 L12 22 L8 23 L8 22 L10.5 20 L10.5 12 L4 13 L4 9 L10.5 5 Z",
    cargo_commercial: "M12 1 L14 5 L22 10 L22 14 L14 13 L14 21 L17 23 L17 24 L12 23 L7 24 L7 23 L10 21 L10 13 L2 14 L2 10 L10 5 Z",
    charter:          "M12 2 L13.5 6 L20 10 L20 13 L13.5 13 L13.5 20 L16 22 L16 23 L12 22 L8 23 L8 22 L10.5 20 L10.5 13 L4 13 L4 10 L10.5 6 Z",
    turboprop:        "M12 3 C13 3 13.5 4 13.5 5 L13.5 7 L19 10 L19 12 L13.5 12 L13.5 19 L15 20 L15 21 L12 20.5 L9 21 L9 20 L10.5 19 L10.5 12 L5 12 L5 10 L10.5 7 L10.5 5 C10.5 4 11 3 12 3 Z",
    business_jet:     "M12 2 L13 6 L18 10 L18 13 L13 12.5 L13 19 L15 21 L15 22 L12 21.5 L9 22 L9 21 L11 19 L11 12.5 L6 13 L6 10 L11 6 Z",
    light_aircraft:   "M12 5 L13 8 L17 10 L17 12 L13 12 L13 17 L14 18 L14 19 L12 18.5 L10 19 L10 18 L11 17 L11 12 L7 12 L7 10 L11 8 Z",
    helicopter:       "M12 5 L22 5 L22 6 L13 6 L13 8 C15 8 16 9 16 11 L16 13 L13 13 L13 18 L18 19 L18 20 L13 19 L13 22 L11 22 L11 19 L6 20 L6 19 L11 18 L11 13 L8 13 L8 11 C8 9 9 8 11 8 L11 6 L2 6 L2 5 L12 5 Z",
    general_aviation: "M12 4 L13 8 L18 11 L18 13 L13 13 L13 19 L15 21 L15 22 L12 21 L9 22 L9 21 L11 19 L11 13 L6 13 L6 11 L11 8 Z"
  };

  // Category color scheme — each category has a distinct, curated color
  const CATEGORY_COLORS = {
    // Military
    fighter:          "#f87171",  // hot red
    bomber:           "#c084fc",  // vivid violet
    tanker:           "#fb923c",  // amber-orange
    transport:        "#a3e635",  // lime green
    recon:            "#67e8f9",  // cyan
    trainer:          "#fde68a",  // pale yellow
    drone:            "#e879f9",  // fuchsia
    military_general: "#94a3b8",  // slate
    // Commercial
    heavy:            "#38bdf8",  // sky blue — flagship widebodies
    airline:          "#60a5fa",  // blue — standard narrowbody
    cargo_commercial: "#fb923c",  // orange — freighter
    charter:          "#a78bfa",  // violet — charter
    turboprop:        "#4ade80",  // green — regional prop
    business_jet:     "#f0abfc",  // pink/magenta — VIP biz
    light_aircraft:   "#86efac",  // pale green — small GA
    helicopter:       "#fcd34d",  // gold — rotorcraft
    general_aviation: "#6ee7b7",  // teal — other GA
  };

  /**
   * Get altitude color (altitude-based gradient — used for unknown military)
   */
  function getAltitudeColor(altFt, onGround) {
    if (onGround) return "#9ca3af";
    if (altFt === null || altFt === undefined) return "#38bdf8";
    if (altFt < 5000)  return "#22c55e";
    if (altFt < 15000) return "#06b6d4";
    if (altFt < 25000) return "#3b82f6";
    if (altFt < 35000) return "#f59e0b";
    return "#ec4899";
  }

  /**
   * Create Leaflet DivIcon with heading rotation
   */
  function createMarkerIcon(flight, isSelected = false) {
    const heading = (flight.heading !== null && flight.heading !== undefined) ? flight.heading : 0;
    const cat = flight.category || (flight.is_military ? "military_general" : "airline");
    const path = SVG_PATHS[cat] || (flight.is_military ? SVG_PATHS.military_general : SVG_PATHS.airline);

    const hasCritical = flight.is_emergency || flight.max_severity === "critical";
    const hasWarning  = flight.max_severity === "warning";

    let color;
    if (hasCritical) {
      color = "#ef4444";
    } else if (hasWarning) {
      color = "#f59e0b";
    } else if (isSelected) {
      color = "#38bdf8";
    } else {
      color = CATEGORY_COLORS[cat] || getAltitudeColor(flight.alt_ft, flight.on_ground);
    }

    // Icon size varies by category importance
    const sizeMap = {
      heavy: 28, airline: 22, cargo_commercial: 24, charter: 21,
      turboprop: 19, business_jet: 20, light_aircraft: 16, helicopter: 20,
      general_aviation: 17,
      fighter: 22, bomber: 24, transport: 24, tanker: 24,
      recon: 22, trainer: 19, drone: 21, military_general: 21
    };
    const size = isSelected ? 34 : (sizeMap[cat] || 22);

    // Ring overlay for alerts / selection
    let ringSvg = "";
    if (hasCritical) {
      ringSvg = `<circle cx="12" cy="12" r="11" fill="none" stroke="#ef4444" stroke-width="2" class="marker-emergency-pulse"/>`;
    } else if (hasWarning) {
      ringSvg = `<circle cx="12" cy="12" r="11" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="2, 2"/>`;
    } else if (isSelected) {
      ringSvg = `<circle cx="12" cy="12" r="11" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="3, 3"/>`;
    }

    // Glow filter
    let glowFilter = `filter: drop-shadow(0 1px 3px rgba(0,0,0,0.85));`;
    if (hasCritical) {
      glowFilter = `filter: drop-shadow(0 0 6px rgba(239,68,68,0.9));`;
    } else if (hasWarning) {
      glowFilter = `filter: drop-shadow(0 0 5px rgba(245,158,11,0.7));`;
    } else if (isSelected) {
      glowFilter = `filter: drop-shadow(0 0 8px ${color}88);`;
    } else if (!flight.is_military) {
      glowFilter = `filter: drop-shadow(0 1px 2px ${color}55);`;
    }

    const strokeColor  = hasCritical ? "#7f1d1d" : (flight.is_military ? "#0b0f15" : "#1e293b");
    const strokeWidth  = hasCritical ? "1.0" : "0.5";
    const opacity      = (isSelected || hasCritical) ? 1 : (flight.is_military ? 0.95 : 0.88);

    // Detection badge
    let detectionBadgeHtml = "";
    if (hasCritical) {
      const label = flight.emergency_type || "EMERGENCY";
      detectionBadgeHtml = `<div class="marker-alert-tag critical">⚠️ ${label}</div>`;
    } else if (hasWarning && flight.detections && flight.detections.length > 0) {
      const warnDet = flight.detections.find(d => d.severity === "warning") || flight.detections[0];
      detectionBadgeHtml = `<div class="marker-alert-tag warning">⚡ ${warnDet.label}</div>`;
    } else if (flight.spi) {
      detectionBadgeHtml = `<div class="marker-alert-tag ident">IDENT</div>`;
    }

    const markerClass = flight.is_military
      ? `military-marker mil-${cat.replace(/_/g, '-')}`
      : `commercial-marker cat-${cat.replace(/_/g, '-')}`;

    const svgHtml = `
      <div class="radar-marker-container ${markerClass} ${hasCritical ? 'is-critical-marker' : ''} ${isSelected ? 'is-selected' : ''}" style="width:${size}px; height:${size}px;">
        <svg viewBox="0 0 24 24" class="radar-plane-svg" style="transform:rotate(${heading}deg); width:100%; height:100%; ${glowFilter}">
          ${ringSvg}
          <path d="${path}" fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${opacity}"/>
        </svg>
        ${flight.callsign && flight.callsign !== "NO CALL"
          ? `<div class="marker-callsign-badge ${flight.is_military ? '' : 'commercial-badge'} ${hasCritical ? 'emergency-badge' : ''}">${flight.callsign}</div>`
          : ""}
        ${detectionBadgeHtml}
      </div>
    `;

    return L.divIcon({
      html: svgHtml,
      className: "custom-radar-icon",
      iconSize:    [size, size],
      iconAnchor:  [size / 2, size / 2],
      popupAnchor: [0, -size / 2]
    });
  }

  return { SVG_PATHS, CATEGORY_COLORS, getAltitudeColor, createMarkerIcon };
})();
