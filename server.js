const express = require('express');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// GLOBAL CENTRAL STATE (SEOC DEHRADUN REAL-TIME SYSTEM)
let systemState = {
    simulatedCity: null,
    watchCommander: {
        name: "Capt. Rajeshwar Negi",
        role: "SEOC Chief Watch Officer",
        badge: "UK-SEOC-04",
        shift: "Crisis Protocol Alpha"
    },
    telemetry: {
        rainfall: 14,
        slope: 38,
        elevation: 1982,
        tempTomorrow: 19.5,
        soil: 'Wet',
        network: 'Satellite SATCOM Active',
        cloudburst: false,
        satelliteUplink: 'INSAT-3DR (GSAT-7A Relay)',
        uplinkLatency: '42ms'
    },
    risk: {
        score: 34,
        level: 'WATCH',
        popAtRisk: 1200,
        explanation: 'Atmospheric moisture elevation in Alaknanda & Mandakini upper catchment valleys.'
    },
    riverBasins: [
        { river: "Mandakini (Rudraprayag)", currentLevel: 624.8, dangerLevel: 627.0, status: "WARNING", trend: "+0.4m/hr" },
        { river: "Alaknanda (Joshimath)", currentLevel: 1148.2, dangerLevel: 1152.5, status: "NOMINAL", trend: "+0.1m/hr" },
        { river: "Bhagirathi (Uttarkashi)", currentLevel: 1120.0, dangerLevel: 1125.0, status: "NOMINAL", trend: "Steady" },
        { river: "Tehri Dam Reservoir", currentLevel: 818.5, dangerLevel: 830.0, status: "SAFE", trend: "+0.2m/day" }
    ],
    fieldUnits: [
        { id: "NDRF-8", name: "NDRF 8th Battalion", callsign: "Vajra-1", sector: "Gauchar Base", strength: 36, status: "PRE-POSITIONED", contact: "+91-135-2710334" },
        { id: "SDRF-M1", name: "SDRF High Altitude Rescue", callsign: "Cheetah-Alpha", sector: "Guptkashi", strength: 18, status: "PATROL EN ROUTE", contact: "+91-135-2410882" },
        { id: "IAF-CH1", name: "IAF Chetak Air-Ambulance", callsign: "Garuda-3", sector: "Sahastradhara Helipad", strength: 4, status: "STANDBY", contact: "Air Control 121.5 MHz" },
        { id: "BRO-TF7", name: "BRO Task Force Shivalik", callsign: "Mountain-Clear", sector: "Joshimath-Malari Axis", strength: 24, status: "CLEARING DEBRIS", contact: "VHF Ch-08" }
    ],
    alerts: [
        {
            id: 101,
            type: 'WARNING',
            msg: 'IMD Doppler Radar: Sustained rain cells detected over Chamoli & Rudraprayag corridors.',
            time: '10 mins ago',
            zone: 'Rudraprayag Sector',
            priority: 'HIGH'
        },
        {
            id: 102,
            type: 'ADVISORY',
            msg: 'BRO Task Force reports boulder debris cleared near NH-07 KM 48. Single-lane movement restored.',
            time: '24 mins ago',
            zone: 'Joshimath Axis',
            priority: 'MEDIUM'
        },
        {
            id: 103,
            type: 'LOGISTICS',
            msg: 'SDRF forward relief shelters at Sonprayag & Govindghat stocked with 4,000 emergency ration packets.',
            time: '45 mins ago',
            zone: 'Kedarnath Basin',
            priority: 'INFO'
        }
    ],
    sosSignals: [
        {
            id: "SOS-701",
            callerName: "Pooja Dobhal & Family (4)",
            phone: "+91 98450 11204",
            lat: 30.6558,
            lng: 79.0289,
            locationName: "Gaurikund Trek KM 3.2",
            details: "Landslide mud blocking downhill trail. 4 pilgrims sheltered in tin shed, low drinking water.",
            time: "14 mins ago",
            status: "DISPATCHED",
            assignedUnit: "SDRF High Altitude Rescue"
        },
        {
            id: "SOS-702",
            callerName: "Driver Surender Singh (Bolero Taxi)",
            phone: "+91 94120 88319",
            lat: 30.5506,
            lng: 79.5660,
            locationName: "Joshimath Upper Bypass",
            details: "Tree fallen across road, vehicle axle cracked. 6 passengers safe inside vehicle.",
            time: "28 mins ago",
            status: "PENDING",
            assignedUnit: "Unassigned"
        },
        {
            id: "SOS-703",
            callerName: "Gram Pradhan - Rampur",
            phone: "+91 97561 02931",
            lat: 30.5230,
            lng: 79.0833,
            locationName: "Guptkashi Rampur Outskirts",
            details: "Local stream overflowed into 2 cattle sheds. Elderly evacuation assistance needed.",
            time: "41 mins ago",
            status: "EN ROUTE",
            assignedUnit: "District Rapid Force Unit 2"
        }
    ]
};

// ==========================================
// ENDPOINTS
// ==========================================

// 1. Central System State
app.get('/api/state', (req, res) => {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.json(systemState);
});

// 2. Field Units
app.get('/api/field-units', (req, res) => {
    res.json({ success: true, units: systemState.fieldUnits });
});

// 3. Disaster Simulation Engine
app.post('/api/simulate', (req, res) => {
    const { cityName, rainfall, slope, elevation, soil, cloudburst, network, population } = req.body;

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
    systemState.telemetry = {
        rainfall: rainVal,
        slope: slopeVal,
        elevation: elevVal,
        tempTomorrow: (18 - (elevVal/400)).toFixed(1),
        soil: soil || 'Saturated',
        cloudburst: !!cloudburst,
        network: network || 'Satellite SATCOM Emergency Mode',
        satelliteUplink: 'INSAT-3DR Telemetry Active',
        uplinkLatency: '28ms'
    };
    
    systemState.risk = {
        score: finalScore,
        level: level,
        popAtRisk: finalScore > 50 ? Math.round((population || 12000) * (finalScore / 100)) : 0,
        explanation: `Field Telemetry Alert for ${cityName}. Geomorphic slope factor: ${Math.round(baseRisk)} pts, Precipitation flux: ${Math.round(weatherRisk)} pts.`
    };

    if (finalScore > 75) {
        systemState.alerts.unshift({
            id: Date.now(),
            type: 'FLASH FLOOD',
            msg: `URGENT EVACUATION DISPATCH: Hydrological runoff model breached threshold in ${cityName} Valley basin!`,
            time: 'Just now',
            zone: cityName,
            priority: 'CRITICAL'
        });
    }

    res.json({ success: true, state: systemState });
});

// 4. Register Incoming Citizen SOS
app.post('/api/sos', (req, res) => {
    const { lat, lng, callerName, phone, locationName, details } = req.body;
    const time = 'Just now';
    const newSOS = {
        id: `SOS-${Math.floor(100 + Math.random() * 900)}`,
        callerName: callerName || 'Civilian Distress Beacon',
        phone: phone || '+91-112-RELAY',
        lat: lat || 30.7352,
        lng: lng || 79.0669,
        locationName: locationName || 'Himalayan GPS Fix',
        details: details || 'Emergency location broadcast triggered from mobile terminal.',
        time: time,
        status: 'PENDING',
        assignedUnit: 'Awaiting Command Triage'
    };
    systemState.sosSignals.unshift(newSOS);
    
    // Also push to active alerts
    systemState.alerts.unshift({
        id: Date.now(),
        type: 'CITIZEN SOS',
        msg: `INCOMING DISTRESS: ${newSOS.callerName} at ${newSOS.locationName} requests emergency assistance.`,
        time: 'Just now',
        zone: newSOS.locationName,
        priority: 'HIGH'
    });

    res.json({ success: true, sos: newSOS });
});

// 5. Triage / Update Citizen SOS Status
app.post('/api/sos/update', (req, res) => {
    const { id, status, assignedUnit } = req.body;
    const sos = systemState.sosSignals.find(s => s.id === id);
    if (sos) {
        if (status) sos.status = status;
        if (assignedUnit) sos.assignedUnit = assignedUnit;
        return res.json({ success: true, sos });
    }
    res.status(404).json({ success: false, message: 'SOS signal not found' });
});

// 6. Direct Field Unit Dispatch
app.post('/api/dispatch', (req, res) => {
    const { unitId, sector, objective } = req.body;
    const unit = systemState.fieldUnits.find(u => u.id === unitId);
    if (unit) {
        unit.status = `DEPLOYED TO ${sector.toUpperCase()}`;
        systemState.alerts.unshift({
            id: Date.now(),
            type: 'UNIT DISPATCHED',
            msg: `${unit.name} (${unit.callsign}) mobilized to ${sector} for: ${objective || 'Tactical Search & Rescue'}.`,
            time: 'Just now',
            zone: sector,
            priority: 'HIGH'
        });
        return res.json({ success: true, unit });
    }
    res.status(404).json({ success: false, message: 'Field unit not found' });
});

app.listen(PORT, () => console.log(`Project Rakshak SEOC Command Server active on port ${PORT}`));