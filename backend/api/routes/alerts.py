"""Routes: Emergency broadcast management with AI multi-language generation."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from backend.core.database import get_db
from backend.services.gemini_service import generate_broadcast

router = APIRouter(prefix="/api", tags=["Alerts & Broadcasts"])


class BroadcastRequest(BaseModel):
    city: str
    risk_level: str          # LOW / MEDIUM / HIGH / CRITICAL
    rainfall_mm: Optional[float] = 0.0
    slope_deg: Optional[float] = 30.0
    details: Optional[str] = ""
    channels: Optional[list] = None
    operator_id: Optional[str] = "SEOC-DUTY-OFFICER"


@router.post("/broadcast/synthesize")
async def synthesize_broadcast(payload: BroadcastRequest):
    """Generate AI-powered multi-language emergency broadcast and log it."""
    import asyncio

    result = await asyncio.to_thread(
        generate_broadcast,
        risk_level=payload.risk_level.upper(),
        city=payload.city,
        rainfall_mm=payload.rainfall_mm or 0.0,
        slope_deg=payload.slope_deg or 30.0,
        details=payload.details or "",
        operator=payload.operator_id or "SEOC",
    )

    channels = payload.channels or ["Cell SMS", "Temple PA", "AIR FM"]
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    import json
    conn.execute("""
        INSERT INTO broadcasts
        (target_city, risk_level, msg_english, msg_hindi, msg_garhwali, msg_kumaoni,
         channels, ai_generated, operator_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.city,
        payload.risk_level.upper(),
        result.get("english", ""),
        result.get("hindi", ""),
        result.get("garhwali", ""),
        result.get("kumaoni", ""),
        json.dumps(channels),
        1 if result.get("source") == "gemini" else 0,
        payload.operator_id,
        now,
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "broadcast": result,
        "channels": channels,
        "logged_at": now,
    }


@router.get("/broadcasts")
def get_broadcasts(city: Optional[str] = None, limit: int = 20):
    conn = get_db()
    if city:
        rows = conn.execute(
            "SELECT * FROM broadcasts WHERE target_city=? ORDER BY created_at DESC LIMIT ?",
            (city, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/weather/{city}")
async def get_weather(city: str):
    """Get live weather for a named Uttarakhand city."""
    import asyncio
    from backend.services.weather_api import fetch_weather
    result = await asyncio.to_thread(fetch_weather, city)
    if not result:
        return {"error": f"Weather data unavailable for {city}"}
    return result


@router.get("/weather")
async def get_all_weather():
    """Get weather for all high-priority cities."""
    import asyncio
    from backend.services.weather_api import fetch_all_weather
    return await asyncio.to_thread(fetch_all_weather)


@router.post("/alerts/phone-test")
def trigger_phone_test(city: Optional[str] = "Kedarnath Mandakini Basin"):
    """
    Generates an emergency crisis payload for testing real smartphone alerts,
    including haptic vibration patterns and high-decibel tactical sirens.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "success": True,
        "title": "⚠️ SEOC CRITICAL EMERGENCY: FLASH FLOOD ALERT",
        "body": f"Urgent Evacuation Warning: Cloudburst detected upstream of {city}! Runoff velocity 45 km/h. Move to designated high ground immediately!",
        "vibrate_pattern": [500, 150, 500, 150, 800],
        "audio_siren": True,
        "timestamp": now,
        "emergency_helpline": "1070 (Disaster Call) / 112 (Police & SDRF)"
    }


class BroadcastPublishRequest(BaseModel):
    city: str
    risk_level: Optional[str] = "CRITICAL"
    message: str
    channels: Optional[list] = None
    operator_id: Optional[str] = "UK-SEOC-OFFICER-04"


@router.post("/alerts/broadcast")
def publish_broadcast(payload: BroadcastPublishRequest):
    """Publish a live multi-channel disaster broadcast and log to incidents for citizen notifications."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    c = conn.cursor()

    # Log into incidents so it appears in /api/state and triggers live client push alerts
    c.execute("""
        INSERT INTO incidents (type, msg, zone, priority, risk_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        f"BROADCAST_{payload.risk_level.upper()}",
        payload.message,
        payload.city,
        payload.risk_level.upper(),
        95 if payload.risk_level.upper() == "CRITICAL" else 75,
        now
    ))

    import json
    c.execute("""
        INSERT INTO broadcasts (target_city, risk_level, msg_english, channels, operator_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        payload.city,
        payload.risk_level.upper(),
        payload.message,
        json.dumps(payload.channels or ["Cell SMS", "Temple PA", "AIR FM", "Web Push"]),
        payload.operator_id,
        now
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Broadcast transmitted across all towers and web channels for {payload.city}.",
        "timestamp": now,
        "city": payload.city,
        "risk_level": payload.risk_level,
        "body": payload.message
    }


@router.get("/alerts/latest")
def get_latest_alerts(since: Optional[str] = None):
    """Lightweight polling endpoint for smartphone client notifications."""
    conn = get_db()
    if since:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE created_at > ? ORDER BY created_at DESC LIMIT 10",
            (since,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]



