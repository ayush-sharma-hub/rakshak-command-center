# 🏔️ Rakshak — Uttarakhand SEOC Disaster Intelligence Dashboard

> **"Rakshak" (रक्षक) means "Protector" in Hindi.**
> A real-time disaster early-warning and response coordination platform for the Uttarakhand State Emergency Operations Centre (SEOC).

---

## 🚀 Live Demo

| Service | URL |
|---|---|
| 🖥️ **Main War Room Dashboard** | http://localhost:3000 |
| 📊 **Analytics Dashboard** | http://localhost:8501 |
| 📋 **Interactive API Docs** | http://localhost:3000/api/docs |

---

## ✨ Features

### 🌐 Front-End (9 Pages)
| Page | What it does |
|---|---|
| `index.html` | USDMA Secure Login — duty shift selector, biometric auth |
| `dashboard.html` | **Live War Room** — SOS triage, river gauges, field units, incident wire |
| `map.html` | **Tactical GIS Map** — 3 base layers, rescue unit pins, UAV drone HUD |
| `simulator.html` | **Crisis Simulator** — 2013 Kedarnath, 2021 Chamoli presets, debris physics |
| `evacuation.html` | **Convoy Manager** — 4-stage SOP, fleet tracker, shelter inventory |
| `alerts.html` | **Broadcast Hub** — 4-language emergency alerts, speech synthesis |
| `assistant.html` | **VHF Radio Comms** — RF waveform visualizer, Push-to-Talk |

### 🐍 Back-End (Python FastAPI)
- **8-table SQLite database** — fully persisted, never lost on restart
- **Geo-routing engine** — Haversine distance + mountain terrain ETA, auto-assigns nearest responder to any SOS
- **Live Open-Meteo weather** — free API, no key, real precipitation data for 25 Uttarakhand cities
- **Gemini AI broadcasts** — free tier, multi-language alerts (English + Hindi + Garhwali + Kumaoni)
- **Real-time WebSocket** — live river basin updates pushed to all browser tabs every 30 seconds
- **Background sensor loop** — simulates live IoT gauge readings, auto-generates AI alerts for dangerous rivers

### 📊 Analytics Dashboard (Streamlit)
- Interactive river basin gauge charts
- Incident priority breakdown pie chart
- Live SOS signal tracker with one-click new SOS form
- Real-time risk simulator with AI analysis
- Broadcast generator with Gemini AI

---

## 🏗️ Architecture

```
rakshak-new/
├── main.py                    ← FastAPI server (port 3000)
├── streamlit_app.py           ← Analytics dashboard (port 8501)
├── start.py                   ← Convenient startup script
├── requirements.txt
├── rakshak.db                 ← SQLite database (auto-created)
├── .env.example               ← Copy to .env for Gemini key
│
├── backend/
│   ├── core/database.py       ← 8-table schema + seed data
│   ├── services/
│   │   ├── geo_engine.py      ← Haversine, ETA, risk matrix, runoff physics
│   │   ├── weather_api.py     ← Open-Meteo ingestion + DB cache
│   │   └── gemini_service.py  ← Gemini AI + fallback templates
│   ├── cache/ttl_cache.py     ← Thread-safe TTL cache
│   ├── tasks/background.py    ← Async sensor simulation + WebSocket push
│   └── api/routes/            ← 6 modular route files
│       ├── state.py, sos.py, simulate.py
│       ├── alerts.py, dispatch.py, ws.py
│
└── public/                    ← HTML/JS frontend (unchanged, served at /)
    ├── index.html, dashboard.html, map.html
    ├── simulator.html, evacuation.html
    ├── alerts.html, assistant.html
    └── app.js                 ← Shared tactical engine
```

---

## 🛠️ How to Run

### Step 1 — Start the Main Backend
```powershell
# In your rakshak-new folder:
python -m uvicorn main:app --host 0.0.0.0 --port 3000

# Open browser: http://localhost:3000
```

### Step 2 — Start the Analytics Dashboard (Optional)
```powershell
# In a second terminal:
streamlit run streamlit_app.py --server.port 8501

# Open browser: http://localhost:8501
```

### Step 3 — Enable Gemini AI (Optional, Completely Free)
```powershell
# 1. Get free key (no credit card): https://aistudio.google.com/app/apikey
# 2. Set the key:
$env:GEMINI_API_KEY="AIzaSy..."
# 3. Then start the server as above
```

> **Without Gemini key:** The system uses smart built-in fallback templates.
> Everything still works 100% — weather, maps, SOS, simulation, dispatch.

---

## 💸 Cost — ₹0 / \$0 / FREE

| Component | Cost |
|---|---|
| Open-Meteo Weather API | 🆓 Free, no key |
| Gemini AI API | 🆓 Free tier (just Gmail) |
| Leaflet Maps | 🆓 Open source |
| OpenStreetMap tiles | 🆓 Free |
| SQLite database | 🆓 Built into Python |
| FastAPI / Uvicorn / Streamlit | 🆓 Open source |
| **Total** | **₹0** |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/state` | Full SEOC system snapshot |
| `GET` | `/api/river-basins` | Live gauge readings |
| `GET` | `/api/field-units` | All field units with status |
| `GET` | `/api/incidents` | Alert/incident log |
| `POST` | `/api/sos` | Submit citizen distress call |
| `POST` | `/api/sos/update` | Triage/resolve SOS |
| `POST` | `/api/simulate` | Run disaster risk simulation |
| `POST` | `/api/dispatch` | Dispatch field unit |
| `POST` | `/api/broadcast/synthesize` | Generate AI multi-language alert |
| `GET` | `/api/weather/{city}` | Live weather for any UK city |
| `WS` | `/ws/live` | Real-time state stream |
| `GET` | `/api/docs` | Swagger interactive docs |

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Database** | SQLite (via stdlib sqlite3) |
| **AI** | Google Gemini 2.0 Flash Lite (free) |
| **Weather** | Open-Meteo API (free, no key) |
| **Maps** | Leaflet.js + OpenStreetMap |
| **Frontend** | Vanilla HTML5, TailwindCSS CDN, Web Audio API |
| **Analytics** | Streamlit, Plotly, Pandas |
| **Real-time** | WebSocket (FastAPI + browser native) |

---

## 📞 Emergency Helplines (India)
- **NDRF Control Room:** 011-24363260
- **Uttarakhand SDMA:** 0135-2710334
- **National Disaster Helpline:** 1077
- **National Emergency:** 112

---

*Built for Hackathon 2026 — Uttarakhand Disaster Intelligence Initiative*
*"Technology in Service of the Hills"*

