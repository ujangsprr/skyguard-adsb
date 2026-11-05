/**
 * SkyGuard Sentinel — Aircraft SVG Silhouette Generator
 * Military + Commercial Aviation Markers (Directional, ADS-B Exchange Style)
 * Distinct icons per category: heavy, airline, cargo, turboprop, bizjet, light, helicopter + all military
 */

const AircraftIcons = (() => {
  // SVG paths per category — high-precision aerodynamic silhouettes (nose up = 0 deg)
  const SVG_PATHS = {
    // Military
    fighter:          "M 12 1.5 L 12.8 4.2 L 13.6 7.8 L 14.2 9.0 L 19.8 13.5 L 19.8 14.8 L 14.2 14.2 L 14.2 18.2 L 16.8 20.8 L 16.8 22.2 L 14.2 21.4 L 13.2 22.5 L 12.0 21.8 L 10.8 22.5 L 9.8 21.4 L 7.2 22.2 L 7.2 20.8 L 9.8 18.2 L 9.8 14.2 L 4.2 14.8 L 4.2 13.5 L 9.8 9.0 L 10.4 7.8 L 11.2 4.2 Z",
    bomber:           "M 12 1.4 C 12.7 1.4 13.6 2.3 13.6 4.2 L 13.6 8.8 L 16.2 10.8 L 16.2 9.9 L 17.5 9.9 L 17.5 11.8 L 19.4 13.2 L 19.4 12.4 L 20.6 12.4 L 20.6 14.1 L 22.5 15.4 L 22.5 16.8 L 13.6 13.4 L 13.2 19.8 L 16.0 21.4 L 16.0 22.5 L 12.0 21.8 L 8.0 22.5 L 8.0 21.4 L 10.8 19.8 L 10.4 13.4 L 1.5 16.8 L 1.5 15.4 L 3.4 14.1 L 3.4 12.4 L 4.6 12.4 L 4.6 13.2 L 6.5 11.8 L 6.5 9.9 L 7.8 9.9 L 7.8 10.8 L 10.4 8.8 L 10.4 4.2 C 10.4 2.3 11.3 1.4 12 1.4 Z",
    transport:        "M 12 1.6 C 12.8 1.6 13.7 2.6 13.7 4.5 L 13.7 9.2 L 16.5 11.3 L 16.5 10.4 L 17.8 10.4 L 17.8 12.3 L 21.5 14.8 L 21.5 16.5 L 13.7 13.5 L 13.2 19.9 L 15.8 21.4 L 15.8 22.5 L 12.0 21.7 L 8.2 22.5 L 8.2 21.4 L 10.8 19.9 L 10.3 13.5 L 2.5 16.5 L 2.5 14.8 L 6.2 12.3 L 6.2 10.4 L 7.5 10.4 L 7.5 11.3 L 10.3 9.2 L 10.3 4.5 C 10.3 2.6 11.2 1.6 12 1.6 Z",
    tanker:           "M 12 1.6 C 12.8 1.6 13.7 2.6 13.7 4.5 L 13.7 9.2 L 16.5 11.3 L 16.5 10.4 L 17.8 10.4 L 17.8 12.3 L 21.5 14.8 L 21.5 16.5 L 13.7 13.5 L 13.2 19.9 L 15.8 21.4 L 15.8 22.5 L 12.0 21.7 L 8.2 22.5 L 8.2 21.4 L 10.8 19.9 L 10.3 13.5 L 2.5 16.5 L 2.5 14.8 L 6.2 12.3 L 6.2 10.4 L 7.5 10.4 L 7.5 11.3 L 10.3 9.2 L 10.3 4.5 C 10.3 2.6 11.2 1.6 12 1.6 Z",
    recon:            "M 12 1.6 C 12.6 1.6 13.3 2.5 13.3 4.2 L 13.3 9.4 L 22.2 12.6 L 22.2 14.0 L 13.3 13.0 L 13.1 19.8 L 15.6 21.4 L 15.6 22.4 L 12.0 21.7 L 8.4 22.4 L 8.4 21.4 L 10.9 19.8 L 10.7 13.0 L 1.8 14.0 L 1.8 12.6 L 10.7 9.4 L 10.7 4.2 C 10.7 2.5 11.4 1.6 12 1.6 Z",
    trainer:          "M 12 1.8 C 12.5 1.8 13.2 2.6 13.2 4.0 L 13.2 9.0 L 18.6 13.2 L 18.6 14.5 L 13.2 13.0 L 13.0 19.5 L 15.2 21.0 L 15.2 22.0 L 12.0 21.5 L 8.8 22.0 L 8.8 21.0 L 11.0 19.5 L 10.8 13.0 L 5.4 14.5 L 5.4 13.2 L 10.8 9.0 L 10.8 4.0 C 10.8 2.6 11.5 1.8 12 1.8 Z",
    drone:            "M 12 2.2 C 12.5 2.2 13.0 2.8 13.0 4.2 L 13.0 9.5 L 22.5 11.4 L 22.5 12.6 L 13.0 12.6 L 12.8 19.2 L 15.4 22.2 L 14.2 22.8 L 12.0 20.2 L 9.8 22.8 L 8.6 22.2 L 11.2 19.2 L 11.0 12.6 L 1.5 12.6 L 1.5 11.4 L 11.0 9.5 L 11.0 4.2 C 11.0 2.8 11.5 2.2 12 2.2 Z",
    military_general: "M 12 1.8 C 12.6 1.8 13.4 2.6 13.4 4.2 L 13.4 9.1 L 16.2 11.1 L 16.2 10.3 L 17.5 10.3 L 17.5 12.1 L 20.8 14.5 L 20.8 16.2 L 13.4 13.2 L 13.1 19.8 L 15.3 21.2 L 15.3 22.3 L 12.0 21.6 L 8.7 22.3 L 8.7 21.2 L 10.9 19.8 L 10.6 13.2 L 3.2 16.2 L 3.2 14.5 L 6.5 12.1 L 6.5 10.3 L 7.8 10.3 L 7.8 11.1 L 10.6 9.1 L 10.6 4.2 C 10.6 2.6 11.4 1.8 12 1.8 Z",
    // Commercial / Civilian (Aerodynamic airliner with wing engine nacelles)
    heavy:            "M 12 1.4 C 12.7 1.4 13.6 2.3 13.6 4.2 L 13.6 8.8 L 16.2 10.8 L 16.2 9.9 L 17.5 9.9 L 17.5 11.8 L 19.4 13.2 L 19.4 12.4 L 20.6 12.4 L 20.6 14.1 L 22.5 15.4 L 22.5 16.8 L 13.6 13.4 L 13.2 19.8 L 16.0 21.4 L 16.0 22.5 L 12.0 21.8 L 8.0 22.5 L 8.0 21.4 L 10.8 19.8 L 10.4 13.4 L 1.5 16.8 L 1.5 15.4 L 3.4 14.1 L 3.4 12.4 L 4.6 12.4 L 4.6 13.2 L 6.5 11.8 L 6.5 9.9 L 7.8 9.9 L 7.8 10.8 L 10.4 8.8 L 10.4 4.2 C 10.4 2.3 11.3 1.4 12 1.4 Z",
    airline:          "M 12 1.8 C 12.6 1.8 13.4 2.6 13.4 4.2 L 13.4 9.1 L 16.2 11.1 L 16.2 10.3 L 17.5 10.3 L 17.5 12.1 L 20.8 14.5 L 20.8 16.2 L 13.4 13.2 L 13.1 19.8 L 15.3 21.2 L 15.3 22.3 L 12.0 21.6 L 8.7 22.3 L 8.7 21.2 L 10.9 19.8 L 10.6 13.2 L 3.2 16.2 L 3.2 14.5 L 6.5 12.1 L 6.5 10.3 L 7.8 10.3 L 7.8 11.1 L 10.6 9.1 L 10.6 4.2 C 10.6 2.6 11.4 1.8 12 1.8 Z",
    cargo_commercial: "M 12 1.6 C 12.8 1.6 13.7 2.6 13.7 4.5 L 13.7 9.2 L 16.5 11.3 L 16.5 10.4 L 17.8 10.4 L 17.8 12.3 L 21.5 14.8 L 21.5 16.5 L 13.7 13.5 L 13.2 19.9 L 15.8 21.4 L 15.8 22.5 L 12.0 21.7 L 8.2 22.5 L 8.2 21.4 L 10.8 19.9 L 10.3 13.5 L 2.5 16.5 L 2.5 14.8 L 6.2 12.3 L 6.2 10.4 L 7.5 10.4 L 7.5 11.3 L 10.3 9.2 L 10.3 4.5 C 10.3 2.6 11.2 1.6 12 1.6 Z",
    charter:          "M 12 1.8 C 12.6 1.8 13.4 2.6 13.4 4.2 L 13.4 9.1 L 16.2 11.1 L 16.2 10.3 L 17.5 10.3 L 17.5 12.1 L 20.8 14.5 L 20.8 16.2 L 13.4 13.2 L 13.1 19.8 L 15.3 21.2 L 15.3 22.3 L 12.0 21.6 L 8.7 22.3 L 8.7 21.2 L 10.9 19.8 L 10.6 13.2 L 3.2 16.2 L 3.2 14.5 L 6.5 12.1 L 6.5 10.3 L 7.8 10.3 L 7.8 11.1 L 10.6 9.1 L 10.6 4.2 C 10.6 2.6 11.4 1.8 12 1.8 Z",
    turboprop:        "M 12 1.8 C 12.6 1.8 13.3 2.5 13.3 4.2 L 13.3 9.4 L 15.6 10.4 L 15.6 9.2 L 16.8 9.2 L 16.8 10.9 L 21.0 12.8 L 21.0 14.2 L 13.3 13.0 L 13.1 19.8 L 15.6 21.4 L 15.6 22.4 L 12.0 21.7 L 8.4 22.4 L 8.4 21.4 L 10.9 19.8 L 10.7 13.0 L 3.0 14.2 L 3.0 12.8 L 7.2 10.9 L 7.2 9.2 L 8.4 9.2 L 8.4 10.4 L 10.7 9.4 L 10.7 4.2 C 10.7 2.5 11.4 1.8 12 1.8 Z",
    business_jet:     "M 12 1.6 C 12.5 1.6 13.1 2.4 13.1 4.2 L 13.1 9.6 L 19.5 14.2 L 19.5 15.6 L 13.1 13.4 L 13.1 16.0 L 14.8 16.0 L 14.8 18.8 L 13.1 18.8 L 13.1 20.2 L 15.6 21.8 L 15.6 22.6 L 12.0 21.8 L 8.4 22.6 L 8.4 21.8 L 10.9 20.2 L 10.9 18.8 L 9.2 18.8 L 9.2 16.0 L 10.9 16.0 L 10.9 13.4 L 4.5 15.6 L 4.5 14.2 L 10.9 9.6 L 10.9 4.2 C 10.9 2.4 11.5 1.6 12 1.6 Z",
    light_aircraft:   "M 12 2.2 C 12.5 2.2 13.0 2.8 13.0 4.0 L 13.0 9.6 L 18.8 11.8 L 18.8 13.2 L 13.0 12.8 L 12.8 19.4 L 15.0 21.0 L 15.0 22.0 L 12.0 21.5 L 9.0 22.0 L 9.0 21.0 L 11.2 19.4 L 11.0 12.8 L 5.2 13.2 L 5.2 11.8 L 11.0 9.6 L 11.0 4.0 C 11.0 2.8 11.5 2.2 12 2.2 Z",
    helicopter:       "M 12 1.8 L 12.6 1.8 L 12.6 4.5 L 22.5 4.5 L 22.5 5.5 L 12.6 5.5 L 12.8 7.5 C 13.6 7.8 14.2 8.8 14.2 10.2 L 14.2 13.5 L 12.7 14.2 L 12.7 19.6 L 14.8 20.8 L 14.8 22.4 L 12.7 21.6 L 12.7 23.0 L 11.3 23.0 L 11.3 21.6 L 9.2 22.4 L 9.2 20.8 L 11.3 19.6 L 11.3 14.2 L 9.8 13.5 L 9.8 10.2 C 9.8 8.8 10.4 7.8 11.2 7.5 L 11.4 5.5 L 1.5 5.5 L 1.5 4.5 L 11.4 4.5 L 11.4 1.8 Z",
    general_aviation: "M 12 2.0 C 12.5 2.0 13.1 2.8 13.1 4.2 L 13.1 9.4 L 19.2 12.5 L 19.2 14.0 L 13.1 13.0 L 12.9 19.6 L 15.2 21.2 L 15.2 22.2 L 12.0 21.6 L 8.8 22.2 L 8.8 21.2 L 11.1 19.6 L 10.9 13.0 L 4.8 14.0 L 4.8 12.5 L 10.9 9.4 L 10.9 4.2 C 10.9 2.8 11.5 2.0 12 2.0 Z"
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
   * Specialized animated SVG generators for Helicopter & Drone
   */
  function getHelicopterSvgInner(color, strokeColor, strokeWidth, opacity) {
    return `
      <!-- Helicopter Landing Skids -->
      <line x1="8" y1="7.2" x2="8" y2="13.8" stroke="${strokeColor}" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="16" y1="7.2" x2="16" y2="13.8" stroke="${strokeColor}" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="8" y1="9.2" x2="10.5" y2="9.2" stroke="${strokeColor}" stroke-width="1.0"/>
      <line x1="13.5" y1="9.2" x2="16" y2="9.2" stroke="${strokeColor}" stroke-width="1.0"/>
      <line x1="8" y1="12.2" x2="10.5" y2="12.2" stroke="${strokeColor}" stroke-width="1.0"/>
      <line x1="13.5" y1="12.2" x2="16" y2="12.2" stroke="${strokeColor}" stroke-width="1.0"/>

      <!-- Fuselage & Tail Boom -->
      <path d="M 12 4.2 C 13.6 4.2 14.6 5.8 14.6 8.5 L 14.3 13.0 C 14.1 14.2 13.3 15.0 12.8 15.8 L 12.6 21.6 L 14.8 21.0 L 14.8 22.0 L 12.6 22.5 L 11.4 22.5 L 11.4 15.8 C 10.9 15.0 10.1 14.2 9.9 13.0 L 9.6 8.5 C 9.6 5.8 10.6 4.2 12 4.2 Z" fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${opacity}"/>

      <!-- Tail Rotor (Animated Spin) -->
      <g class="spinning-tail-rotor" style="transform-origin: 14.8px 21.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 14.8 21.5" to="360 14.8 21.5" dur="0.14s" repeatCount="indefinite"/>
        <line x1="14.8" y1="19.2" x2="14.8" y2="23.8" stroke="${color}" stroke-width="1.3" stroke-linecap="round"/>
      </g>

      <!-- Rotor Disc Arc Guide (High-speed blur effect) -->
      <circle cx="12" cy="10.5" r="9.2" fill="none" stroke="${color}" stroke-width="0.75" stroke-dasharray="2, 3" opacity="0.45"/>

      <!-- Main Rotor Blades (Animated Spin) -->
      <g class="spinning-rotor-main" style="transform-origin: 12px 10.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 12 10.5" to="360 12 10.5" dur="0.22s" repeatCount="indefinite"/>
        <line x1="12" y1="1.3" x2="12" y2="19.7" stroke="${color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="2.8" y1="10.5" x2="21.2" y2="10.5" stroke="${color}" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="12" cy="10.5" r="1.6" fill="${strokeColor}"/>
      </g>
    `;
  }

  function getDroneSvgInner(color, strokeColor, strokeWidth, opacity) {
    return `
      <!-- 4 Diagonal Carbon Arms -->
      <line x1="12" y1="12" x2="5.5" y2="5.5" stroke="${strokeColor}" stroke-width="2.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="18.5" y2="5.5" stroke="${strokeColor}" stroke-width="2.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="18.5" y2="18.5" stroke="${strokeColor}" stroke-width="2.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="5.5" y2="18.5" stroke="${strokeColor}" stroke-width="2.0" stroke-linecap="round"/>

      <line x1="12" y1="12" x2="5.5" y2="5.5" stroke="${color}" stroke-width="1.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="18.5" y2="5.5" stroke="${color}" stroke-width="1.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="18.5" y2="18.5" stroke="${color}" stroke-width="1.0" stroke-linecap="round"/>
      <line x1="12" y1="12" x2="5.5" y2="18.5" stroke="${color}" stroke-width="1.0" stroke-linecap="round"/>

      <!-- Center Avionics Pod -->
      <path d="M 10 9 C 10 8.5 10.5 8 11 8 L 13 8 C 13.5 8 14 8.5 14 9 L 14.5 14 C 14.5 14.8 13.8 15.5 13 15.5 L 11 15.5 C 10.2 15.5 9.5 14.8 9.5 14 Z" fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${opacity}"/>

      <!-- Forward Heading Arrow / Camera Sensor -->
      <polygon points="12,4.8 13.6,7.5 10.4,7.5" fill="${color}" stroke="${strokeColor}" stroke-width="0.5"/>

      <!-- Rotor Disc Circles -->
      <circle cx="5.5" cy="5.5" r="3.5" fill="none" stroke="${color}" stroke-width="0.6" stroke-dasharray="1.5, 2" opacity="0.45"/>
      <circle cx="18.5" cy="5.5" r="3.5" fill="none" stroke="${color}" stroke-width="0.6" stroke-dasharray="1.5, 2" opacity="0.45"/>
      <circle cx="18.5" cy="18.5" r="3.5" fill="none" stroke="${color}" stroke-width="0.6" stroke-dasharray="1.5, 2" opacity="0.45"/>
      <circle cx="5.5" cy="18.5" r="3.5" fill="none" stroke="${color}" stroke-width="0.6" stroke-dasharray="1.5, 2" opacity="0.45"/>

      <!-- 4 Spinning Propellers (Counter-Rotating CW / CCW) -->
      <g class="spinning-drone-rotor-cw" style="transform-origin: 5.5px 5.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 5.5 5.5" to="360 5.5 5.5" dur="0.18s" repeatCount="indefinite"/>
        <line x1="2.5" y1="5.5" x2="8.5" y2="5.5" stroke="${color}" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="5.5" cy="5.5" r="1.0" fill="${strokeColor}"/>
      </g>
      <g class="spinning-drone-rotor-ccw" style="transform-origin: 18.5px 5.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 18.5 5.5" to="-360 18.5 5.5" dur="0.18s" repeatCount="indefinite"/>
        <line x1="15.5" y1="5.5" x2="21.5" y2="5.5" stroke="${color}" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="18.5" cy="5.5" r="1.0" fill="${strokeColor}"/>
      </g>
      <g class="spinning-drone-rotor-cw" style="transform-origin: 18.5px 18.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 18.5 18.5" to="360 18.5 18.5" dur="0.18s" repeatCount="indefinite"/>
        <line x1="15.5" y1="18.5" x2="21.5" y2="18.5" stroke="${color}" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="18.5" cy="18.5" r="1.0" fill="${strokeColor}"/>
      </g>
      <g class="spinning-drone-rotor-ccw" style="transform-origin: 5.5px 18.5px;">
        <animateTransform attributeName="transform" type="rotate" from="0 5.5 18.5" to="-360 5.5 18.5" dur="0.18s" repeatCount="indefinite"/>
        <line x1="2.5" y1="18.5" x2="8.5" y2="18.5" stroke="${color}" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="5.5" cy="18.5" r="1.0" fill="${strokeColor}"/>
      </g>
    `;
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

    // Icon size varies by category importance (calibrated for high-res silhouette readability)
    const sizeMap = {
      heavy: 30, airline: 26, cargo_commercial: 28, charter: 25,
      turboprop: 24, business_jet: 24, light_aircraft: 20,
      helicopter: 26,
      drone: 26,
      general_aviation: 21,
      fighter: 25, bomber: 28, transport: 28, tanker: 28,
      recon: 25, trainer: 23, military_general: 25
    };
    const size = isSelected ? 36 : (sizeMap[cat] || 25);

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

    const strokeColor  = hasCritical ? "#7f1d1d" : (isSelected ? "#0284c7" : "#0f172a");
    const strokeWidth  = hasCritical ? "1.2" : (isSelected ? "0.8" : "0.5");
    const opacity      = (isSelected || hasCritical) ? 1 : 0.96;

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

    let iconInnerSvg = "";
    if (cat === "helicopter") {
      iconInnerSvg = getHelicopterSvgInner(color, strokeColor, strokeWidth, opacity);
    } else if (cat === "drone") {
      iconInnerSvg = getDroneSvgInner(color, strokeColor, strokeWidth, opacity);
    } else {
      iconInnerSvg = `<path d="${path}" fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${opacity}"/>`;
    }

    const svgHtml = `
      <div class="radar-marker-container ${markerClass} ${hasCritical ? 'is-critical-marker' : ''} ${isSelected ? 'is-selected' : ''}" style="width:${size}px; height:${size}px;">
        <svg viewBox="0 0 24 24" class="radar-plane-svg" style="transform:rotate(${heading}deg); width:100%; height:100%; ${glowFilter}">
          ${ringSvg}
          ${iconInnerSvg}
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
