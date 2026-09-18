// =========================================================================
// PROJECT RAKSHAK - UTTARAKHAND STATE EMERGENCY OPERATIONS CENTRE (SEOC)
// MASTER CLIENT ENGINE & TACTICAL DISPATCH PROTOCOL v3.0
// =========================================================================

// 1. TACTICAL WEB AUDIO ENGINE (Zero external dependencies)
class TacticalAudioEngine {
    constructor() {
        this.ctx = null;
        this.isMuted = localStorage.getItem('rakshak_muted') === 'true';
    }

    initCtx() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        localStorage.setItem('rakshak_muted', this.isMuted);
        this.updateAudioIcons();
        if (!this.isMuted) {
            this.playConfirm();
        }
        return this.isMuted;
    }

    updateAudioIcons() {
        const btns = document.querySelectorAll('.audio-toggle-btn');
        btns.forEach(btn => {
            if (this.isMuted) {
                btn.innerHTML = '<i class="fa-solid fa-volume-xmark text-slate-500"></i>';
                btn.setAttribute('title', 'Tactical Audio: MUTED (Click to Enable)');
                btn.classList.add('opacity-60');
            } else {
                btn.innerHTML = '<i class="fa-solid fa-volume-high text-emerald-400"></i>';
                btn.setAttribute('title', 'Tactical Audio: ACTIVE (Click to Mute)');
                btn.classList.remove('opacity-60');
            }
        });
    }

    // Authentic Walkie-Talkie Radio Squelch Burst
    playSquelch() {
        if (this.isMuted) return;
        try {
            this.initCtx();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            
            // Noise buffer for radio burst
            const bufferSize = this.ctx.sampleRate * 0.08;
            const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                data[i] = Math.random() * 2 - 1;
            }

            const noise = this.ctx.createBufferSource();
            noise.buffer = buffer;

            // Bandpass filter to sound like VHF/HF radio
            const filter = this.ctx.createBiquadFilter();
            filter.type = 'bandpass';
            filter.frequency.setValueAtTime(1400, now);
            filter.Q.setValueAtTime(3.5, now);

            const gain = this.ctx.createGain();
            gain.gain.setValueAtTime(0.12, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

            noise.connect(filter);
            filter.connect(gain);
            gain.connect(this.ctx.destination);
            noise.start(now);

            // Sub-click
            const osc = this.ctx.createOscillator();
            const oscGain = this.ctx.createGain();
            osc.frequency.setValueAtTime(520, now);
            osc.frequency.exponentialRampToValueAtTime(120, now + 0.04);
            oscGain.gain.setValueAtTime(0.15, now);
            oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
            osc.connect(oscGain);
            oscGain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.04);
        } catch (e) {}
    }

    // High-Tech Sonar / Radar Ping
    playSonar() {
        if (this.isMuted) return;
        try {
            this.initCtx();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(980, now);
            osc.frequency.exponentialRampToValueAtTime(1450, now + 0.15);

            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.35);
        } catch (e) {}
    }

    // Tactical Alert Alarm
    playAlert() {
        if (this.isMuted) return;
        try {
            this.initCtx();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            [0, 0.14].forEach(offset => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(880, now + offset);
                gain.gain.setValueAtTime(0.18, now + offset);
                gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.1);
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.start(now + offset);
                osc.stop(now + offset + 0.1);
            });
        } catch (e) {}
    }

    // Tactical Dispatch Confirmation Tone
    playConfirm() {
        if (this.isMuted) return;
        try {
            this.initCtx();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            const freqs = [659.25, 880.0, 1174.66]; // E5, A5, D6
            freqs.forEach((f, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(f, now + idx * 0.07);
                gain.gain.setValueAtTime(0.12, now + idx * 0.07);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.07 + 0.18);
                osc.connect(gain);
                gain.connect(this.ctx.destination);
                osc.start(now + idx * 0.07);
                osc.stop(now + idx * 0.07 + 0.18);
            });
        } catch (e) {}
    }

    // Audible Civil Defense Siren Synthesizer
    playSiren(durationSeconds = 4) {
        if (this.isMuted) return;
        try {
            this.initCtx();
            if (!this.ctx) return;
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sawtooth';
            // Undulating siren frequency wave
            for (let t = 0; t < durationSeconds; t += 1.2) {
                osc.frequency.setValueAtTime(440, now + t);
                osc.frequency.linearRampToValueAtTime(820, now + t + 0.6);
                osc.frequency.linearRampToValueAtTime(440, now + t + 1.2);
            }

            gain.gain.setValueAtTime(0.01, now);
            gain.gain.linearRampToValueAtTime(0.2, now + 0.3);
            gain.gain.setValueAtTime(0.2, now + durationSeconds - 0.5);
            gain.gain.linearRampToValueAtTime(0.001, now + durationSeconds);

            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + durationSeconds);
        } catch (e) {}
    }
}

const RakshakAudio = new TacticalAudioEngine();

// =========================================================================
// 2. UTTARAKHAND MASTER CIVIL DEFENSE SECTOR REGISTRY
// =========================================================================
const ukCities = [
    { name: "Dehradun", category: "Capital HQ / SEOC Command", lat: 30.3165, lng: 78.0322, elevation: 450, slope: 5, soil: "Clay Loam / Stable", status: "SAFE", basePrecip: 5, population: 850000, riverBasin: "Song & Rispana", helipad: "Sahastradhara (Active)", sdrfBase: "Jolly Grant 1st Bn" },
    { name: "Kedarnath", category: "High Hazard Pilgrimage", lat: 30.7352, lng: 79.0669, elevation: 3583, slope: 48, soil: "Glacial Till / Saturated", status: "CRITICAL", basePrecip: 45, population: 14000, riverBasin: "Mandakini Valley", helipad: "Kedarnath Temple Helipad", sdrfBase: "Lincheli Forward Post" },
    { name: "Badrinath", category: "High Hazard Pilgrimage", lat: 30.7433, lng: 79.4938, elevation: 3300, slope: 42, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 40, population: 12000, riverBasin: "Alaknanda Upper", helipad: "Army Badrinath Helipad", sdrfBase: "Joshimath Sector" },
    { name: "Joshimath", category: "Subsidence & Debris Axis", lat: 30.5506, lng: 79.5660, elevation: 1890, slope: 44, soil: "Morainic Unstable / Wet", status: "CRITICAL", basePrecip: 35, population: 25000, riverBasin: "Dhauliganga / Alaknanda", helipad: "Ravigram Helipad", sdrfBase: "Joshimath 3rd Post" },
    { name: "Gaurikund", category: "High Hazard Trek Gate", lat: 30.6558, lng: 79.0289, elevation: 1982, slope: 52, soil: "Rocky Colluvium / Saturated", status: "CRITICAL", basePrecip: 42, population: 8500, riverBasin: "Mandakini Gorge", helipad: "Sonprayag Helipad", sdrfBase: "Sonprayag Base" },
    { name: "Rambara", category: "Flash Surge Bottleneck", lat: 30.6975, lng: 79.0435, elevation: 2800, slope: 56, soil: "Rocky Shingle / Saturated", status: "CRITICAL", basePrecip: 50, population: 3500, riverBasin: "Mandakini Gorge", helipad: "Jungle Chatti Clearing", sdrfBase: "Gaurikund Quick Response" },
    { name: "Govindghat", category: "Valley of Flowers Gate", lat: 30.6253, lng: 79.5539, elevation: 1828, slope: 46, soil: "Rocky Slope / Wet", status: "WARNING", basePrecip: 30, population: 6000, riverBasin: "Alaknanda / Bhyundar", helipad: "Govindghat Riverside", sdrfBase: "Gauchar NDRF Axis" },
    { name: "Malari", category: "Strategic Border Axis", lat: 30.6866, lng: 79.8893, elevation: 3048, slope: 36, soil: "Scree / Permafrost", status: "WARNING", basePrecip: 20, population: 3200, riverBasin: "Dhauliganga", helipad: "ITBP Malari Strip", sdrfBase: "ITBP 8th Bn" },
    { name: "Dharchula", category: "Kali River Border Corridor", lat: 29.8519, lng: 80.5284, elevation: 940, slope: 40, soil: "Clay Slate / Wet", status: "WARNING", basePrecip: 25, population: 18000, riverBasin: "Kali River Basin", helipad: "Dharchula Stadium", sdrfBase: "Pithoragarh SDMA" },
    { name: "Munsiyari", category: "Alpine Trans-Himalaya", lat: 30.0681, lng: 80.2372, elevation: 2200, slope: 38, soil: "Forest Humus / Wet", status: "WARNING", basePrecip: 22, population: 14000, riverBasin: "Goriganga", helipad: "Munsiyari Helipad", sdrfBase: "Almora Contingent" },
    { name: "Bhatwari", category: "Bhagirathi Gorge Axis", lat: 30.8252, lng: 78.6315, elevation: 1218, slope: 45, soil: "Fractured Gneiss / Wet", status: "CRITICAL", basePrecip: 32, population: 11000, riverBasin: "Bhagirathi Valley", helipad: "Bhatwari Ground", sdrfBase: "Uttarkashi QRT" },
    { name: "Guptkashi", category: "Mandakini Valley Staging", lat: 30.5230, lng: 79.0833, elevation: 1319, slope: 35, soil: "Clay Loam / Wet", status: "WARNING", basePrecip: 20, population: 22000, riverBasin: "Mandakini Valley", helipad: "Narayankoti Helipads (8)", sdrfBase: "Guptkashi Command" },
    { name: "Sonprayag", category: "Confluence Barrier Point", lat: 30.6375, lng: 78.9950, elevation: 1829, slope: 46, soil: "Debris Slope / Saturated", status: "CRITICAL", basePrecip: 38, population: 7500, riverBasin: "Mandakini / Vasukiganga", helipad: "Sonprayag Main", sdrfBase: "SDRF Sonprayag Station" },
    { name: "Srinagar", category: "Sub-Himalayan Reservoir Hub", lat: 30.2201, lng: 78.7847, elevation: 560, slope: 16, soil: "Alluvial Terrace / Normal", status: "WATCH", basePrecip: 10, population: 45000, riverBasin: "Alaknanda Dam Basin", helipad: "Srinagar Airbase (SSB)", sdrfBase: "Srinagar SDRF Barracks" },
    { name: "Devprayag", category: "Holy Confluence (Sangam)", lat: 30.1458, lng: 78.5994, elevation: 830, slope: 35, soil: "Steep Rocky / Wet", status: "WARNING", basePrecip: 15, population: 16000, riverBasin: "Bhagirathi & Alaknanda", helipad: "Tehri Axis LZ", sdrfBase: "Rishikesh Unit" },
    { name: "Haridwar", category: "Plains Spillway & Flood Plain", lat: 29.9457, lng: 78.1642, elevation: 314, slope: 4, soil: "Alluvial / Safe", status: "SAFE", basePrecip: 2, population: 310000, riverBasin: "Ganga Downstream", helipad: "BHEL Helipad", sdrfBase: "State Police Reserve" },
    { name: "Nainital", category: "Lake Basin Slope Watch", lat: 29.3919, lng: 79.4542, elevation: 2084, slope: 34, soil: "Limestone Scree / Wet", status: "WARNING", basePrecip: 15, population: 42000, riverBasin: "Naini Catchment", helipad: "Nainital Flats LZ", sdrfBase: "Nainital Police QRT" },
    { name: "Almora", category: "Kumaon Ridge Command", lat: 29.5982, lng: 79.6644, elevation: 1642, slope: 26, soil: "Pine Forest / Normal", status: "WATCH", basePrecip: 10, population: 38000, riverBasin: "Kosi & Suyal", helipad: "Almora Cantonment", sdrfBase: "Kumaon Scouts Base" },
    { name: "Pithoragarh", category: "Border Tactical Operations", lat: 29.5829, lng: 80.2182, elevation: 1514, slope: 22, soil: "Clay Loam / Normal", status: "WATCH", basePrecip: 8, population: 58000, riverBasin: "Saryu & Kali", helipad: "Naini Saini Airport", sdrfBase: "Pithoragarh 5th Post" },
    { name: "Uttarkashi", category: "Bhagirathi Valley HQ", lat: 30.7268, lng: 78.4354, elevation: 1158, slope: 30, soil: "River Silt / Wet", status: "WATCH", basePrecip: 12, population: 35000, riverBasin: "Bhagirathi Basin", helipad: "Matli ITBP Helipad", sdrfBase: "Uttarkashi SDRF HQ" },
    { name: "Rudraprayag", category: "Valley Confluence Nexus", lat: 30.2844, lng: 78.9811, elevation: 895, slope: 36, soil: "Rocky Gorge / Wet", status: "WARNING", basePrecip: 20, population: 28000, riverBasin: "Alaknanda & Mandakini", helipad: "Gulabrai LZ", sdrfBase: "Rudraprayag Police Line" },
    { name: "Gangotri", category: "Glacial Source Pilgrimage", lat: 30.9947, lng: 78.9398, elevation: 3100, slope: 42, soil: "Granite / Snow melt", status: "WARNING", basePrecip: 20, population: 4500, riverBasin: "Bhagirathi River Head", helipad: "Harsil Military Helipad", sdrfBase: "Harsil Camp" },
    { name: "Yamunotri", category: "Steep Thermal Springs Zone", lat: 31.0140, lng: 78.4600, elevation: 3293, slope: 47, soil: "Foliated Gneiss / Wet", status: "CRITICAL", basePrecip: 25, population: 5200, riverBasin: "Yamuna Gorge", helipad: "Kharsali Helipad", sdrfBase: "Barkot Command" },
    { name: "Mussoorie", category: "Pre-Himalayan Ridge", lat: 30.4598, lng: 78.0664, elevation: 2005, slope: 32, soil: "Karstic Limestone / Wet", status: "WARNING", basePrecip: 15, population: 32000, riverBasin: "Aglar & Yamuna", helipad: "Polo Ground LZ", sdrfBase: "Dehradun QRT" },
    { name: "Auli", category: "High Altitude Slope Axis", lat: 30.5312, lng: 79.5668, elevation: 2800, slope: 37, soil: "Meadow / Wet", status: "WARNING", basePrecip: 18, population: 4000, riverBasin: "Alaknanda South", helipad: "Auli ITBP Helipad", sdrfBase: "Joshimath Post" }
];

// IN-MEMORY DATA CACHE & SYSTEM TIMERS
const cityCache = {};
let activeFluctuationTimer = null;
let leafletMap = null;
let mapMarkers = [];
let unitMarkers = [];
let activeDroneAnim = null;

// =========================================================================
// 3. SITUATIONAL BULLETIN & TICKER ENGINE
// =========================================================================
const situationBulletins = [
    "SEOC STATUS: Satcom Telemetry live on INSAT-3DR | Mandakini basin water level +0.4m/hr at Rudraprayag.",
    "BRO UPDATE: Task Force Shivalik has cleared landslide debris at NH-07 KM 48. Heavy vehicle traffic regulated.",
    "IMD DEHRADUN: Doppler radar detects active cloud cluster over Chamoli-Rudraprayag border ridges. Orange Alert maintained.",
    "FORCE TRACKER: NDRF 8th Bn stationed at Gauchar with 4 inflatable rescue boats and satellite comms.",
    "TEHRI HYDRO: Dam reservoir at 818.5m (Safe limit 830m). Controlled spillway discharge under continuous automated monitoring.",
    "CHAR DHAM LOGISTICS: Over 18,400 pilgrims safely tracked via biometric RFID transit gates across Sonprayag & Govindghat."
];

function initLiveTicker() {
    const tickerContainer = document.getElementById('live-ticker-text');
    if (!tickerContainer) return;
    let idx = 0;
    tickerContainer.textContent = situationBulletins[idx];
    setInterval(() => {
        idx = (idx + 1) % situationBulletins.length;
        tickerContainer.style.opacity = '0';
        setTimeout(() => {
            tickerContainer.textContent = situationBulletins[idx];
            tickerContainer.style.opacity = '1';
        }, 400);
    }, 8000);
}

// =========================================================================
// 4. SYSTEM LOGGER
// =========================================================================
function addLog(msg, type = 'sys') {
    const box = document.getElementById('systemLog');
    if (!box) return;

    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    let colorClass = 'text-emerald-400';
    let tag = '[SEOC-HQ]';

    if (type === 'api') { colorClass = 'text-cyan-400'; tag = '[INSAT-SAT]'; }
    if (type === 'ai') { colorClass = 'text-indigo-400'; tag = '[HYDRO-MODEL]'; }
    if (type === 'warn') { colorClass = 'text-amber-400'; tag = '[WATCH-DISPATCH]'; }
    if (type === 'crit') { colorClass = 'text-rose-400'; tag = '[FLASH-ALERT]'; }
    if (type === 'radio') { colorClass = 'text-purple-400'; tag = '[VHF-RADIO]'; }

    const line = document.createElement('div');
    line.className = `${colorClass} leading-snug break-words flex items-start gap-1.5`;
    line.innerHTML = `<span class="text-slate-500 shrink-0 font-mono text-[10px]">${time}</span> <strong class="shrink-0 text-[10px]">${tag}</strong> <span>${msg}</span>`;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

// =========================================================================
// 5. DOM INITIALIZATION
// =========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Clock with Indian Standard Time (IST)
    const clockEl = document.getElementById('clock');
    if (clockEl) {
        setInterval(() => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', { hour12: false, timeZone: 'Asia/Kolkata' });
            clockEl.innerHTML = `<span class="text-slate-400">IST</span> <span class="text-white font-bold">${timeStr}</span>`;
        }, 1000);
    }

    // 2. Audio button listener
    const audioBtns = document.querySelectorAll('.audio-toggle-btn');
    audioBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            RakshakAudio.initCtx();
            RakshakAudio.toggleMute();
        });
    });
    RakshakAudio.updateAudioIcons();

    // 3. Search Datalist setup
    const cityListEl = document.getElementById('cityList');
    if (cityListEl) {
        const sorted = [...ukCities].sort((a, b) => a.name.localeCompare(b.name));
        cityListEl.innerHTML = sorted.map(c => `<option value="${c.name}">${c.name} (${c.category})</option>`).join('');
    }

    // 4. City Search listener
    const cityInput = document.getElementById('cityInput');
    if (cityInput) {
        cityInput.addEventListener('change', (e) => {
            const matched = ukCities.find(c => c.name.toLowerCase() === e.target.value.trim().toLowerCase());
            if (matched) {
                RakshakAudio.playSonar();
                loadCityData(matched);
            }
        });
    }

    // 5. Tactical Map Init (if present)
    if (document.getElementById('map')) {
        initTacticalMap();
    }

    // 6. Live Ticker
    initLiveTicker();

    // 7. Global State Sync
    syncBackendStatus();
    setInterval(syncBackendStatus, 3000);
});

// =========================================================================
// 6. MULTI-LAYER TACTICAL LEAFLET GIS ENGINE
// =========================================================================
function initTacticalMap() {
    // Center around Garhwal & Kumaon Himalayas
    leafletMap = L.map('map', { zoomControl: false }).setView([30.35, 79.15], 8);
    L.control.zoom({ position: 'topright' }).addTo(leafletMap);

    // Layer 1: Dark Tactical Vector (100% Free, No Watermark, No API Key)
    const darkLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; SEOC Rakshak | OpenStreetMap',
        className: 'tactical-dark-tiles',
        maxZoom: 18
    });

    // Layer 2: High-Resolution Satellite
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri World Imagery | SEOC Uttarakhand',
        maxZoom: 18
    });

    // Layer 3: Topographic Contours
    const topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenTopoMap | SEOC Uttarakhand',
        maxZoom: 17
    });

    darkLayer.addTo(leafletMap);

    // Tactical Layer Control
    const baseMaps = {
        "<span class='text-xs font-bold text-slate-800'>Tactical Dark</span>": darkLayer,
        "<span class='text-xs font-bold text-slate-800'>Satellite Ortho</span>": satelliteLayer,
        "<span class='text-xs font-bold text-slate-800'>Terrain Topo</span>": topoLayer
    };
    L.control.layers(baseMaps, null, { position: 'bottomleft' }).addTo(leafletMap);

    renderMapMarkers();
    renderRescueUnits();
}

function renderMapMarkers() {
    if (!leafletMap) return;
    mapMarkers.forEach(m => leafletMap.removeLayer(m));
    mapMarkers = [];

    ukCities.forEach(city => {
        let color = '#10b981'; // Safe
        let radius = 6000;
        let pulseClass = '';

        if (city.status === 'WATCH') { color = '#facc15'; radius = 7500; }
        if (city.status === 'WARNING') { color = '#f97316'; radius = 10000; }
        if (city.status === 'CRITICAL') { color = '#ef4444'; radius = 14000; pulseClass = 'leaflet-critical-pulse'; }

        const circle = L.circle([city.lat, city.lng], {
            color: color,
            fillColor: color,
            fillOpacity: 0.35,
            radius: radius,
            weight: 2,
            className: pulseClass
        }).addTo(leafletMap);

        // Custom HTML Marker Pin
        const pinIcon = L.divIcon({
            className: 'custom-tactical-pin',
            html: `
                <div style="background:${color}; width:12px; height:12px; border-radius:50%; border:2px solid white; box-shadow:0 0 10px ${color}; cursor:pointer;"></div>
            `,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });

        const pin = L.marker([city.lat, city.lng], { icon: pinIcon }).addTo(leafletMap);

        const popupContent = `
            <div style="color:#0f172a; font-family:'Inter',sans-serif; min-width:210px; padding:2px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-weight:800; font-size:14px; text-transform:uppercase;">${city.name}</span>
                    <span style="background:${color}22; color:${color}; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px; border:1px solid ${color};">${city.status}</span>
                </div>
                <div style="font-size:11px; color:#475569; margin-bottom:6px;">${city.category}</div>
                <div style="background:#f1f5f9; padding:6px; border-radius:6px; font-size:11px; display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-bottom:8px;">
                    <div>Elev: <b>${city.elevation}m</b></div>
                    <div>Slope: <b>${city.slope}&deg;</b></div>
                    <div>River: <b>${city.riverBasin.split(' ')[0]}</b></div>
                    <div>Pop: <b>${city.population.toLocaleString()}</b></div>
                </div>
                <div style="font-size:10px; color:#64748b; margin-bottom:8px;">
                    <div>Helipad: <b>${city.helipad}</b></div>
                    <div>SDRF Post: <b>${city.sdrfBase}</b></div>
                </div>
                <button onclick="selectCityByName('${city.name}')" 
                        style="width:100%; background:#4f46e5; color:white; border:none; padding:6px; font-size:11px; font-weight:bold; border-radius:6px; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
                    <span>Target Sector Telemetry</span> &rarr;
                </button>
            </div>
        `;

        circle.bindPopup(popupContent);
        pin.bindPopup(popupContent);

        pin.on('click', () => selectCityByName(city.name));

        mapMarkers.push(circle);
        mapMarkers.push(pin);
    });
}

// Live NDRF / SDRF / IAF Field Units on the Tactical Map
function renderRescueUnits() {
    if (!leafletMap) return;
    unitMarkers.forEach(m => leafletMap.removeLayer(m));
    unitMarkers = [];

    const fieldUnitsOnMap = [
        { name: "NDRF 8th Bn Quick Response", callsign: "Vajra-1", lat: 30.2980, lng: 79.1620, type: "boat", status: "Patrolling Alaknanda" },
        { name: "SDRF Mountain Rescue Team", callsign: "Cheetah-Alpha", lat: 30.5840, lng: 79.0520, type: "truck", status: "Guptkashi-Sonprayag Road" },
        { name: "IAF Chetak Air-Ambulance", callsign: "Garuda-3", lat: 30.3420, lng: 78.0860, type: "chopper", status: "Sahastradhara LZ Standby" },
        { name: "BRO Task Force Shivalik", callsign: "Mountain-Clear", lat: 30.5600, lng: 79.5800, type: "dozer", status: "Joshimath KM-48" }
    ];

    fieldUnitsOnMap.forEach(unit => {
        let iconHtml = '<i class="fa-solid fa-truck-medical text-amber-400"></i>';
        if (unit.type === 'chopper') iconHtml = '<i class="fa-solid fa-helicopter text-cyan-400 animate-pulse"></i>';
        if (unit.type === 'boat') iconHtml = '<i class="fa-solid fa-ship text-emerald-400"></i>';
        if (unit.type === 'dozer') iconHtml = '<i class="fa-solid fa-tractor text-orange-400"></i>';

        const customUnitIcon = L.divIcon({
            className: 'field-unit-icon',
            html: `
                <div style="background:#0f172a; border:1px solid #475569; width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 12px rgba(0,0,0,0.8); cursor:pointer;">
                    ${iconHtml}
                </div>
            `,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        const m = L.marker([unit.lat, unit.lng], { icon: customUnitIcon }).addTo(leafletMap);
        m.bindPopup(`
            <div style="color:#0f172a; font-family:sans-serif; min-width:180px;">
                <div style="font-weight:bold; font-size:13px; color:#1e293b;">${unit.name}</div>
                <div style="font-size:11px; color:#6366f1; font-weight:bold;">Callsign: ${unit.callsign}</div>
                <hr style="margin:4px 0;">
                <div style="font-size:11px; color:#475569;">Mission: <b>${unit.status}</b></div>
                <div style="font-size:10px; color:#10b981; margin-top:4px;"><i class="fa-solid fa-satellite-dish"></i> SATCOM Tracking Active</div>
            </div>
        `);
        unitMarkers.push(m);
    });
}

let activeSectorName = null;

function selectCityByName(cityName) {
    const city = ukCities.find(c => c.name.toLowerCase() === cityName.toLowerCase());
    if (city) {
        if (activeSectorName === city.name) return; // Prevent duplicate concurrent trigger
        activeSectorName = city.name;
        RakshakAudio.playSonar();
        const input = document.getElementById('cityInput');
        if (input) input.value = city.name;
        loadCityData(city);
    }
}

function flyToCity(lat, lng) {
    if (leafletMap) {
        leafletMap.flyTo([lat, lng], 12, { duration: 1.6, easeLinearity: 0.25 });
    }
}

// =========================================================================
// 7. SATELLITE & SENSOR TELEMETRY SYNC
// =========================================================================
async function loadCityData(cityData) {
    const cityName = cityData.name;
    flyToCity(cityData.lat, cityData.lng);
    RakshakAudio.playSquelch();
    addLog(`Radar telemetry locked on: ${cityName} [Grid: ${cityData.lat.toFixed(4)}N, ${cityData.lng.toFixed(4)}E]`, 'sys');

    const cardContainer = document.getElementById('telemetryCards');
    const breakdownContainer = document.getElementById('riskBreakdown');
    const droneContainer = document.getElementById('droneReconPanel');

    if (cardContainer) { cardContainer.classList.remove('hidden'); cardContainer.classList.add('flex'); }
    if (breakdownContainer) { breakdownContainer.classList.remove('hidden'); breakdownContainer.classList.add('flex'); }
    if (droneContainer) {
        droneContainer.classList.remove('hidden');
        renderDroneFeed(cityData);
    }

    if (activeFluctuationTimer) {
        clearInterval(activeFluctuationTimer);
        activeFluctuationTimer = null;
    }

    // Immediately display reliable cached sector baseline to prevent UI freeze/jump
    const initialPayload = {
        ...cityData,
        currentTemp: 19.5,
        tempTomorrow: 21.0,
        precip: cityData.basePrecip
    };
    updateVisualMetrics(initialPayload);

    try {
        // 1. Check if Simulator is overriding this city
        const stateRes = await fetch('/api/state');
        const systemState = await stateRes.json();

        if (systemState.simulatedCity === cityName && systemState.telemetry) {
            addLog(`OVERRIDE DETECTED: Loading manual simulator injection for ${cityName}...`, "warn");
            const simulatedData = {
                ...cityData,
                currentTemp: 22,
                tempTomorrow: 22,
                precip: systemState.telemetry.rainfall,
                soil: systemState.telemetry.soil,
                cloudburst: systemState.telemetry.cloudburst
            };
            startFluctuationLoop(simulatedData);
            return;
        }

        // 2. Fetch live weather via backend cache to avoid client-side 429 & CORS
        addLog(`Querying SEOC weather service for ${cityName}...`, 'api');
        const weatherRes = await fetch(`/api/weather/${encodeURIComponent(cityName)}`);
        if (weatherRes.ok) {
            const wData = await weatherRes.json();
            const payload = {
                ...cityData,
                currentTemp: wData.temperature ?? 19.0,
                tempTomorrow: wData.temperature ? (wData.temperature + 1.5) : 21.0,
                precip: (wData.precipitation !== undefined && wData.precipitation > 0) ? wData.precipitation : cityData.basePrecip
            };
            cityCache[cityName] = payload;
            addLog(`Hydrological matrix computed for ${cityName}. Telemetry stable.`, 'sys');
            startFluctuationLoop(payload);
            return;
        }

    } catch (err) {
        console.warn('Telemetry fetch notice:', err);
    }

    // Reliable mountain fallback model
    cityCache[cityName] = initialPayload;
    startFluctuationLoop(initialPayload);
}

// =========================================================================
// 8. TELEMETRY FLUCTUATION & TACTICAL CALCULATION
// =========================================================================
function startFluctuationLoop(baseData) {
    if (activeFluctuationTimer) {
        clearInterval(activeFluctuationTimer);
        activeFluctuationTimer = null;
    }

    let working = JSON.parse(JSON.stringify(baseData));
    updateVisualMetrics(working);

    // Subtle, realistic telemetry heartbeat (+-0.1°C temperature variation only)
    // Precipitation & risk score remain rock-solid and stable
    activeFluctuationTimer = setInterval(() => {
        if (activeSectorName && activeSectorName !== baseData.name) {
            clearInterval(activeFluctuationTimer);
            activeFluctuationTimer = null;
            return;
        }
        const tempShift = (Math.random() - 0.5) * 0.2;
        working.tempTomorrow = (parseFloat(baseData.tempTomorrow || 20) + tempShift).toFixed(1);
        updateVisualMetrics(working);
    }, 3000);
}

function updateVisualMetrics(data) {
    const tempEl = document.getElementById('val-temp');
    const precipEl = document.getElementById('val-precip');
    const soilEl = document.getElementById('val-soil');
    const elevEl = document.getElementById('val-elev');
    const slopeEl = document.getElementById('val-slope');
    const basinEl = document.getElementById('val-basin');
    const popEl = document.getElementById('val-pop');

    if (tempEl) tempEl.textContent = `${data.tempTomorrow || 20} °C`;
    if (precipEl) precipEl.textContent = `${data.precip || data.basePrecip || 10} mm/hr`;
    if (soilEl) soilEl.textContent = data.soil || "Rocky";
    if (elevEl) elevEl.textContent = `${data.elevation}m`;
    if (slopeEl) slopeEl.textContent = `${data.slope}°`;
    if (basinEl) basinEl.textContent = data.riverBasin || "Alaknanda Basin";
    if (popEl && data.population) popEl.textContent = data.population.toLocaleString();

    // SEOC UNIFIED HYDROLOGICAL RISK MODEL
    const slopeFactor = (data.slope || 25) * 1.1;
    const elevFactor = Math.min(30, (data.elevation || 1500) / 120);
    let baseRisk = slopeFactor + elevFactor;

    const precipVal = parseFloat(data.precip || data.basePrecip || 10);
    let weatherRisk = Math.min(45, precipVal * 1.1);

    if (data.soil && data.soil.includes('Wet')) weatherRisk += 8;
    if (data.soil && data.soil.includes('Saturated')) weatherRisk += 14;
    if (data.cloudburst) weatherRisk += 25;

    const totalScore = Math.min(100, Math.max(5, Math.round(baseRisk + weatherRisk)));

    const logTerrain = document.getElementById('log-terrain');
    const logWeather = document.getElementById('log-weather');
    const logTotal = document.getElementById('log-total');
    const riskBar = document.getElementById('riskBar');

    if (logTerrain) logTerrain.textContent = `${Math.round(baseRisk)} pts`;
    if (logWeather) logWeather.textContent = `+${Math.round(weatherRisk)} pts`;
    if (logTotal) logTotal.textContent = `${totalScore} / 100`;

    if (riskBar) {
        riskBar.style.width = `${totalScore}%`;
        if (totalScore > 75) {
            riskBar.className = 'bg-rose-500 h-1.5 rounded-full transition-all duration-700 shadow-[0_0_12px_rgba(244,63,94,0.8)]';
        } else if (totalScore > 50) {
            riskBar.className = 'bg-amber-500 h-1.5 rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(245,158,11,0.6)]';
        } else if (totalScore > 25) {
            riskBar.className = 'bg-yellow-400 h-1.5 rounded-full transition-all duration-700';
        } else {
            riskBar.className = 'bg-emerald-500 h-1.5 rounded-full transition-all duration-700';
        }
    }

    // Status Banner
    const banner = document.getElementById('statusBanner');
    if (banner) {
        banner.className = 'p-3 rounded-xl text-center text-xs font-bold tracking-wider uppercase transition-all duration-300 border ';
        if (totalScore > 75) {
            banner.textContent = `CRITICAL ALERT: IMMEDIATE EVACUATION FOR ${data.name.toUpperCase()}`;
            banner.classList.add('bg-rose-950/80', 'border-rose-500', 'text-rose-300', 'animate-pulse');
        } else if (totalScore > 50) {
            banner.textContent = `WARNING: ELEVATED FLASH FLOOD HAZARD IN ${data.name.toUpperCase()}`;
            banner.classList.add('bg-amber-950/80', 'border-amber-500', 'text-amber-300');
        } else if (totalScore > 25) {
            banner.textContent = `WATCH: MONITORING UPPER BASIN IN ${data.name.toUpperCase()}`;
            banner.classList.add('bg-yellow-950/80', 'border-yellow-500', 'text-yellow-300');
        } else {
            banner.textContent = `ALL CLEAR: ${data.name.toUpperCase()} BASIN SAFE & NOMINAL`;
            banner.classList.add('bg-emerald-950/80', 'border-emerald-500', 'text-emerald-300');
        }
    }
}

// =========================================================================
// 9. SIMULATED DRONE RECON VIEWPORT (UAV Infrared HUD)
// =========================================================================
function renderDroneFeed(cityData) {
    const canvas = document.getElementById('droneCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (activeDroneAnim) cancelAnimationFrame(activeDroneAnim);

    let frame = 0;
    function drawHUD() {
        frame++;
        const w = canvas.width;
        const h = canvas.height;

        // Dark thermal canvas
        ctx.fillStyle = '#05101a';
        ctx.fillRect(0, 0, w, h);

        // Simulated thermal terrain mesh
        ctx.strokeStyle = 'rgba(34, 197, 94, 0.2)';
        ctx.lineWidth = 1;
        const gridGap = 24;
        const offset = (frame * 0.4) % gridGap;

        for (let x = 0; x < w; x += gridGap) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
        }
        for (let y = offset; y < h; y += gridGap) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Center Crosshair
        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 1.5;
        const cx = w / 2;
        const cy = h / 2;

        ctx.beginPath();
        ctx.arc(cx, cy, 28, 0, Math.PI * 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(cx - 40, cy); ctx.lineTo(cx - 15, cy);
        ctx.moveTo(cx + 15, cy); ctx.lineTo(cx + 40, cy);
        ctx.moveTo(cx, cy - 40); ctx.lineTo(cx, cy - 15);
        ctx.moveTo(cx, cy + 15); ctx.lineTo(cx, cy + 40);
        ctx.stroke();

        // Corner brackets
        const bSize = 14;
        ctx.beginPath();
        ctx.moveTo(10, 10 + bSize); ctx.lineTo(10, 10); ctx.lineTo(10 + bSize, 10);
        ctx.moveTo(w - 10, 10 + bSize); ctx.lineTo(w - 10, 10); ctx.lineTo(w - 10 - bSize, 10);
        ctx.moveTo(10, h - 10 - bSize); ctx.lineTo(10, h - 10); ctx.lineTo(10 + bSize, h - 10);
        ctx.moveTo(w - 10, h - 10 - bSize); ctx.lineTo(w - 10, h - 10); ctx.lineTo(w - 10 - bSize, h - 10);
        ctx.stroke();

        // Telemetry Text
        ctx.fillStyle = '#22c55e';
        ctx.font = '10px monospace';
        ctx.fillText(`UAV: DRONE-ALPHA // IR-THERMAL`, 16, 24);
        ctx.fillText(`SECTOR: ${cityData.name.toUpperCase()}`, 16, 38);
        ctx.fillText(`ALT: ${(cityData.elevation + 240)}m AGL`, 16, 52);
        ctx.fillText(`ZOOM: 4.8X // GIMBAL: -42°`, w - 145, 24);
        ctx.fillText(`BATT: 84% // LINK: 5.8 GHz`, w - 145, 38);
        ctx.fillText(`REC: [LIVE FEED]`, w - 145, 52);

        activeDroneAnim = requestAnimationFrame(drawHUD);
    }
    drawHUD();
}

// =========================================================================
// 10. BACKEND STATE SYNC & SOS TRIAGE
// =========================================================================
async function syncBackendStatus() {
    try {
        const timestamp = new Date().getTime();
        const res = await fetch(`/api/state?t=${timestamp}`, { cache: 'no-store' });
        const state = await res.json();
        
        // 1. Global Status Bar
        const globalStatus = document.getElementById('global-status');
        if (globalStatus) {
            const level = state.risk ? state.risk.level : 'SAFE';
            if (level === 'CRITICAL') {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping mr-2 inline-block"></span> CRITICAL: EVACUATION DISPATCH ACTIVE`;
                globalStatus.className = 'text-rose-400 font-bold flex items-center text-xs md:text-sm';
            } else if (level === 'WARNING' || level === 'HIGH') {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-amber-500 mr-2 inline-block"></span> WARNING: BASIN WATCH LEVEL 2`;
                globalStatus.className = 'text-amber-400 font-bold flex items-center text-xs md:text-sm';
            } else {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2 inline-block"></span> SEOC NOMINAL &bull; SATCOM UPLINK ONLINE`;
                globalStatus.className = 'text-emerald-400 font-bold flex items-center text-xs md:text-sm';
            }
        }

        // 2. Render Citizen SOS Signals (if SOS container exists)
        renderLiveSOSList(state.sosSignals || state.activeSOS);

        // 3. Render River Basins (if River container exists)
        renderRiverBasins(state.riverBasins);

    } catch (e) {
        // Fail silently if offline
    }
}

function renderRiverBasins(basins) {
    const container = document.getElementById('river-basins-grid');
    if (!container || !basins) return;

    container.innerHTML = basins.map(b => {
        const curr = parseFloat(b.current_level ?? b.currentLevel ?? 0);
        const dang = parseFloat(b.danger_level ?? b.dangerLevel ?? 100);
        const percent = Math.min(100, Math.round((curr / dang) * 100));
        const status = b.status || 'SAFE';
        const trend = b.trend || 'Steady';

        let badgeColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
        let barColor = 'bg-emerald-500';
        if (status === 'WARNING') {
            badgeColor = 'text-amber-400 bg-amber-500/10 border-amber-500/30';
            barColor = 'bg-amber-500';
        } else if (status === 'CRITICAL' || status === 'DANGER') {
            badgeColor = 'text-rose-400 bg-rose-500/10 border-rose-500/30';
            barColor = 'bg-rose-500';
        }

        return `
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <span class="text-xs font-bold text-white block">${b.river}</span>
                        <span class="text-[10px] text-slate-400">Danger Mark: ${dang}m</span>
                    </div>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded border ${badgeColor}">${status}</span>
                </div>
                <div class="mt-2">
                    <div class="flex justify-between text-xs font-mono mb-1">
                        <span class="text-white font-bold">${curr.toFixed(1)} m</span>
                        <span class="text-slate-400">${trend}</span>
                    </div>
                    <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div class="${barColor} h-full" style="width: ${percent}%"></div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderLiveSOSList(sosSignals) {
    const container = document.getElementById('sos-incident-list');
    if (!container || !sosSignals) return;

    if (sosSignals.length === 0) {
        container.innerHTML = `
            <div class="text-center py-6 text-slate-500 text-xs">
                <i class="fa-solid fa-check-circle text-2xl mb-2 text-emerald-500/40"></i>
                <p>No active civilian distress signals pending triage.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = sosSignals.map(sos => {
        const caller = sos.caller_name ?? sos.callerName ?? 'Civilian Caller';
        const loc = sos.location_name ?? sos.locationName ?? 'Sector Point';
        const assigned = sos.assigned_unit ?? sos.assignedUnit ?? 'Unassigned';
        const timeVal = sos.time ?? (sos.created_at ? sos.created_at.split('T')[1].slice(0, 5) : 'Recent');
        const phone = sos.phone || '1077';

        let statusBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
        if (sos.status === 'DISPATCHED') statusBadge = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
        if (sos.status === 'EN ROUTE') statusBadge = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
        if (sos.status === 'CLEARED' || sos.status === 'RESOLVED') statusBadge = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';

        return `
            <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/90 hover:border-slate-700 transition flex flex-col gap-2.5">
                <div class="flex justify-between items-start">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-white text-xs">${caller}</span>
                            <span class="text-[10px] font-mono text-slate-400">${timeVal}</span>
                        </div>
                        <div class="text-[11px] text-indigo-400 font-medium mt-0.5">
                            <i class="fa-solid fa-location-dot mr-1"></i> ${loc}
                        </div>
                    </div>
                    <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${statusBadge}">${sos.status}</span>
                </div>
                <p class="text-xs text-slate-300 bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 leading-relaxed">
                    ${sos.details}
                </p>
                <div class="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
                    <span class="text-slate-400">Assigned: <b class="text-slate-200">${assigned}</b></span>
                    <div class="flex gap-2">
                        ${sos.status === 'PENDING' ? `
                            <button onclick="dispatchRescueTeam('${sos.id}', 'SDRF High Altitude Unit')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-[10px] shadow transition">
                                <i class="fa-solid fa-person-running mr-1"></i> Deploy Team
                            </button>
                        ` : `
                            <button onclick="resolveDistressCall('${sos.id}')" class="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg font-bold text-[10px] transition">
                                <i class="fa-solid fa-check mr-1"></i> Mark Cleared
                            </button>
                        `}
                        <a href="tel:${phone}" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[10px] transition">
                            <i class="fa-solid fa-phone mr-1"></i> Call Back
                        </a>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Interactive Dispatch Actions
async function dispatchRescueTeam(sosId, teamName) {
    RakshakAudio.playConfirm();
    try {
        const resp = await fetch('/api/sos/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: sosId, status: 'DISPATCHED', assigned_unit: teamName })
        });
        if (!resp.ok) throw new Error(await resp.text());
        addLog(`COMMAND DISPATCH: ${teamName} assigned to ${sosId}. Mission order relayed via SATCOM.`, 'warn');
        syncBackendStatus();
    } catch (e) { console.error('dispatchRescueTeam error:', e); }
}

async function resolveDistressCall(sosId) {
    RakshakAudio.playConfirm();
    try {
        const resp = await fetch('/api/sos/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: sosId, status: 'CLEARED', assigned_unit: 'Mission Accomplished' })
        });
        if (!resp.ok) throw new Error(await resp.text());
        addLog(`MISSION CLEARED: Civilians under ${sosId} confirmed safe at forward relief base.`, 'sys');
        syncBackendStatus();
    } catch (e) { console.error('resolveDistressCall error:', e); }
}

// Geolocation SOS Sender
function sendSOS() {
    RakshakAudio.playAlert();
    if (!navigator.geolocation) {
        alert('Geolocation services not available on this device.');
        return;
    }

    addLog('Acquiring high-precision GPS coordinates for emergency civilian broadcast...', 'crit');
    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            const res = await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude,
                    caller_name: 'Field Mobile Operator',
                    location_name: `GPS Lat ${pos.coords.latitude.toFixed(4)}, Lng ${pos.coords.longitude.toFixed(4)}`,
                    details: 'Immediate emergency rescue requested from active field mobile terminal.'
                })
            });
            const data = await res.json();
            RakshakAudio.playConfirm();
            addLog(`BEACON BROADCAST: SOS ${data.sos_id} logged. Nearest unit: ${data.assigned_unit} (ETA ${data.eta_minutes} min).`, 'sys');
            alert(`SOS ${data.sos_id} transmitted! ${data.assigned_unit} dispatched — ETA ${data.eta_minutes} minutes.`);
            syncBackendStatus();
        } catch (err) {
            alert('Could not relay beacon to server.');
        }
    }, () => {
        // Fallback simulated SOS for testing (geolocation denied)
        fetch('/api/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: 30.7352,
                lng: 79.0669,
                caller_name: 'Kedarnath Valley Pilgrim Group (6)',
                location_name: 'Kedarnath Base Camp Post',
                details: 'Heavy snowmelt runoff cut off river crossing. 6 civilians stranded.'
            })
        }).then(r => r.json()).then(data => {
            RakshakAudio.playConfirm();
            addLog(`SIMULATION SOS ${data.sos_id}: Nearest unit ${data.assigned_unit} assigned, ETA ${data.eta_minutes} min.`, 'sys');
            alert(`Simulation SOS sent! ${data.assigned_unit} dispatched — ETA ${data.eta_minutes} minutes.`);
            syncBackendStatus();
        }).catch(err => console.error('SOS fallback error:', err));
    });
}