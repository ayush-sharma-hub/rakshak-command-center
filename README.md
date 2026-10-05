# PROJECT RAKSHAK — SEOC TACTICAL C4ISR COMMAND CENTER

```
╔══════════════════════════════════════════════════════════════════╗
║  PROJECT RAKSHAK  ·  UTTARAKHAND STATE EMERGENCY OPERATIONS     ║
║  C4ISR — Command · Control · Communications · Computers ·       ║
║          Intelligence · Surveillance · Reconnaissance           ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Autonomous AI-powered disaster intelligence platform** for real-time flood, landslide, and GLOF (Glacial Lake Outburst Flood) response in Uttarakhand, India. Built as a Palantir Gotham–inspired Tactical HUD — serving NDRF/SDRF commanders with live agent telemetry, river sensor feeds, and multi-hazard threat assessment.

---

## ⚡ Key Features

| Capability | Description |
|---|---|
| **Dual-Provider AI Agent** | Gemini (cloud) + Ollama (on-prem) via LiteLLM — zero vendor lock-in |
| **Live WebSocket Telemetry** | Real-time agent thought-logs streamed to the C4ISR terminal as the AI reasons |
| **Palantir-Inspired Tactical HUD** | Pure HTML5/CSS3/Vanilla JS — no frameworks, no build steps — brutalist edge-to-edge C4ISR layout |
| **Autonomous Disaster Intelligence** | Smolagents runs DuckDuckGo web searches to fetch live disaster data, rainfall, and NDRF deployment status |
| **CartoDB Dark Matter GIS Map** | Leaflet.js map defaulting to Uttarakhand (30.0668°N, 79.0193°E) with river sensor overlays |
| **Dynamic Threat Level Engine** | UI border/glow transitions from Normal → Elevated → Severe in real time |
| **LoRa Mesh Network Monitor** | 865 MHz 8-node Himalayan mesh status dashboard |
| **Emergency Broadcast Panel** | Push alerts to LoRa mesh and satellite uplink from the HUD |

---

## 🛠 Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Runtime | **Python 3.11+** |
| Web Framework | **FastAPI** + Uvicorn ASGI server |
| AI Agent Engine | **Smolagents** (HuggingFace) with `DuckDuckGoSearchTool` |
| LLM Routing | **LiteLLM** — routes to Gemini 2.0 Flash or local Ollama |
| WebSocket Streaming | FastAPI native WebSocket — agent thought-logs streamed without blocking |
| Static Serving | `fastapi.staticfiles.StaticFiles` mounts `frontend_tactical/` at `/` |

### Frontend
| Layer | Technology |
|---|---|
| Markup | **Pure HTML5** — semantic, grid-based, zero framework |
| Styles | **Custom CSS3** — CSS Grid, CSS Variables, `@keyframes`, no Tailwind |
| Scripting | **Vanilla JS ES6+** — no React, no bundler, no build step |
| GIS Map | **Leaflet.js 1.9.4** — CartoDB Dark Matter tile layer |
| Icons | Font Awesome 6.5 |
| Typography | Inter (UI labels) + JetBrains Mono / Courier New (all telemetry & terminal data) |

### Infrastructure
| Concern | Solution |
|---|---|
| Production Host | **Render.com** — `Procfile` binds `$PORT` via Uvicorn |
| Env Secrets | `GEMINI_API_KEY`, `OLLAMA_BASE_URL` via env vars / `.env` |

---

## 📁 Project Structure

```
rakshak-new/
├── main.py                          # FastAPI app — mounts frontend, registers routers
├── Procfile                         # Render deploy: uvicorn main:app --host 0.0.0.0 --port $PORT
├── requirements.txt                 # Python dependencies
├── .env                             # API keys (gitignored)
│
├── backend/
│   ├── api/routes/
│   │   ├── agent_routes.py          # POST /api/agent/analyze  +  WS /api/agent/stream
│   │   ├── river_routes.py          # GET  /api/river-basins/live
│   │   ├── alert_routes.py          # GET  /api/alerts/latest
│   │   └── state_routes.py          # GET  /api/state
│   └── services/
│       └── agent_service.py         # Smolagents runner + contextvars WS streaming
│
└── frontend_tactical/               # Served at / by FastAPI StaticFiles
    ├── index.html                   # C4ISR HUD skeleton — CSS Grid layout
    ├── css/
    │   └── style.css                # Gotham × SpaceX aesthetic — 1100+ lines
    └── js/
        └── app.js                   # Vanilla JS brain — clocks, map, WS, agent API
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11+
- (Optional) Ollama running locally for offline LLM

### 1. Clone & install

```bash
git clone https://github.com/your-org/rakshak-new.git
cd rakshak-new
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
# GEMINI_API_KEY=your_gemini_api_key_here
# OLLAMA_BASE_URL=http://localhost:11434   (optional)
```

### 3. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

Open **http://localhost:3000** — the C4ISR HUD loads directly.

### 4. Test the AI agent

- In the HUD search bar, type `Kedarnath, Uttarakhand` and click **ANALYZE SECTOR**
- Watch the **bottom terminal** stream real-time AI thought-logs via WebSocket
- The threat level indicator and map borders update dynamically based on the assessment

---

## 🌐 Production Deployment (Render)

The `Procfile` at project root handles Render auto-detection:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set the following environment variables in your Render dashboard:
- `GEMINI_API_KEY`
- `OLLAMA_BASE_URL` (optional — omit for cloud-only mode)

---

## 🔌 API Reference

### `POST /api/agent/analyze`
Triggers autonomous disaster analysis for a given location.

**Request:**
```json
{ "location": "Rudraprayag, Uttarakhand" }
```

**Response:**
```json
{
  "location": "Rudraprayag, Uttarakhand",
  "threat_level": "Elevated",
  "active_hazards": ["Flash Flood", "Landslide"],
  "action_plan": ["Deploy NDRF-11/C", "Issue evacuation advisory"],
  "summary": "Heavy monsoon activity detected upstream...",
  "confidence": "High",
  "resources_needed": { "ndrf_teams": 2, "helicopters": 1 }
}
```

### `WS /api/agent/stream`
WebSocket endpoint. Streams agent thought-logs in real time.

**Message format (server → client):**
```json
{ "type": "thought", "log": "Searching DuckDuckGo for Kedarnath flood alerts...", "level": "info" }
{ "type": "result", "data": { ...same as analyze response... } }
```

### `GET /api/river-basins/live`
Returns live hydrological sensor readings for Uttarakhand river basins.

### `GET /api/alerts/latest`
Returns recent SOS/incident alerts. Supports `?after_id=` for incremental polling.

---

## 🖥 UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  TOP HUD — IST/UTC Clocks · SAT Uplink · THREAT LEVEL  │  42px
├───┬─────────────────────────────────────────┬───────────┤
│   │                                         │  HYDRO    │
│NAV│      TACTICAL GIS MAP                   │  FORCES   │
│   │  (CartoDB Dark Matter + Leaflet)        │  BROADCAST│
│   │  AI Intel Brief overlay on analyze      │  LORA     │
│   │  Radar scanline animation               │           │
├───┴─────────────────────────────────────────┴───────────┤
│  BOTTOM TERMINAL — Live Agent Stream (lime-green mono)  │  130px
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 Design System

| Token | Value | Usage |
|---|---|---|
| `--bg-void` | `#02040A` | Root background |
| `--panel-bg` | `#0D1117` | Panel fills |
| `--border-dim` | `#1E293B` | Default borders (1px solid, 0 radius) |
| `--alert-amber` | `#F59E0B` | Elevated threat |
| `--alert-red` | `#EF4444` | Severe/Critical threat |
| `--alert-cyan` | `#06B6D4` | Active / nominal status |
| Terminal fg | `#39FF14` | Lime-green phosphor glow |
| Terminal bg | `#000000` | Pitch black |

**Design rules:** No `border-radius` > 2px. No soft shadows. No rounded buttons. Sharp brutalist edges only.

---

## 📡 WebSocket Architecture

```
Browser                        FastAPI Server
   │                                │
   │── WS CONNECT /api/agent/stream ──►│
   │                                │ AgentStreamManager registers client
   │── POST /api/agent/analyze ──────►│
   │                                │ ContextVar sets callback
   │                                │ Smolagents thread starts
   │◄── { type:"thought", log:"..." } │ step_callback fires → asyncio bridge
   │◄── { type:"thought", log:"..." } │ DuckDuckGo tool fires → emit_thought
   │◄── { type:"result",  data:{...}} │ Analysis complete
   │                                │
```

---

## 🔒 License

Project Rakshak is developed for emergency response research and SEOC operational support. All rights reserved.

---

*Built for Uttarakhand SEOC — "जन सेवा ही ईश्वर सेवा" (Service to People is Service to God)*
