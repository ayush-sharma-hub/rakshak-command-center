"""Routes: SOS signal management — receive, triage, resolve distress calls."""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from backend.core.database import get_db
from backend.services.geo_engine import find_nearest_unit

router = APIRouter(prefix="/api/sos", tags=["SOS"])


class SOSCreate(BaseModel):
    caller_name: str
    phone: Optional[str] = None
    lat: float
    lng: float
    location_name: Optional[str] = None
    details: Optional[str] = None
    priority: Optional[str] = "HIGH"


class SOSUpdate(BaseModel):
    id: str
    status: str                            # PENDING / DISPATCHED / EN ROUTE / CLEARED
    assigned_unit: Optional[str] = None
    operator_note: Optional[str] = None


@router.get("")
def get_sos_signals(status: Optional[str] = None):
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM sos_signals WHERE status=? ORDER BY created_at DESC",
            (status.upper(),)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sos_signals ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
def receive_sos(payload: SOSCreate):
    """Receive a new citizen SOS distress call."""
    conn = get_db()
    sos_id = f"SOS-{str(uuid.uuid4())[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    # Auto-assign nearest available unit
    units_raw = conn.execute(
        "SELECT id, lat, lng, unit_type, status, callsign FROM field_units"
    ).fetchall()
    units = [dict(u) for u in units_raw]
    nearest = find_nearest_unit(payload.lat, payload.lng, units)

    nearest_id = nearest["id"] if nearest else None
    assigned_unit = nearest["callsign"] if nearest else "Unassigned"
    eta = nearest.get("eta_minutes") if nearest else None
    dist = nearest.get("distance_km") if nearest else None

    conn.execute("""
        INSERT INTO sos_signals
        (id, caller_name, phone, lat, lng, location_name, details, status, assigned_unit,
         nearest_unit_id, eta_minutes, distance_km, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?)
    """, (
        sos_id, payload.caller_name, payload.phone,
        payload.lat, payload.lng, payload.location_name, payload.details,
        assigned_unit, nearest_id, eta, dist, payload.priority or "HIGH",
        now, now
    ))

    # Log to incidents
    conn.execute("""
        INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, created_at)
        VALUES ('SOS', ?, ?, ?, ?, ?, 60, ?)
    """, (
        f"Citizen SOS from {payload.caller_name} — {payload.details or 'No details'}",
        payload.location_name or "Unknown Location",
        payload.priority or "HIGH",
        payload.lat, payload.lng, now,
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "sos_id": sos_id,
        "assigned_unit": assigned_unit,
        "eta_minutes": eta,
        "distance_km": dist,
        "message": f"SOS {sos_id} received and logged. Nearest responder: {assigned_unit}.",
    }


@router.post("/update")
def update_sos(payload: SOSUpdate):
    """Update triage status of an existing SOS signal."""
    conn = get_db()
    row = conn.execute("SELECT id FROM sos_signals WHERE id=?", (payload.id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"SOS {payload.id} not found.")

    now = datetime.now(timezone.utc).isoformat()
    update_fields = ["status=?", "updated_at=?"]
    values = [payload.status.upper(), now]

    if payload.assigned_unit:
        update_fields.append("assigned_unit=?")
        values.append(payload.assigned_unit)

    values.append(payload.id)
    conn.execute(
        f"UPDATE sos_signals SET {', '.join(update_fields)} WHERE id=?",
        values
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "id": payload.id,
        "new_status": payload.status.upper(),
        "updated_at": now,
    }

