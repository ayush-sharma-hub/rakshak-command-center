"""Routes: Dispatch orders — send field units to sectors."""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from backend.core.database import get_db

router = APIRouter(prefix="/api", tags=["Dispatch"])


class DispatchRequest(BaseModel):
    unit_id: str
    target_sector: str
    objective: Optional[str] = None
    sos_id: Optional[str] = None
    authorized_by: Optional[str] = "SEOC-DUTY-OFFICER"


@router.post("/dispatch")
def dispatch_unit(payload: DispatchRequest):
    conn = get_db()

    unit = conn.execute("SELECT * FROM field_units WHERE id=?", (payload.unit_id,)).fetchone()
    if not unit:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Unit {payload.unit_id} not found.")

    order_ref = f"ORD-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO dispatch_orders (order_ref, sos_id, unit_id, target_sector, objective, authorized_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        order_ref, payload.sos_id, payload.unit_id,
        payload.target_sector, payload.objective, payload.authorized_by, now,
    ))

    conn.execute(
        "UPDATE field_units SET status='DEPLOYED', last_updated=? WHERE id=?",
        (now, payload.unit_id)
    )

    conn.execute("""
        INSERT INTO incidents (type, msg, zone, priority, created_at)
        VALUES ('DISPATCH', ?, ?, 'INFO', ?)
    """, (
        f"[{order_ref}] {unit['callsign']} dispatched to {payload.target_sector}. Objective: {payload.objective or 'Search & Rescue'}.",
        payload.target_sector, now,
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "order_ref": order_ref,
        "unit": {"id": payload.unit_id, "callsign": unit["callsign"], "new_status": "DEPLOYED"},
        "target_sector": payload.target_sector,
        "authorized_by": payload.authorized_by,
        "dispatched_at": now,
    }


@router.get("/dispatch")
def get_dispatch_orders(limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM dispatch_orders ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

