const express = require('express');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// GLOBAL CENTRAL STATE
let systemState = {
    simulatedCity: null, // Tracks if a city is under manual simulation
    telemetry: { rainfall: 0, slope: 0, elevation: 0, tempTomorrow: 0, soil: 'Normal', network: 'Online', cloudburst: false },
    risk: { score: 0, level: 'SAFE', popAtRisk: 0, explanation: 'System Normal' },
    alerts: [],
    sosSignals: []
};

// ENDPOINTS
app.get('/api/state', (req, res) => {
    res.json(systemState);
});

app.post('/api/simulate', (req, res) => {
    const { cityName, rainfall, slope, elevation, soil, cloudburst, network, population } = req.body;

    // UNIFIED MATH ENGINE (Must match frontend exactly)
    let rainVal = parseFloat(rainfall) || 0;
    let slopeVal = parseFloat(slope) || 0;
    let elevVal = parseFloat(elevation) || 0;
    
    let baseRisk = (slopeVal * 1.2) + (elevVal / 110);
    let weatherRisk = (rainVal * 1.4);
    
    if (soil && soil.includes('Wet')) weatherRisk += 15;
    if (soil && soil.includes('Saturated')) weatherRisk += 25;
    if (cloudburst) weatherRisk += 30;

    let finalScore = Math.min(100, Math.max(5, Math.round(baseRisk + weatherRisk)));

    let level = 'SAFE';
    if (finalScore > 75) level = 'CRITICAL';
    else if (finalScore > 50) level = 'WARNING';
    else if (finalScore > 25) level = 'WATCH';

    // Update Central State
    systemState.simulatedCity = cityName;
    systemState.telemetry = { rainfall: rainVal, slope: slopeVal, elevation: elevVal, soil, cloudburst, network };
    systemState.risk = {
        score: finalScore,
        level: level,
        popAtRisk: finalScore > 50 ? Math.round(population * (finalScore/100)) : 0,
        explanation: `Simulated trigger for ${cityName}. Terrain Base: ${Math.round(baseRisk)}, Weather Factor: ${Math.round(weatherRisk)}.`
    };

    if (finalScore > 75) {
        systemState.alerts.unshift({
            id: Date.now(),
            type: 'FLOOD',
            msg: `CRITICAL SIMULATION: Evacuation threshold breached in ${cityName}.`,
            time: new Date().toLocaleTimeString(),
            zone: cityName
        });
    }

    res.json({ success: true, state: systemState });
});

app.post('/api/sos', (req, res) => {
    const { lat, lng } = req.body;
    const time = new Date().toLocaleTimeString();
    systemState.sosSignals.unshift({ lat, lng, time });
    res.json({ success: true });
});

app.listen(PORT, () => console.log(`Rakshak Server active on port ${PORT}`));