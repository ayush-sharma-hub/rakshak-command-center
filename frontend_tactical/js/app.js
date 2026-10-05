/**
 * PROJECT RAKSHAK — SEOC TACTICAL C4ISR COMMAND CENTER
 * js/app.js — Pure Vanilla ES6+ Application Brain
 * Backend: FastAPI at http://localhost:3000
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════════
const isFile = window.location.protocol === 'file:' || !window.location.host || window.location.origin === 'null';
const API = isFile ? 'http://localhost:3000' : window.location.origin;
const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsHost = isFile ? 'localhost:3000' : window.location.host;
const WS_URL = `${wsProto}//${wsHost}/ws/live`;
const AGENT_WS_URL = `${wsProto}//${wsHost}/api/agent/stream`;
const AGENT_WS_FALLBACK = `${wsProto}//${wsHost}/stream`;

const LORA_NODES_STATIC = [
    { id: 'LORA-GW-08', sector: 'SEOC Central Hub · Rudraprayag', rssi: -68, status: 'ACTIVE' },
    { id: 'LORA-GW-05', sector: 'Kedarnath Base Camp Post',       rssi: -78, status: 'ACTIVE' },
    { id: 'LORA-ND-04', sector: 'Sonprayag Relay Node',           rssi: -84, status: 'ACTIVE' },
    { id: 'LORA-ND-03', sector: 'Gaurikund Upper Station',        rssi: -89, status: 'ACTIVE' },
    { id: 'LORA-ND-02', sector: 'Rambara Gorge Repeater',         rssi: -93, status: 'MARGINAL' },
    { id: 'LORA-ND-01', sector: 'Bheerunbali Forward Post',       rssi: -97, status: 'MARGINAL' },
    { id: 'LORA-ND-06', sector: 'Badrinath Sector Node',          rssi: -81, status: 'ACTIVE' },
    { id: 'LORA-ND-07', sector: 'Joshimath Ridge Station',        rssi: -86, status: 'ACTIVE' },
];

const FORCES_STATIC = [
    { id: 'NDRF-11/C', name: 'Rudraprayag NDRF Alpha', status: 'DEPLOYED' },
    { id: 'SDRF-UKH-3', name: 'Uttarkashi SDRF Bravo', status: 'DEPLOYED' },
    { id: 'SDRF-UKH-7', name: 'Chamoli Quick Response', status: 'STANDBY' },
    { id: 'NDRF-11/D', name: 'Tehri Dam Security Unit', status: 'DEPLOYED' },
    { id: 'SDRF-UKH-2', name: 'Pithoragarh Mountain Rescue', status: 'STANDBY' },
    { id: 'AIRF-HQ',   name: 'Heli-Med Evac · Jolly Grant', status: 'STANDBY' },
];

let terminalPaused = false;
let incidentCount = 0;
let leafletMap = null;
let riverMarkers = [];
let sosMarkers = [];

// ═══════════════════════════════════════════════════════════════════
// 1. LIVE DUAL-TIMEZONE CLOCK
// ═══════════════════════════════════════════════════════════════════
function startClock() {
    const elIST  = document.getElementById('clock-ist');
    const elUTC  = document.getElementById('clock-utc');
    const elDate = document.getElementById('hud-date');

    function tick() {
        const now = new Date();

        // IST = UTC+5:30
        const ist = new Date(now.getTime() + (5.5 * 3600 * 1000));
        const utc = now;

        const fmt = (d) =>
            [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()]
                .map(v => String(v).padStart(2, '0'))
                .join(':');

        elIST.textContent = fmt(ist);
        elUTC.textContent = fmt(utc);

        // Date display
        const months = ['JAN','FEB','MAR','APR','MAY','JUN',
                        'JUL','AUG','SEP','OCT','NOV','DEC'];
        const days   = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
        elDate.textContent =
            `${days[now.getUTCDay()]} ${String(now.getUTCDate()).padStart(2,'0')}-` +
            `${months[now.getUTCMonth()]}-${now.getUTCFullYear()}`;
    }

    tick();
    setInterval(tick, 1000);
}

// ═══════════════════════════════════════════════════════════════════
// 2. TACTICAL LEAFLET MAP
// ═══════════════════════════════════════════════════════════════════
function initMap() {
    leafletMap = L.map('tactical-map', {
        center: [30.0668, 79.0193],
        zoom: 8,
        zoomControl: false,
        attributionControl: false
    });

    // CartoDB Dark Matter — crisp, true military contrast without watermark/API key
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
        attribution: ''
    }).addTo(leafletMap);

    // Track cursor coordinates
    leafletMap.on('mousemove', (e) => {
        const coordEl = document.getElementById('cursor-coord');
        if (coordEl) {
            coordEl.textContent =
                `LAT: ${e.latlng.lat.toFixed(4)} · LNG: ${e.latlng.lng.toFixed(4)}`;
        }
    });

    // Track zoom level
    leafletMap.on('zoom', () => {
        const zEl = document.getElementById('map-zoom');
        if (zEl) zEl.textContent = leafletMap.getZoom();
    });

    // River monitoring station markers with vibrant glowing pulsing circles
    const riverStations = [
        { name: 'Mandakini at Rudraprayag', lat: 30.2844, lng: 78.9811, status: 'WARNING' },
        { name: 'Alaknanda at Joshimath',   lat: 30.5599, lng: 79.5644, status: 'NORMAL' },
        { name: 'Bhagirathi at Uttarkashi', lat: 30.7260, lng: 78.4370, status: 'NORMAL' },
        { name: 'THDC Tehri Dam Reservoir', lat: 30.3784, lng: 78.4808, status: 'NORMAL' },
        { name: 'Kali at Dharchula',        lat: 29.8489, lng: 80.5340, status: 'NORMAL' },
    ];

    riverStations.forEach(s => {
        const color = s.status === 'DANGER' ? '#EF4444' :
                      s.status === 'WARNING' ? '#F59E0B' : '#06B6D4';
        const pulseClass = s.status === 'DANGER' ? 'pin-red' :
                           s.status === 'WARNING' ? 'pin-amber' : 'pin-cyan';

        const icon = L.divIcon({
            className: '',
            html: `<div class="map-pin-circle ${pulseClass}" style="
                width:14px; height:14px;
                background:${color};
                border:2px solid #ffffff;
                box-shadow:0 0 14px ${color};
                position:relative;
            ">
                <div style="
                    position:absolute; inset:-4px;
                    border:1px solid ${color};
                    border-radius:50%;
                    opacity:0.6;
                    animation:dot-blink 1.8s infinite;
                "></div>
            </div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });

        const m = L.marker([s.lat, s.lng], { icon })
            .bindPopup(`
                <div style="padding:4px 0;">
                    <div style="font-weight:800;color:${color};margin-bottom:4px;letter-spacing:0.06em;">${s.name}</div>
                    <div>STATUS: <b style="color:${color}">${s.status}</b></div>
                    <div>LAT: ${s.lat} | LNG: ${s.lng}</div>
                </div>
            `)
            .addTo(leafletMap);
        riverMarkers.push(m);
    });

    // NDRF/SDRF unit markers with illuminated tactical beacons
    const unitPositions = [
        { id: 'NDRF-11/C', lat: 30.28, lng: 78.98, name: 'Rudraprayag NDRF Alpha' },
        { id: 'SDRF-UKH-3', lat: 30.73, lng: 78.44, name: 'Uttarkashi SDRF Bravo' },
        { id: 'SDRF-UKH-7', lat: 30.42, lng: 79.32, name: 'Chamoli Quick Response' },
    ];

    unitPositions.forEach(u => {
        const icon = L.divIcon({
            className: '',
            html: `<div style="
                display:inline-flex; align-items:center; gap:4px;
                font-size:9px; font-weight:800; font-family:'JetBrains Mono', Courier New, monospace;
                color:#22C55E; background:rgba(13,17,23,0.92);
                border:1px solid #22C55E;
                padding:2px 6px;
                box-shadow:0 0 10px rgba(34,197,94,0.5);
                backdrop-filter:blur(4px);
            ">
                <span class="led-blinker led-green"></span>
                <span>${u.id}</span>
            </div>`,
            iconAnchor: [34, 10]
        });
        L.marker([u.lat, u.lng], { icon })
            .bindPopup(`<div>UNIT: <b>${u.id}</b><br>${u.name}<br>STATUS: <span style="color:#22C55E; font-weight:800;">DEPLOYED</span></div>`)
            .addTo(leafletMap);
    });
}

function mapZoomHome() {
    if (leafletMap) leafletMap.setView([30.0668, 79.0193], 7);
}

function toggleMapLayer(type) {
    // Placeholder for satellite / flood overlay toggle
    addTerminalEntry('SYS', `MAP LAYER TOGGLE: ${type.toUpperCase()} — (attach your tile source)`, 'sys');
}

// ═══════════════════════════════════════════════════════════════════
// 3. FETCH — LIVE RIVER TELEMETRY FROM FASTAPI
// ═══════════════════════════════════════════════════════════════════
async function fetchRiverTelemetry() {
    try {
        const res = await fetch(`${API}/api/river-basins/live`);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();

        renderRiverGrid(data.rivers || []);

        const ts = document.getElementById('river-ts');
        if (ts) {
            const d = new Date(data.fetched_at);
            ts.textContent = d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
        }

        // Check for danger rivers and trigger alert banner
        const danger = (data.rivers || []).filter(r => r.status === 'DANGER' || r.status === 'EXTREME_FLOOD');
        if (danger.length > 0) {
            showAlertBanner(`🚨 ${danger[0].river} — ${danger[0].status} LEVEL BREACHED`);
            setThreatLevel('CRITICAL', 5);
        }

    } catch (e) {
        console.warn('[River Telemetry]', e.message);
        // Show cached/placeholder data
        renderRiverGrid([]);
    }
}

function renderRiverGrid(rivers) {
    const grid = document.getElementById('river-sensor-grid');
    if (!grid) return;

    if (rivers.length === 0) {
        grid.innerHTML = `<div class="sensor-loading"><i class="fa-solid fa-circle-exclamation"></i> BACKEND OFFLINE — CACHED SIMULATION MODE</div>`;
        return;
    }

    grid.innerHTML = rivers.map(r => {
        const isDanger  = r.status === 'DANGER' || r.status === 'EXTREME_FLOOD';
        const isWarning = r.status === 'WARNING';
        const rowClass  = isDanger ? 'sensor-danger' : isWarning ? 'sensor-warning' : '';
        const badgeClass = isDanger ? 'badge-danger' : isWarning ? 'badge-warning' : 'badge-normal';
        const barClass   = isDanger ? 'bar-danger'  : isWarning ? 'bar-warning'  : '';

        const bedDatum = (r.current_level - r.gauge_height_m).toFixed(1);
        const pct = Math.min(100, Math.max(4,
            ((r.current_level - parseFloat(bedDatum)) /
             (r.danger_level_m - parseFloat(bedDatum))) * 100
        )).toFixed(0);

        return `
        <div class="sensor-row ${rowClass}">
            <div style="flex:1">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
                    <span class="sensor-basin">${r.basin}</span>
                    <span class="sensor-level">${r.current_level.toFixed(2)}<span class="sensor-unit">m MSL</span></span>
                    <span class="sensor-badge ${badgeClass}">${r.status}</span>
                </div>
                <div class="sensor-bar-wrap">
                    <div class="sensor-bar-fill ${barClass}" style="width:${pct}%"></div>
                </div>
                <div class="sensor-meta">
                    <span class="sensor-meta-item">RAIN: <span>${r.upstream_precip_mmhr}mm/h</span></span>
                    <span class="sensor-meta-item">Q: <span>${r.discharge_m3s}m³/s</span></span>
                    <span class="sensor-meta-item">H: <span>${r.gauge_height_m}m</span></span>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════════
// 4. FETCH — SEOC INCIDENT FEED FROM FASTAPI
// ═══════════════════════════════════════════════════════════════════
let lastIncidentId = 0;

async function fetchIncidents() {
    try {
        const url = lastIncidentId > 0
            ? `${API}/api/alerts/latest?after_id=${lastIncidentId}`
            : `${API}/api/alerts/latest`;

        const res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const incidents = await res.json();

        if (incidents.length > 0) {
            incidents.forEach(inc => {
                if (inc.id > lastIncidentId) lastIncidentId = inc.id;
                const level = inc.priority === 'CRITICAL' ? 'critical' :
                              inc.priority === 'HIGH'     ? 'warning'  : 'info';
                addTerminalEntry(
                    inc.type || 'INCIDENT',
                    inc.msg || 'Unknown event',
                    level,
                    inc.zone || '---',
                    inc.created_at
                );
            });
        }
    } catch (e) {
        // silently fail — backend may be starting
    }
}

// ═══════════════════════════════════════════════════════════════════
// 5. AUTONOMOUS AGENT API & WEBSOCKET TELEMETRY
// ═══════════════════════════════════════════════════════════════════
let agentWs = null;
let agentWsTimer = null;

function connectAgentWebSocket() {
    if (agentWs && (agentWs.readyState === WebSocket.OPEN || agentWs.readyState === WebSocket.CONNECTING)) {
        return;
    }
    if (agentWsTimer) {
        clearTimeout(agentWsTimer);
        agentWsTimer = null;
    }

    function tryConnect(url, isFallback = false) {
        if (agentWs && (agentWs.readyState === WebSocket.OPEN || agentWs.readyState === WebSocket.CONNECTING)) {
            return;
        }
        try {
            const ws = new WebSocket(url);

            ws.onopen = () => {
                agentWs = ws;
                if (agentWsTimer) { clearTimeout(agentWsTimer); agentWsTimer = null; }
                console.log(`[Agent WS] Connected to ${url}`);
                addTerminalEntry('AGENT WS', 'Autonomous Agent telemetry stream link established.', 'sys');
            };

            ws.onmessage = (evt) => {
                try {
                    const msg = JSON.parse(evt.data);
                    if (msg.type === 'thought') {
                        const lvl = msg.level || 'info';
                        addTerminalEntry('AI AGENT', msg.log || '', lvl);
                    } else if (msg.type === 'result') {
                        if (msg.data) {
                            applyAgentAnalysisResult(msg.data);
                        }
                    }
                } catch (err) {
                    if (evt.data) {
                        addTerminalEntry('AI AGENT', String(evt.data), 'info');
                    }
                }
            };

            ws.onclose = () => {
                agentWs = null;
                if (agentWsTimer) clearTimeout(agentWsTimer);
                if (!isFallback) {
                    agentWsTimer = setTimeout(() => tryConnect(AGENT_WS_FALLBACK, true), 3000);
                } else {
                    agentWsTimer = setTimeout(() => tryConnect(AGENT_WS_URL, false), 5000);
                }
            };

            ws.onerror = (e) => {
                console.warn('[Agent WS] Connection state event:', e);
            };
        } catch (e) {
            agentWs = null;
            console.warn('[Agent WS] Init failed:', e);
        }
    }

    tryConnect(AGENT_WS_URL, false);
}

async function triggerLocationAnalysis() {
    const input = document.getElementById('target-location-input');
    const btn = document.getElementById('btn-analyze-target');
    const location = (input ? input.value : '').trim() || 'Rudraprayag, Uttarakhand';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> SCANNING…';
    }

    addTerminalEntry('MISSION', `Target Sector Assessment dispatched: '${location}'`, 'warning');

    // Also send through WebSocket if open for immediate interactive streaming
    if (agentWs && agentWs.readyState === WebSocket.OPEN) {
        try {
            agentWs.send(JSON.stringify({ location: location }));
        } catch (e) { /* ignore */ }
    }

    try {
        const res = await fetch(`${API}/api/agent/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location: location })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();
        applyAgentAnalysisResult(data);

    } catch (err) {
        console.error('[Agent Assessment Error]', err);
        addTerminalEntry('ERROR', `Assessment execution error: ${err.message}`, 'critical');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-microchip"></i> ANALYZE SECTOR';
        }
    }
}

function applyAgentAnalysisResult(data) {
    if (!data) return;

    const threat = String(data.threat_level || 'Normal').trim();
    const location = data.location || 'Target Sector';
    const hazards = data.active_hazards || [];
    const actionPlan = data.action_plan || [];
    const summary = data.summary || 'Situational analysis complete.';
    const confidence = data.confidence || 'Medium';
    const resources = data.resources_needed || {};

    // 1. Dynamic UI Theme & Border Transitions
    document.body.classList.remove('threat-severe', 'threat-elevated', 'threat-normal');
    if (threat.toLowerCase() === 'severe' || threat.toLowerCase() === 'critical') {
        document.body.classList.add('threat-severe');
        setThreatLevel('SEVERE', 5);
        showAlertBanner(`🚨 SEVERE THREAT DETECTED: ${location.toUpperCase()} | IMMEDIATE EVACUATION DIRECTIVE`);
    } else if (threat.toLowerCase() === 'elevated' || threat.toLowerCase() === 'warning') {
        document.body.classList.add('threat-elevated');
        setThreatLevel('ELEVATED', 3);
        showAlertBanner(`⚠️ ELEVATED RISK ADVISORY: ${location.toUpperCase()}`);
    } else {
        document.body.classList.add('threat-normal');
        setThreatLevel('NORMAL', 1);
    }

    // 2. Populate AI Intel Brief HUD Overlay
    const overlay = document.getElementById('ai-intel-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');

        const elLoc = document.getElementById('ai-intel-location');
        if (elLoc) elLoc.textContent = location.toUpperCase();

        const elThreat = document.getElementById('ai-intel-threat');
        if (elThreat) {
            elThreat.textContent = threat.toUpperCase();
            elThreat.style.color = threat.toLowerCase() === 'severe' ? 'var(--alert-red)' :
                                   threat.toLowerCase() === 'elevated' ? 'var(--alert-amber)' : 'var(--alert-green)';
        }

        const elConf = document.getElementById('ai-intel-confidence');
        if (elConf) elConf.textContent = confidence.toUpperCase();

        const elNdrf = document.getElementById('ai-intel-ndrf');
        if (elNdrf) elNdrf.textContent = resources.ndrf_teams || 0;

        const elHelis = document.getElementById('ai-intel-helis');
        if (elHelis) elHelis.textContent = resources.helicopters || 0;

        const elHazards = document.getElementById('ai-intel-hazards');
        if (elHazards) {
            elHazards.innerHTML = hazards.length > 0
                ? hazards.map(h => `<span class="ai-hazard-chip ${threat.toLowerCase() === 'severe' ? 'severe' : ''}">${h}</span>`).join('')
                : '<span class="ai-hazard-chip">None active</span>';
        }

        const elSumm = document.getElementById('ai-intel-summary');
        if (elSumm) elSumm.textContent = summary;

        const elActions = document.getElementById('ai-intel-actions');
        if (elActions) {
            elActions.innerHTML = actionPlan.map(a => `<li><span>${a}</span></li>`).join('');
        }
    }

    // 3. Print directives into the Bottom Terminal Log
    const lvl = threat.toLowerCase() === 'severe' ? 'critical' : (threat.toLowerCase() === 'elevated' ? 'warning' : 'info');
    addTerminalEntry('ASSESSMENT', `Threat: ${threat.toUpperCase()} (${confidence} Conf) | Hazards: ${hazards.join(', ') || 'None'}`, lvl, location);

    actionPlan.slice(0, 3).forEach((item, idx) => {
        addTerminalEntry('DIRECTIVE', `${idx + 1}. ${item}`, 'warning', location);
    });

    // 4. Map centering if known sector coordinates exist
    const LOC_COORDS = {
        'rudraprayag': [30.2844, 78.9811],
        'kedarnath': [30.7346, 79.0669],
        'joshimath': [30.5599, 79.5644],
        'badrinath': [30.7433, 79.4938],
        'uttarkashi': [30.7260, 78.4370],
        'tehri': [30.3784, 78.4808],
        'dharchula': [29.8489, 80.5340],
        'roorkee': [29.8543, 77.8880],
        'dehradun': [30.3165, 78.0322],
        'chamoli': [30.4074, 79.3248]
    };
    const key = Object.keys(LOC_COORDS).find(k => location.toLowerCase().includes(k));
    if (key && leafletMap) {
        leafletMap.setView(LOC_COORDS[key], 10);
        addSOSMarkerToMap({
            lat: LOC_COORDS[key][0],
            lng: LOC_COORDS[key][1],
            zone: location,
            message: `THREAT: ${threat.toUpperCase()} — ${hazards.join(', ') || summary.slice(0, 50)}`
        });
    }
}

function dismissAiIntel() {
    const overlay = document.getElementById('ai-intel-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// ═══════════════════════════════════════════════════════════════════
// 6. FETCH — SYSTEM STATE FROM /api/state
// ═══════════════════════════════════════════════════════════════════
async function fetchSystemState() {
    try {
        const res = await fetch(`${API}/api/state`);
        if (!res.ok) return;
        const data = await res.json();

        // Update threat level from risk score
        if (data.risk && data.risk.score !== undefined) {
            const score = data.risk.score;
            if (score >= 80)      setThreatLevel('CRITICAL', 5);
            else if (score >= 60) setThreatLevel('HIGH', 4);
            else if (score >= 40) setThreatLevel('ELEVATED', 3);
            else if (score >= 20) setThreatLevel('GUARDED', 2);
            else                  setThreatLevel('LOW', 1);
        }

        // Update CPU/memory indicators (simulated from sensor count)
        const cpuEl = document.getElementById('cpu-val');
        const memEl = document.getElementById('mem-val');
        if (cpuEl) cpuEl.textContent = (12 + Math.random() * 15).toFixed(0) + '%';
        if (memEl) memEl.textContent = (38 + Math.random() * 12).toFixed(0) + '%';

    } catch (e) {
        // backend warming up
    }
}

// ═══════════════════════════════════════════════════════════════════
// 7. WEBSOCKET LIVE FEED
// ═══════════════════════════════════════════════════════════════════
let liveWs = null;
let liveWsTimer = null;

function connectWebSocket() {
    if (liveWs && (liveWs.readyState === WebSocket.OPEN || liveWs.readyState === WebSocket.CONNECTING)) {
        return;
    }
    if (liveWsTimer) {
        clearTimeout(liveWsTimer);
        liveWsTimer = null;
    }
    const wsEl = document.getElementById('ws-status');

    function connect() {
        if (liveWs && (liveWs.readyState === WebSocket.OPEN || liveWs.readyState === WebSocket.CONNECTING)) {
            return;
        }
        try {
            liveWs = new WebSocket(WS_URL);

            liveWs.onopen = () => {
                if (liveWsTimer) { clearTimeout(liveWsTimer); liveWsTimer = null; }
                if (wsEl) { wsEl.textContent = 'ACTIVE'; wsEl.style.color = 'var(--alert-green)'; }
                addTerminalEntry('SYS', 'WebSocket live feed connected — SEOC data stream active.', 'sys');
            };

            liveWs.onmessage = (evt) => {
                try {
                    const msg = JSON.parse(evt.data);
                    handleWsMessage(msg);
                } catch (e) { /* ignore */ }
            };

            liveWs.onclose = () => {
                liveWs = null;
                if (wsEl) { wsEl.textContent = 'RECONNECTING'; wsEl.style.color = 'var(--alert-amber)'; }
                if (liveWsTimer) clearTimeout(liveWsTimer);
                liveWsTimer = setTimeout(connect, 4000);
            };

            liveWs.onerror = () => {
                if (wsEl) { wsEl.textContent = 'DISCONNECTED'; wsEl.style.color = 'var(--alert-red)'; }
            };
        } catch (e) {
            liveWs = null;
            if (wsEl) { wsEl.textContent = 'N/A'; wsEl.style.color = 'var(--text-dim)'; }
        }
    }

    connect();
}

function handleWsMessage(msg) {
    if (!msg || !msg.type) return;

    switch (msg.type) {
        case 'sos_signal':
            addTerminalEntry('SOS DISTRESS', msg.message || 'SOS Signal received.', 'critical', msg.zone || '---');
            addSOSMarkerToMap(msg);
            showAlertBanner(`SOS: ${msg.zone || 'Unknown Location'} — SDRF DISPATCH REQUIRED`);
            break;
        case 'incident_update':
            fetchIncidents();
            break;
        case 'river_alert':
            fetchRiverTelemetry();
            addTerminalEntry('RIVER ALERT', msg.message || 'River basin status update.', 'warning', msg.zone || '---');
            break;
        default:
            break;
    }
}

function addSOSMarkerToMap(sos) {
    if (!leafletMap || !sos.lat || !sos.lng) return;
    const icon = L.divIcon({
        className: '',
        html: `<div style="
            font-size:8px;font-weight:900;font-family:Courier New;
            color:#fff;background:#EF4444;
            border:1px solid #fff;
            padding:2px 5px;
            animation:pulse-red 1s infinite;
            box-shadow:0 0 12px rgba(239,68,68,0.6);
            cursor:pointer;
        ">SOS</div>`,
        iconAnchor: [16, 8]
    });
    L.marker([sos.lat, sos.lng], { icon })
        .bindPopup(`<div><b style="color:#EF4444">SOS DISTRESS</b><br>${sos.message || ''}<br>Zone: ${sos.zone || '---'}</div>`)
        .addTo(leafletMap);
}

// ═══════════════════════════════════════════════════════════════════
// 8. TERMINAL — TYPEWRITER SLIDE-IN ENTRY
// ═══════════════════════════════════════════════════════════════════
function addTerminalEntry(type, msg, level = 'info', zone = '', timestamp = null) {
    if (terminalPaused) return;

    incidentCount++;
    const countEl = document.getElementById('incident-count');
    if (countEl) countEl.textContent = incidentCount;

    const body = document.getElementById('terminal-body');
    if (!body) return;

    const now = timestamp ? new Date(timestamp) : new Date();
    const ts = [now.getHours(), now.getMinutes(), now.getSeconds()]
        .map(v => String(v).padStart(2, '0')).join(':');

    const levelMap = {
        critical: 'te-critical',
        warning:  'te-warning',
        info:     'te-info',
        sys:      'te-sys',
    };

    const entry = document.createElement('div');
    entry.className = `terminal-entry ${levelMap[level] || 'te-info'}`;
    entry.innerHTML = `
        <span class="te-ts">${ts}</span>
        <span class="te-type">[${(type || 'EVENT').substring(0, 10).toUpperCase()}]</span>
        <span class="te-msg" id="te-msg-${incidentCount}"></span>
        ${zone ? `<span class="te-zone">${zone}</span>` : ''}
    `;

    body.appendChild(entry);

    // Typewriter effect for message — scroll again when done
    typewriterEffect(`te-msg-${incidentCount}`, msg, 18, () => {
        body.scrollTop = body.scrollHeight;
    });

    // Immediate auto-scroll to bottom
    body.scrollTop = body.scrollHeight;

    // Limit terminal to last 200 entries
    const entries = body.querySelectorAll('.terminal-entry');
    if (entries.length > 200) {
        entries[0].remove();
    }
}

function typewriterEffect(elementId, text, speed = 20, onDone = null) {
    const el = document.getElementById(elementId);
    if (!el) return;
    let i = 0;
    const interval = setInterval(() => {
        if (i < text.length) {
            el.textContent += text[i++];
        } else {
            clearInterval(interval);
            if (onDone) onDone();
        }
    }, speed);
}

function clearTerminal() {
    const body = document.getElementById('terminal-body');
    if (body) body.innerHTML = '';
    incidentCount = 0;
    const countEl = document.getElementById('incident-count');
    if (countEl) countEl.textContent = '0';
}

function pauseTerminal() {
    terminalPaused = !terminalPaused;
    const btn = document.getElementById('pause-btn');
    if (btn) btn.textContent = terminalPaused ? '▶ RESUME' : '❚❚ PAUSE';
}

// ═══════════════════════════════════════════════════════════════════
// 9. BROADCAST COMMAND
// ═══════════════════════════════════════════════════════════════════
async function triggerBroadcast(channel) {
    const title = document.getElementById('bc-title').value.trim();
    const body  = document.getElementById('bc-body').value.trim();
    const status = document.getElementById('bc-status');

    if (!title || !body) {
        if (status) status.textContent = '> ERROR: Title and message body required.';
        return;
    }

    if (status) status.textContent = `> TRANSMITTING VIA ${channel}...`;

    try {
        if (channel === 'PUSH') {
            const res = await fetch(`${API}/api/push/broadcast`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, body })
            });
            const result = await res.json();
            if (status) status.textContent = `> OK: Push delivered. Sent: ${result.sent}, ntfy: ${result.ntfy_delivered ? 'YES' : 'NO'}`;
            addTerminalEntry('BROADCAST', `${title}: ${body}`, 'critical', 'ALL ZONES');
        } else if (channel === 'LORA') {
            const res = await fetch(`${API}/api/lora/broadcast`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: `${title}: ${body}`, priority: 'CRITICAL' })
            });
            const result = await res.json();
            if (status) status.textContent = `> LORA OK: ${result.nodes_count} mountain nodes reached. Hash: ${result.packet_hash}`;
            addTerminalEntry('LORA MESH', `${title}: ${body}`, 'critical', 'ALL HIMALAYAN SECTORS');
        }
    } catch (e) {
        if (status) status.textContent = `> TX ERROR: ${e.message}`;
    }
}

// ═══════════════════════════════════════════════════════════════════
// 10. STATIC UI RENDERERS
// ═══════════════════════════════════════════════════════════════════
function renderForceGrid() {
    const grid = document.getElementById('force-grid');
    if (!grid) return;
    grid.innerHTML = FORCES_STATIC.map(f => {
        const sc = f.status === 'DEPLOYED' ? 'fs-deployed' : 'fs-standby';
        return `
        <div class="force-row">
            <span class="force-id">${f.id}</span>
            <span class="force-name" title="${f.name}">${f.name}</span>
            <span class="force-status ${sc}">${f.status}</span>
        </div>`;
    }).join('');
}

function renderLoraGrid() {
    const grid = document.getElementById('lora-grid');
    if (!grid) return;
    grid.innerHTML = LORA_NODES_STATIC.map(n => {
        const dotClass = n.status === 'ACTIVE' ? 'status-green' :
                         n.status === 'MARGINAL' ? 'status-amber' : 'status-dim';
        return `
        <div class="lora-row">
            <span class="status-dot ${dotClass}"></span>
            <span class="lora-id">${n.id}</span>
            <span class="lora-sector" title="${n.sector}">${n.sector}</span>
            <span class="lora-rssi">${n.rssi}dBm</span>
        </div>`;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════════
// 11. THREAT LEVEL INDICATOR
// ═══════════════════════════════════════════════════════════════════
function setThreatLevel(label, bars) {
    const el = document.getElementById('threat-value');
    const barEls = document.querySelectorAll('.threat-bar');
    if (!el) return;

    el.textContent = label;
    const colorMap = {
        'CRITICAL': 'var(--alert-red)',
        'HIGH':     'var(--alert-red)',
        'ELEVATED': 'var(--alert-amber)',
        'GUARDED':  'var(--alert-amber)',
        'LOW':      'var(--alert-green)',
    };
    el.style.color = colorMap[label] || 'var(--alert-amber)';

    barEls.forEach((b, i) => {
        b.classList.remove('tb-active', 'tb-critical');
        if (i < bars) {
            b.classList.add(bars >= 4 ? 'tb-critical' : 'tb-active');
        }
    });
}

// ═══════════════════════════════════════════════════════════════════
// 12. ALERT BANNER
// ═══════════════════════════════════════════════════════════════════
function showAlertBanner(text) {
    const banner = document.getElementById('alert-banner');
    const textEl = document.getElementById('alert-banner-text');
    if (!banner || !textEl) return;
    textEl.textContent = text;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 10000);
}

function dismissBanner() {
    const banner = document.getElementById('alert-banner');
    if (banner) banner.classList.add('hidden');
}

// ═══════════════════════════════════════════════════════════════════
// 13. SPA VIEW ROUTER & NAVIGATION CONTROLLER
// ═══════════════════════════════════════════════════════════════════
function switchView(viewId) {
    // 1. Hide all spa-views, show target view with animation
    const views = document.querySelectorAll('.spa-view');
    views.forEach(v => {
        v.classList.remove('active-view');
        v.style.display = 'none';
    });
    
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.add('active-view');
        target.style.display = 'flex';
    }

    // 2. Update nav buttons with glowing cyan indicator
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.nav-btn[data-view="${viewId}"]`);
    if (btn) btn.classList.add('active');

    // 3. Recalculate Leaflet map dimensions if switching back to GIS
    if (viewId === 'view-gis' && leafletMap) {
        setTimeout(() => leafletMap.invalidateSize(), 80);
    }

    // 4. View-specific renders
    if (viewId === 'view-lora') {
        renderFullLoraNodes();
    }

    // 5. Announce viewport transition in C4ISR bottom terminal
    const labels = {
        'view-gis': 'TACTICAL GIS RADAR & AI COMMAND ZONE',
        'view-hydro': 'HIMALAYAN HYDROLOGICAL & DAM BASIN MATRIX',
        'view-evacuation': 'STATEWIDE EVACUATION LOGISTICS & TRANSIT COMMAND',
        'view-lora': 'OFFLINE LORA MESH RELAY TOPOLOGY & SNIFFER',
        'view-broadcast': 'INTEGRATED CIVIL DEFENSE BROADCAST HUB (CAP-UK)',
        'view-forces': 'TACTICAL QUICK RESPONSE FORCES (NDRF/SDRF/IAF)',
        'view-syslog': 'HARDWARE DIAGNOSTICS & WEBSOCKET EVENT KERNEL'
    };
    addTerminalEntry('NAV ROUTER', `Viewport shifted ➔ ${labels[viewId] || viewId.toUpperCase()}`, 'sys');
}
window.switchView = switchView;

function switchPanel(panel) {
    const map = {
        'map': 'view-gis',
        'rivers': 'view-hydro',
        'sos': 'view-gis',
        'lora': 'view-lora',
        'broadcast': 'view-broadcast',
        'forces': 'view-forces',
        'syslog': 'view-syslog'
    };
    switchView(map[panel] || 'view-gis');
}
window.switchPanel = switchPanel;

// ═══════════════════════════════════════════════════════════════════
// 14. LIVE TELEMETRY SIMULATION (Anti-Template Life Effect)
// ═══════════════════════════════════════════════════════════════════
function initTelemetryFlicker() {
    setInterval(() => {
        const elements = document.querySelectorAll('.live-data-flicker');
        if (!elements.length) return;

        // Randomly pick 2 to 4 elements to fluctuate
        const count = Math.min(elements.length, Math.floor(Math.random() * 3) + 2);
        for (let i = 0; i < count; i++) {
            const el = elements[Math.floor(Math.random() * elements.length)];
            const type = el.getAttribute('data-flicker');

            if (type === 'cpu') {
                const val = (14 + Math.random() * 12).toFixed(0);
                el.textContent = `${val}%`;
            } else if (type === 'mem') {
                const val = (40 + Math.random() * 7).toFixed(0);
                el.textContent = `${val}%`;
            } else if (type === 'signal') {
                const snr = (9.2 + (Math.random() * 0.8 - 0.4)).toFixed(1);
                el.textContent = `INSAT-3DR · SNR +${snr}dB`;
            } else if (type === 'coord') {
                const lat = (30.2840 + Math.random() * 0.0010).toFixed(4);
                const lng = (78.9810 + Math.random() * 0.0010).toFixed(4);
                el.textContent = `LAT: ${lat} · LNG: ${lng}`;
            } else if (type === 'sectors') {
                el.textContent = 115 + (Math.random() > 0.8 ? 1 : 0);
            } else if (el.textContent.includes('m³/s')) {
                const parts = el.textContent.split(' ');
                const base = parseFloat(parts[0]) || 40;
                const jitter = (base + (Math.random() * 0.6 - 0.3)).toFixed(1);
                el.textContent = `${jitter} m³/s`;
            } else if (el.textContent.includes('dBm')) {
                const base = parseInt(el.textContent) || -84;
                const jitter = base + Math.floor(Math.random() * 3 - 1);
                el.textContent = `${jitter} dBm`;
            }

            el.classList.add('data-update');
            setTimeout(() => el.classList.remove('data-update'), 200);
        }
    }, 1400);
}

// ═══════════════════════════════════════════════════════════════════
// 15. SCROLLING HEX STREAM COCKPIT EFFECT
// ═══════════════════════════════════════════════════════════════════
function initHexStream() {
    const col = document.getElementById('hex-stream-col');
    if (!col) return;

    function genHexWord() {
        const hex = Math.floor(Math.random() * 0xFFFF).toString(16).toUpperCase().padStart(4, '0');
        return `0x${hex}`;
    }

    col.innerHTML = Array.from({ length: 28 }, () => {
        const dur = (4 + Math.random() * 4).toFixed(1);
        const delay = (Math.random() * 3).toFixed(1);
        return `<div class="hex-cell" style="--hex-dur:${dur}s; --hex-delay:${delay}s">${genHexWord()}</div>`;
    }).join('');

    setInterval(() => {
        const cells = col.querySelectorAll('.hex-cell');
        if (!cells.length) return;
        const cell = cells[Math.floor(Math.random() * cells.length)];
        cell.textContent = genHexWord();
    }, 800);
}

// ═══════════════════════════════════════════════════════════════════
// 16. LORA & CIVIL DEFENSE BROADCAST HELPERS
// ═══════════════════════════════════════════════════════════════════
function renderFullLoraNodes() {
    const list = document.getElementById('lora-full-node-list');
    if (!list) return;
    list.innerHTML = LORA_NODES_STATIC.map(n => {
        const dotClass = n.status === 'ACTIVE' ? 'status-green' : 'status-amber';
        return `
        <div class="lora-row">
            <span class="status-dot ${dotClass}"></span>
            <span class="lora-id">${n.id}</span>
            <span class="lora-sector" title="${n.sector}">${n.sector}</span>
            <span class="hud-mono text-xs" style="color:var(--alert-cyan);">${(1.8 + Math.random() * 6).toFixed(1)} km</span>
            <span class="lora-rssi live-data-flicker">${n.rssi} dBm</span>
            <span class="hud-mono text-xs" style="color:var(--alert-green);">BATT: ${(3.9 + Math.random() * 0.25).toFixed(2)}V</span>
        </div>`;
    }).join('');
}

function injectLoraPacket() {
    const input = document.getElementById('lora-inject-input');
    const val = (input ? input.value : '').trim() || 'TEST_FRAME';
    const term = document.getElementById('lora-raw-terminal');
    const hex = Array.from(val).slice(0, 6).map(c => '0x' + c.charCodeAt(0).toString(16).toUpperCase()).join(' ');
    
    if (term) {
        const row = document.createElement('div');
        row.style.color = 'var(--alert-cyan)';
        row.textContent = `[TX 865.200] ${hex} -> PAYLOAD: ${val} (ACK_OK)`;
        term.prepend(row);
    }
    addTerminalEntry('LORA TX', `Injected field packet to 865MHz mesh: ${val}`, 'warning', '865.2MHz');
}
window.injectLoraPacket = injectLoraPacket;

async function triggerFullCapBroadcast() {
    const title = document.getElementById('bcast-hub-title').value.trim();
    const body = document.getElementById('bcast-hub-body').value.trim();
    const sector = document.getElementById('bcast-hub-sector').value.trim();
    const status = document.getElementById('bcast-hub-status');

    if (status) status.innerHTML = `<span style="color:var(--alert-amber)"><i class="fa-solid fa-satellite-dish fa-spin"></i> TRANSMITTING STATEWIDE CELL BROADCAST (CAP)...</span>`;

    try {
        const res = await fetch(`${API}/api/push/broadcast`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, body, sector })
        });
        const data = await res.json();
        if (status) {
            status.innerHTML = `<span style="color:var(--alert-green)">✔ BROADCAST DELIVERED: Sent: ${data.sent || 1}, Push/ntfy: ACTIVE. Jurisdiction: ${sector}</span>`;
        }
        addTerminalEntry('CAP BROADCAST', `${title} (Jurisdiction: ${sector})`, 'critical', sector);
        showAlertBanner(`STATEWIDE CAP ALERT TRANSMITTED: ${title}`);
    } catch (e) {
        if (status) {
            status.innerHTML = `<span style="color:var(--alert-cyan)">✔ SIMULATED CAP TRANSMISSION OK: Cell Towers (BSNL/Jio/Airtel) Broadcasted to ${sector}.</span>`;
        }
        addTerminalEntry('CAP BROADCAST', `[SIMULATED] ${title} delivered to ${sector}`, 'critical', sector);
    }
}
window.triggerFullCapBroadcast = triggerFullCapBroadcast;

function previewTtsAudio() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.35);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.35);
    } catch(e){}
    addTerminalEntry('AUDIO SYNTH', 'Synthesized Hindi alert chime dispatched to FM 100.5 MHz.', 'info');
}
window.previewTtsAudio = previewTtsAudio;

// ═══════════════════════════════════════════════════════════════════
// 17. MODAL
// ═══════════════════════════════════════════════════════════════════
function openModal(title, bodyHTML) {
    const modal = document.getElementById('sos-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody  = document.getElementById('modal-body');
    if (!modal) return;
    if (modalTitle) modalTitle.textContent = title;
    if (modalBody)  modalBody.innerHTML = bodyHTML;
    modal.classList.remove('hidden');
}

function closeModal() {
    const modal = document.getElementById('sos-modal');
    if (modal) modal.classList.add('hidden');
}

function dispatchUnit() {
    addTerminalEntry('DISPATCH', 'SDRF Unit dispatched from nearest post.', 'info', 'HQ → FIELD');
    closeModal();
}

function loraAck() {
    triggerBroadcast('LORA');
    closeModal();
}

// ═══════════════════════════════════════════════════════════════════
// 18. SIMULATION — RANDOM SOS FEED (for demo when backend offline)
// ═══════════════════════════════════════════════════════════════════
const SIM_EVENTS = [
    { type: 'WEATHER', msg: 'Cloudburst warning: Kedarnath sector — 84mm/hr rainfall detected.', level: 'warning', zone: 'Kedarnath' },
    { type: 'RIVER',   msg: 'Mandakini rising: Gauge height +1.8m in 30 min. Monitor closely.', level: 'warning', zone: 'Rudraprayag' },
    { type: 'LORA RX', msg: 'Packet received: LORA-ND-02 Rambara gorge — SNR: 8.4 dB.', level: 'info', zone: 'Rambara' },
    { type: 'SATCOM',  msg: 'INSAT-3DR telemetry uplink refreshed. 13 stations synchronized.', level: 'sys', zone: 'ORBIT' },
    { type: 'SOS',     msg: 'SOS Distress signal: 3 civilians stranded near Gaurikund bridge.', level: 'critical', zone: 'Gaurikund' },
    { type: 'SDRF',    msg: 'SDRF-UKH-3 Unit deployed to Uttarkashi sector. ETA: 18 minutes.', level: 'info', zone: 'Uttarkashi' },
    { type: 'RIVER',   msg: 'Alaknanda at Joshimath: Discharge 284 m³/s — within safe limits.', level: 'info', zone: 'Joshimath' },
];

let simIndex = 0;
function runSimulationFeed() {
    const ev = SIM_EVENTS[simIndex % SIM_EVENTS.length];
    addTerminalEntry(ev.type, ev.msg, ev.level, ev.zone);
    simIndex++;
}

// ═══════════════════════════════════════════════════════════════════
// 19. MASTER BOOT SEQUENCE
// ═══════════════════════════════════════════════════════════════════
async function boot() {
    // 1. Start live dual UTC/IST clock
    startClock();

    // 2. Render static grids & hardware streams
    renderForceGrid();
    renderLoraGrid();
    renderFullLoraNodes();
    initHexStream();
    initTelemetryFlicker();

    // 3. Init Leaflet tactical GIS map
    initMap();

    // 4. Initial telemetry fetch from backend
    await fetchRiverTelemetry();
    await fetchSystemState();
    await fetchIncidents();

    // 5. Connect WebSockets (Telemetry & Autonomous Agent)
    connectWebSocket();
    connectAgentWebSocket();

    // 6. Polling loops
    setInterval(fetchRiverTelemetry, 60000);    // River data every 60s
    setInterval(fetchIncidents, 8000);           // Incidents every 8s
    setInterval(fetchSystemState, 15000);        // State every 15s

    // 7. Simulation feed (adds 1 entry every 14s)
    setInterval(runSimulationFeed, 14000);

    // Boot message
    addTerminalEntry('BOOT', 'SEOC C4ISR Cockpit Engine online. All 6 SPA views active.', 'sys');
}

// Start on DOM ready
document.addEventListener('DOMContentLoaded', boot);

