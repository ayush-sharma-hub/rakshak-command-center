// ==========================================
// RAKSHAK CORE ENGINE & UK DISASTER REGISTRY
// ==========================================

const ukCities = [
    { name: "Dehradun", category: "Most Populated Capital", lat: 30.3165, lng: 78.0322, elevation: 450, slope: 5, soil: "Clay Loam / Normal", status: "SAFE", basePrecip: 5 },
    { name: "Kedarnath", category: "High Risk Zone", lat: 30.7352, lng: 79.0669, elevation: 3583, slope: 45, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 45 },
    { name: "Badrinath", category: "High Risk Zone", lat: 30.7433, lng: 79.4938, elevation: 3300, slope: 40, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 40 },
    { name: "Joshimath", category: "High Risk Zone", lat: 30.5506, lng: 79.5660, elevation: 1890, slope: 42, soil: "Unstable / Wet", status: "CRITICAL", basePrecip: 35 },
    { name: "Gaurikund", category: "High Risk Zone", lat: 30.6558, lng: 79.0289, elevation: 1982, slope: 50, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 42 },
    { name: "Rambara", category: "High Risk Zone", lat: 30.6975, lng: 79.0435, elevation: 2800, slope: 55, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 50 },
    { name: "Govindghat", category: "High Risk Zone", lat: 30.6253, lng: 79.5539, elevation: 1828, slope: 45, soil: "Rocky / Wet", status: "WARNING", basePrecip: 30 },
    { name: "Malari", category: "High Risk Zone", lat: 30.6866, lng: 79.8893, elevation: 3048, slope: 35, soil: "Rocky / Normal", status: "WARNING", basePrecip: 20 },
    { name: "Dharchula", category: "High Risk Zone", lat: 29.8519, lng: 80.5284, elevation: 940, slope: 38, soil: "Clay / Wet", status: "WARNING", basePrecip: 25 },
    { name: "Munsiyari", category: "High Risk Zone", lat: 30.0681, lng: 80.2372, elevation: 2200, slope: 35, soil: "Forest / Wet", status: "WARNING", basePrecip: 22 },
    { name: "Bhatwari", category: "High Risk Zone", lat: 30.8252, lng: 78.6315, elevation: 1218, slope: 42, soil: "Rocky / Wet", status: "CRITICAL", basePrecip: 32 },
    { name: "Guptkashi", category: "High Risk Zone", lat: 30.5230, lng: 79.0833, elevation: 1319, slope: 35, soil: "Clay Loam / Wet", status: "WARNING", basePrecip: 20 },
    { name: "Sonprayag", category: "High Risk Zone", lat: 30.6375, lng: 78.9950, elevation: 1829, slope: 45, soil: "Rocky / Saturated", status: "CRITICAL", basePrecip: 38 },
    { name: "Srinagar", category: "High Risk Zone", lat: 30.2201, lng: 78.7847, elevation: 560, slope: 15, soil: "Alluvial / Normal", status: "WATCH", basePrecip: 10 },
    { name: "Devprayag", category: "High Risk Zone", lat: 30.1458, lng: 78.5994, elevation: 830, slope: 35, soil: "Rocky / Wet", status: "WARNING", basePrecip: 15 },
    { name: "Roorkee", category: "Economic Hub", lat: 29.8543, lng: 77.8880, elevation: 268, slope: 2, soil: "Alluvial / Normal", status: "SAFE", basePrecip: 0 },
    { name: "Haridwar", category: "District Main City", lat: 29.9457, lng: 78.1642, elevation: 314, slope: 5, soil: "Alluvial / Normal", status: "SAFE", basePrecip: 2 },
    { name: "Haldwani", category: "District Main City", lat: 29.2193, lng: 79.5127, elevation: 424, slope: 8, soil: "Alluvial / Normal", status: "SAFE", basePrecip: 5 },
    { name: "Nainital", category: "District Main City", lat: 29.3919, lng: 79.4542, elevation: 2084, slope: 30, soil: "Forest / Wet", status: "WARNING", basePrecip: 15 },
    { name: "Almora", category: "District Main City", lat: 29.5982, lng: 79.6644, elevation: 1642, slope: 25, soil: "Forest / Normal", status: "WATCH", basePrecip: 10 },
    { name: "Pithoragarh", category: "District Main City", lat: 29.5829, lng: 80.2182, elevation: 1514, slope: 20, soil: "Clay / Normal", status: "WATCH", basePrecip: 8 },
    { name: "Uttarkashi", category: "District Main City", lat: 30.7268, lng: 78.4354, elevation: 1158, slope: 28, soil: "Rocky Loam / Wet", status: "WATCH", basePrecip: 12 },
    { name: "Rudraprayag", category: "District Main City", lat: 30.2844, lng: 78.9811, elevation: 895, slope: 35, soil: "Rocky / Wet", status: "WARNING", basePrecip: 20 },
    { name: "Mana", category: "Remote Border", lat: 30.7725, lng: 79.4939, elevation: 3200, slope: 30, soil: "Rocky / Dry", status: "WATCH", basePrecip: 5 },
    { name: "Milam", category: "Remote Border", lat: 30.4358, lng: 80.1558, elevation: 3438, slope: 35, soil: "Rocky / Snow", status: "WARNING", basePrecip: 10 },
    { name: "Gangotri", category: "High Altitude Hub", lat: 30.9947, lng: 78.9398, elevation: 3100, slope: 40, soil: "Rocky / Snow", status: "WARNING", basePrecip: 20 },
    { name: "Yamunotri", category: "High Altitude Hub", lat: 31.0140, lng: 78.4600, elevation: 3293, slope: 45, soil: "Rocky / Wet", status: "CRITICAL", basePrecip: 25 },
    { name: "Mussoorie", category: "Tourist Hub", lat: 30.4598, lng: 78.0664, elevation: 2005, slope: 30, soil: "Forest / Wet", status: "WARNING", basePrecip: 15 },
    { name: "Auli", category: "Tourist Hub", lat: 30.5312, lng: 79.5668, elevation: 2800, slope: 35, soil: "Rocky / Snow", status: "WARNING", basePrecip: 18 }
];

// IN-MEMORY CACHE & TIMERS
const cityCache = {};
let activeFluctuationTimer = null;
let leafletMap = null;
let mapMarkers = [];

// ==========================================
// SYSTEM LOGGER (Visibility Console)
// ==========================================
function addLog(msg, type = 'sys') {
    const box = document.getElementById('systemLog');
    if (!box) return;

    const time = new Date().toLocaleTimeString([], { hour12: false });
    let colorClass = 'text-green-400';
    let tag = '[SYSTEM]';

    if (type === 'api') { colorClass = 'text-cyan-400'; tag = '[API-FETCH]'; }
    if (type === 'ai') { colorClass = 'text-indigo-400'; tag = '[AI-ENGINE]'; }
    if (type === 'warn') { colorClass = 'text-amber-400'; tag = '[CACHE]'; }
    if (type === 'crit') { colorClass = 'text-rose-400'; tag = '[ERROR]'; }

    const line = document.createElement('div');
    line.className = `${colorClass} leading-snug break-words`;
    line.innerHTML = `<span class="text-slate-500">${time}</span> <strong>${tag}</strong> ${msg}`;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

// ==========================================
// DOM INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Clock
    const clockEl = document.getElementById('clock');
    if (clockEl) {
        setInterval(() => { clockEl.textContent = new Date().toLocaleTimeString('en-US', { hour12: false }); }, 1000);
    }

    // 2. Setup Datalist Search
    const cityListEl = document.getElementById('cityList');
    if (cityListEl) {
        const sorted = [...ukCities].sort((a, b) => a.name.localeCompare(b.name));
        cityListEl.innerHTML = sorted.map(c => `<option value="${c.name}">${c.name} (${c.category})</option>`).join('');
    }

    // 3. Search Input Listeners
    const cityInput = document.getElementById('cityInput');
    if (cityInput) {
        cityInput.addEventListener('change', (e) => {
            const matched = ukCities.find(c => c.name.toLowerCase() === e.target.value.trim().toLowerCase());
            if (matched) loadCityData(matched);
        });
    }

    // 4. Map Init (Only runs if map div exists)
    if (document.getElementById('map')) {
        initTacticalMap();
    }

    // 5. Global Status Sync
    syncBackendStatus();
    setInterval(syncBackendStatus, 4000);
});

// ==========================================
// TACTICAL LEAFLET MAP ENGINE
// ==========================================
function initTacticalMap() {
    leafletMap = L.map('map', { zoomControl: false }).setView([30.15, 79.20], 8);
    L.control.zoom({ position: 'topright' }).addTo(leafletMap);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; Project Rakshak DSS | OpenStreetMap',
        maxZoom: 18
    }).addTo(leafletMap);

    renderMapMarkers();
}

function renderMapMarkers() {
    if (!leafletMap) return;
    mapMarkers.forEach(m => leafletMap.removeLayer(m));
    mapMarkers = [];

    ukCities.forEach(city => {
        let color = '#10b981'; // Safe
        let radius = 6000;

        if (city.status === 'WATCH') { color = '#facc15'; radius = 7500; }
        if (city.status === 'WARNING') { color = '#f97316'; radius = 9500; }
        if (city.status === 'CRITICAL') { color = '#ef4444'; radius = 13000; }

        const circle = L.circle([city.lat, city.lng], {
            color: color, fillColor: color, fillOpacity: 0.35, radius: radius, weight: 2
        }).addTo(leafletMap);

        circle.bindPopup(`
            <div style="color:#0f172a; font-family:sans-serif; min-width:140px;">
                <div style="font-weight:bold; font-size:14px;">${city.name}</div>
                <div style="font-size:11px; color:#475569;">${city.category}</div>
                <hr style="margin:4px 0;">
                <div style="font-size:12px;">Elev: <b>${city.elevation}m</b> | Slope: <b>${city.slope}&deg;</b></div>
            </div>
        `);

        circle.on('click', () => {
            const input = document.getElementById('cityInput');
            if (input) input.value = city.name;
            loadCityData(city);
        });

        mapMarkers.push(circle);
    });
}

function flyToCity(lat, lng) {
    if (leafletMap) {
        leafletMap.flyTo([lat, lng], 12, { duration: 1.8, easeLinearity: 0.25 });
    }
}

// ==========================================
// UNIFIED ENGINE & API FETCH
// ==========================================
async function loadCityData(cityData) {
    const cityName = cityData.name;
    flyToCity(cityData.lat, cityData.lng);
    addLog(`Target vector focused on: ${cityName} [${cityData.lat.toFixed(4)}, ${cityData.lng.toFixed(4)}]`, 'sys');

    const cardContainer = document.getElementById('telemetryCards');
    const breakdownContainer = document.getElementById('riskBreakdown');
    if (cardContainer) { cardContainer.classList.remove('hidden'); cardContainer.classList.add('flex'); }
    if (breakdownContainer) { breakdownContainer.classList.remove('hidden'); breakdownContainer.classList.add('flex'); }

    if (activeFluctuationTimer) clearInterval(activeFluctuationTimer);

    try {
        // 1. Check if Simulator is overriding this city
        const stateRes = await fetch('/api/state');
        const systemState = await stateRes.json();

        if (systemState.simulatedCity === cityName) {
            addLog(`OVERRIDE DETECTED: Loading manual simulator injection for ${cityName}...`, "warn");
            const simulatedData = {
                ...cityData,
                currentTemp: 24, tempTomorrow: 24,
                precip: systemState.telemetry.rainfall,
                soil: systemState.telemetry.soil,
                cloudburst: systemState.telemetry.cloudburst
            };
            startFluctuationLoop(simulatedData);
            return;
        }

        // 2. Check Local Cache to save API limits
        if (cityCache[cityName]) {
            addLog(`Cache Hit: Loaded ${cityName} telemetry. Saved satellite API request.`, 'warn');
            startFluctuationLoop(cityCache[cityName]);
            return;
        }

        // 3. Normal Real-world API Fetch
        addLog(`Contacting Open-Meteo Satellite for coordinates...`, 'api');
        const tempEl = document.getElementById('val-temp');
        if (tempEl) tempEl.innerHTML = '<span class="text-xs text-slate-400 animate-pulse">Syncing...</span>';

        const apiUrl = `https://api.open-meteo.com/v1/forecast?latitude=${cityData.lat}&longitude=${cityData.lng}&current=temperature_2m,precipitation&daily=temperature_2m_max&timezone=auto`;
        const response = await fetch(apiUrl);
        const weatherData = await response.json();

        addLog(`Telemetry packet received. Parsing meteorological data...`, 'api');

        const liveTempTomorrow = (weatherData.daily && weatherData.daily.temperature_2m_max) ? weatherData.daily.temperature_2m_max[1] : 24.0;
        const liveRadarPrecip = (weatherData.current && weatherData.current.precipitation) !== undefined ? weatherData.current.precipitation : 0;

        const payload = {
            ...cityData,
            currentTemp: weatherData.current ? weatherData.current.temperature_2m : 22,
            tempTomorrow: liveTempTomorrow,
            precip: liveRadarPrecip > 0 ? liveRadarPrecip : cityData.basePrecip
        };

        cityCache[cityName] = payload;
        addLog(`Evaluating Unified AI Risk Equation...`, 'ai');
        startFluctuationLoop(payload);

    } catch (err) {
        addLog(`Remote telemetry link timeout. Deploying default fallback model.`, 'crit');
        const fallback = { ...cityData, currentTemp: 21, tempTomorrow: 23.5, precip: cityData.basePrecip };
        cityCache[cityName] = fallback;
        startFluctuationLoop(fallback);
    }
}

// ==========================================
// FLUCTUATION LOOP & DYNAMIC FORMULA
// ==========================================
function startFluctuationLoop(baseData) {
    let working = JSON.parse(JSON.stringify(baseData));
    updateVisualMetrics(working);

    activeFluctuationTimer = setInterval(() => {
        const tempShift = (Math.random() - 0.5) * 0.3;
        working.tempTomorrow = (parseFloat(baseData.tempTomorrow) + tempShift).toFixed(1);

        const precipShift = (Math.random() - 0.5) * 1.8;
        working.precip = Math.max(0, (parseFloat(baseData.precip) + precipShift)).toFixed(1);

        updateVisualMetrics(working);
    }, 2500);
}

function updateVisualMetrics(data) {
    // 1. Telemetry Values
    const tempEl = document.getElementById('val-temp');
    const precipEl = document.getElementById('val-precip');
    const soilEl = document.getElementById('val-soil');
    const elevEl = document.getElementById('val-elev');
    const slopeEl = document.getElementById('val-slope');

    if (tempEl) tempEl.textContent = `${data.tempTomorrow} °C`;
    if (precipEl) precipEl.textContent = `${data.precip} mm/hr`;
    if (soilEl) soilEl.textContent = data.soil;
    if (elevEl) elevEl.textContent = data.elevation;
    if (slopeEl) slopeEl.textContent = data.slope;

    // 2. UNIFIED MATH ENGINE
    let baseRisk = (data.slope * 1.2) + (data.elevation / 110);
    let weatherRisk = (data.precip * 1.4);
    
    if (data.soil && data.soil.includes('Wet')) weatherRisk += 15;
    if (data.soil && data.soil.includes('Saturated')) weatherRisk += 25;
    if (data.cloudburst) weatherRisk += 30;

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
        if (totalScore > 75) riskBar.className = 'bg-rose-500 h-1.5 rounded-full transition-all duration-700 shadow-[0_0_10px_rgba(244,63,94,0.6)]';
        else if (totalScore > 50) riskBar.className = 'bg-amber-500 h-1.5 rounded-full transition-all duration-700';
        else if (totalScore > 25) riskBar.className = 'bg-yellow-400 h-1.5 rounded-full transition-all duration-700';
        else riskBar.className = 'bg-emerald-500 h-1.5 rounded-full transition-all duration-700';
    }

    // 3. Status Banner
    const banner = document.getElementById('statusBanner');
    if (banner) {
        banner.className = 'p-3 rounded-lg text-center text-xs md:text-sm font-bold tracking-wider uppercase transition-colors duration-300 border ';
        if (totalScore > 75) {
            banner.textContent = `CRITICAL: EVACUATION ADVISORY FOR ${data.name.toUpperCase()}`;
            banner.classList.add('bg-rose-950/80', 'border-rose-500', 'text-rose-300', 'animate-pulse');
        } else if (totalScore > 50) {
            banner.textContent = `WARNING: ELEVATED FLASH HAZARD IN ${data.name.toUpperCase()}`;
            banner.classList.add('bg-amber-950/80', 'border-amber-500', 'text-amber-300');
        } else if (totalScore > 25) {
            banner.textContent = `WATCH: MONITORING ATMOSPHERIC CELL IN ${data.name.toUpperCase()}`;
            banner.classList.add('bg-yellow-950/80', 'border-yellow-500', 'text-yellow-300');
        } else {
            banner.textContent = `SYSTEM NOMINAL: ${data.name.toUpperCase()} BASIN SAFE`;
            banner.classList.add('bg-emerald-950/80', 'border-emerald-500', 'text-emerald-300');
        }
    }
}

// ==========================================
// BACKEND STATE SYNC & SOS
// ==========================================
async function syncBackendStatus() {
    try {
        const res = await fetch('/api/state');
        const state = await res.json();
        const globalStatus = document.getElementById('global-status');
        if (globalStatus) {
            if (state.risk.level === 'CRITICAL') {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping mr-2 inline-block"></span> CRITICAL: RESPONSE MANDATE`;
                globalStatus.className = 'text-rose-400 font-bold flex items-center';
            } else if (state.risk.level === 'WARNING') {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-amber-500 mr-2 inline-block"></span> WARNING: MONITORING BASIN`;
                globalStatus.className = 'text-amber-400 font-bold flex items-center';
            } else {
                globalStatus.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2 inline-block"></span> SYSTEM NORMAL`;
                globalStatus.className = 'text-emerald-400 font-bold flex items-center';
            }
        }
    } catch (e) {
        // Silent fail if backend is offline
    }
}

function sendSOS() {
    if (!navigator.geolocation) {
        alert('Geolocation services not available on this browser.');
        return;
    }
    alert('Acquiring satellite coordinate fix for emergency broadcast...');
    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
            });
            alert('SOS Coordinates Broadcast to Central Command Room!');
        } catch (err) {
            alert('Could not relay beacon to server.');
        }
    });
}