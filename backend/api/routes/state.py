"""Routes: GET /api/state — Full SEOC system state snapshot."""

from fastapi import APIRouter
from datetime import datetime, timezone
from backend.core.database import get_db

router = APIRouter(prefix="/api", tags=["State"])


@router.get("/state")
def get_state():
    conn = get_db()

    field_units = [dict(r) for r in conn.execute("SELECT * FROM field_units").fetchall()]
    river_basins_raw = [dict(r) for r in conn.execute("SELECT * FROM river_basins").fetchall()]
    sos_signals_raw = [dict(r) for r in conn.execute(
        "SELECT * FROM sos_signals ORDER BY created_at DESC LIMIT 20"
    ).fetchall()]
    incidents_raw = [dict(r) for r in conn.execute(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 30"
    ).fetchall()]

    # Format river basins with dual camelCase & snake_case
    river_basins = []
    for b in river_basins_raw:
        item = dict(b)
        item["currentLevel"] = b["current_level"]
        item["dangerLevel"] = b["danger_level"]
        item["warningLevel"] = b["warning_level"]
        river_basins.append(item)

    # Format SOS signals with dual camelCase & snake_case
    sos_signals = []
    for s in sos_signals_raw:
        item = dict(s)
        item["callerName"] = s["caller_name"]
        item["locationName"] = s["location_name"]
        item["assignedUnit"] = s["assigned_unit"]
        created = s.get("created_at", "")
        item["time"] = created.split("T")[1][:5] if "T" in created else "Just now"
        sos_signals.append(item)

    # Format incidents with time string
    incidents = []
    for i in incidents_raw:
        item = dict(i)
        created = i.get("created_at", "")
        item["time"] = created.split("T")[1][:5] if "T" in created else "Just now"
        incidents.append(item)

    pending_sos = sum(1 for s in sos_signals if s["status"] == "PENDING")
    critical_units = sum(1 for b in river_basins if b["status"] in ("DANGER", "WARNING"))

    # Fetch latest simulation state for risk & telemetry
    latest_sim = conn.execute(
        "SELECT * FROM simulation_sessions ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    if latest_sim:
        risk = {
            "level": latest_sim["risk_level"],
            "score": latest_sim["risk_score"],
            "explanation": latest_sim["explanation"] or "Automated hazard analysis active.",
            "popAtRisk": latest_sim["pop_at_risk"] or 0,
        }
        simulated_city = latest_sim["city_name"]
        telemetry = {
            "rainfall": latest_sim["rainfall"],
            "slope": latest_sim["slope"],
            "elevation": latest_sim["elevation"],
            "soil": latest_sim["soil"] or "Clay",
            "cloudburst": bool(latest_sim["cloudburst"]),
        }
    else:
        risk = {
            "level": "SAFE",
            "score": 18,
            "explanation": "Monitored catchment sensors nominal. No active cloudburst detected.",
            "popAtRisk": 0,
        }
        simulated_city = None
        telemetry = {
            "rainfall": 14.0,
            "slope": 30.0,
            "elevation": 1800.0,
            "soil": "Sandy Loam",
            "cloudburst": False,
        }

    conn.close()

    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "watchCommander": {
            "name": "Capt. Rajeshwar Negi",
            "rank": "SEOC Chief Watch Officer",
            "shift": "Alpha Watch (0600–1800)",
            "badgeId": "UK-SEOC-001",
        },
        "riverBasins": river_basins,
        "fieldUnits": field_units,
        "activeSOS": sos_signals,
        "sosSignals": sos_signals,          # Dual compatibility for app.js
        "recentIncidents": incidents,
        "alerts": incidents,                # Dual compatibility for alerts.html
        "risk": risk,                       # Crucial for app.js, alerts.html, evacuation.html, assistant.html
        "simulatedCity": simulated_city,    # Crucial for simulator override & evacuation
        "telemetry": telemetry,             # Crucial for app.js
        "summary": {
            "pendingSOSCount": pending_sos,
            "criticalBasins": critical_units,
            "deployedUnits": sum(1 for u in field_units if u["status"] not in ("STANDBY", "OFFLINE")),
            "totalFieldStrength": sum(u["strength"] for u in field_units),
        },
    }


@router.get("/incidents")
def get_incidents(limit: int = 50, priority: str = None):
    conn = get_db()
    if priority:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE priority=? ORDER BY created_at DESC LIMIT ?",
            (priority.upper(), limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/field-units")
def get_field_units():
    conn = get_db()
    rows = conn.execute("SELECT * FROM field_units").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/river-basins")
def get_river_basins():
    """Returns river basins stored and synchronized in the database."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM river_basins").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/river-basins/live")
async def get_live_river_data():
    """
    Returns REAL river level data derived from upstream Open-Meteo precipitation.
    Uses hydrological estimation (Rational Method + Manning's equation).
    Data source: Open-Meteo API (free, no key required) + CWC official thresholds.
    """
    import asyncio
    from backend.services.river_data import fetch_all_rivers
    rivers = await asyncio.to_thread(fetch_all_rivers)
    return {
        "source": "Open-Meteo upstream precipitation + Hydrological estimation",
        "note": "River levels estimated from real-time atmospheric data. CWC thresholds are official.",
        "rivers": rivers,
        "fetched_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    }


@router.get("/river-basins/live/{basin_name}")
async def get_live_river_basin(basin_name: str):
    """Get real-time data for a specific river basin."""
    import asyncio
    from backend.services.river_data import fetch_river_data
    from fastapi import HTTPException
    data = await asyncio.to_thread(fetch_river_data, basin_name)
    if not data:
        raise HTTPException(status_code=404, detail=f"Basin '{basin_name}' not found. Available: Mandakini, Alaknanda, Bhagirathi, Tons, Saryu")
    return data

