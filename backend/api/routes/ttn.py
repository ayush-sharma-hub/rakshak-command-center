"""The Things Network (TTN) webhook receiver skeleton for free-tier uplinks."""

import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from backend.core.database import get_db

router = APIRouter(prefix="/api/integrations/ttn", tags=["TTN LoRaWAN Webhook"])


def _verify_secret(received: Optional[str]) -> None:
    """Enable TTN_WEBHOOK_SECRET in production; empty means local/demo mode."""
    expected = os.environ.get("TTN_WEBHOOK_SECRET", "").strip()
    if expected and not received:
        raise HTTPException(status_code=401, detail="Missing TTN webhook secret")
    if expected and not hmac.compare_digest(expected, received or ""):
        raise HTTPException(status_code=401, detail="Invalid TTN webhook secret")


def _decode_payload(uplink: Dict[str, Any]) -> Dict[str, Any]:
    decoded = uplink.get("decoded_payload")
    if isinstance(decoded, dict):
        return decoded
    raw = uplink.get("frm_payload", "")
    if not raw:
        return {}
    try:
        return {"raw_text": base64.b64decode(raw).decode("utf-8", errors="replace")}
    except Exception:
        return {"raw_payload": raw}


@router.post("/uplink")
async def receive_ttn_uplink(request: Request, x_ttn_webhook_secret: Optional[str] = Header(default=None)):
    """Accept the TTN v3 application-uplink body and write an auditable event.

    Configure TTN's Webhook URL as /api/integrations/ttn/uplink and provide the
    same custom X-TTN-Webhook-Secret header as TTN_WEBHOOK_SECRET. SOS payloads
    create a normal SOS signal; every other payload is logged as an incident.
    """
    _verify_secret(x_ttn_webhook_secret)
    body = await request.json()
    identifiers = body.get("end_device_ids", {})
    device_id = identifiers.get("device_id", "ttn-unknown-device")
    uplink = body.get("uplink_message", {})
    decoded = _decode_payload(uplink)
    now = datetime.now(timezone.utc).isoformat()
    event_hash = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM ttn_webhook_events WHERE event_hash=?", (event_hash,)).fetchone()
        if exists:
            return {"success": True, "duplicate": True, "device_id": device_id}
        is_sos = bool(decoded.get("sos") or decoded.get("emergency")) or str(decoded.get("event", "")).upper() == "SOS"
        event_type = "SOS_DISTRESS" if is_sos else "SENSOR_TELEMETRY"
        conn.execute("""
            INSERT INTO ttn_webhook_events (event_hash, device_id, event_type, payload_json, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (event_hash, device_id, event_type, json.dumps(decoded), now))

        lat, lng = float(decoded.get("lat", 30.2844)), float(decoded.get("lng", 78.9811))
        location = str(decoded.get("location", f"TTN device {device_id}"))[:200]
        if is_sos:
            sos_id = f"SOS-TTN-{uuid.uuid4().hex[:6].upper()}"
            details = str(decoded.get("details") or decoded.get("message") or "Offline TTN LoRaWAN SOS uplink received.")[:1000]
            conn.execute("""
                INSERT INTO sos_signals (id, caller_name, phone, lat, lng, location_name, details, status, assigned_unit, priority, created_at, updated_at)
                VALUES (?, ?, 'TTN-LORAWAN', ?, ?, ?, ?, 'PENDING', 'TTN Auto-Triage', 'CRITICAL', ?, ?)
            """, (sos_id, str(decoded.get("caller", device_id))[:160], lat, lng, location, details, now, now))
            message, priority = f"[TTN OFFLINE SOS] {details}", "CRITICAL"
        else:
            sos_id = None
            message, priority = f"[TTN SENSOR] {device_id}: {json.dumps(decoded, ensure_ascii=False)[:800]}", "MEDIUM"

        conn.execute("""
            INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (f"TTN_{event_type}", message, location, priority, lat, lng, 95 if is_sos else 45, now))
        conn.commit()
        return {"success": True, "duplicate": False, "device_id": device_id, "event_type": event_type, "sos_id": sos_id}
    except (TypeError, ValueError) as exc:
        conn.rollback()
        raise HTTPException(status_code=422, detail="TTN payload contains invalid coordinates") from exc
    finally:
        conn.close()
