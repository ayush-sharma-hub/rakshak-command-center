"""Routes: GET /api/state — Full SEOC system state snapshot."""

from fastapi import APIRouter
from datetime import datetime, timezone
from backend.core.database import get_db

router = APIRouter(prefix="/api", tags=["State"])


@router.get("/state")
def get_state():
    conn = get_db()

    field_units = [dict(r) for r in conn.execute("SELECT * FROM field_units").fetchall()]
    river_basins = [dict(r) for r in conn.execute("SELECT * FROM river_basins").fetchall()]
    sos_signals = [dict(r) for r in conn.execute(
        "SELECT * FROM sos_signals ORDER BY created_at DESC LIMIT 20"
    ).fetchall()]
    incidents = [dict(r) for r in conn.execute(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 30"
    ).fetchall()]

    pending_sos = sum(1 for s in sos_signals if s["status"] == "PENDING")
    critical_units = sum(1 for b in river_basins if b["status"] in ("DANGER", "WARNING"))

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
        "recentIncidents": incidents,
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
    conn = get_db()
    rows = conn.execute("SELECT * FROM river_basins").fetchall()
    conn.close()
    return [dict(r) for r in rows]

