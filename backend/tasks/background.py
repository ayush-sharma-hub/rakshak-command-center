"""
Project Rakshak — Background Task Engine
Periodically refreshes weather data, updates river basin levels,
generates AI alerts for high-risk conditions, and broadcasts live
state updates to all connected WebSocket clients.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone

logger = logging.getLogger("rakshak.background")

# Shared WebSocket connection registry — populated by api/routes/ws.py
_ws_clients: set = set()


def register_ws_client(ws):
    _ws_clients.add(ws)
    logger.info("WS client connected. Total: %d", len(_ws_clients))


def deregister_ws_client(ws):
    _ws_clients.discard(ws)
    logger.info("WS client disconnected. Total: %d", len(_ws_clients))


async def _broadcast_ws(payload: dict):
    """Send JSON payload to all connected WebSocket clients."""
    if not _ws_clients:
        return
    import json
    msg = json.dumps(payload)
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _ws_clients.discard(ws)


async def _tick_river_basins():
    """Slightly oscillate river basin levels to simulate real-time sensor feed."""
    try:
        from backend.core.database import get_db
        conn = get_db()
        basins = conn.execute("SELECT id, current_level, danger_level, warning_level, river FROM river_basins").fetchall()
        now = datetime.now(timezone.utc).isoformat()
        for b in basins:
            delta = random.uniform(-0.05, 0.12)   # Slow realistic rise/fall
            new_level = round(b["current_level"] + delta, 2)

            if new_level >= b["danger_level"]:
                status = "DANGER"
                trend = "⬆ Rising Fast"
            elif new_level >= b["warning_level"]:
                status = "WARNING"
                trend = "⬆ Rising"
            elif new_level < b["warning_level"] - 1.5:
                status = "SAFE"
                trend = "⬇ Receding"
            else:
                status = "NOMINAL"
                trend = "Steady"

            conn.execute(
                "UPDATE river_basins SET current_level=?, status=?, trend=?, last_updated=? WHERE id=?",
                (new_level, status, trend, now, b["id"])
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("River basin tick error: %s", exc)


async def _tick_weather_fetch():
    """Fetch fresh weather for priority cities — runs every 15 min."""
    try:
        from backend.services.weather_api import fetch_weather
        priority = ["Rudraprayag", "Chamoli", "Joshimath", "Uttarkashi"]
        for city in priority:
            await asyncio.to_thread(fetch_weather, city)
            await asyncio.sleep(1)   # Small pause between API calls
    except Exception as exc:
        logger.error("Weather fetch error: %s", exc)


async def _tick_ai_alert():
    """
    For each HIGH/CRITICAL river basin, auto-generate a Gemini AI incident
    and store it in the incidents table.
    """
    try:
        from backend.core.database import get_db
        from backend.services.gemini_service import analyze_risk

        conn = get_db()
        risky = conn.execute(
            "SELECT * FROM river_basins WHERE status IN ('DANGER', 'WARNING')"
        ).fetchall()

        for basin in risky:
            # Check if we already logged this recently (don't spam DB)
            recent = conn.execute(
                "SELECT id FROM incidents WHERE zone LIKE ? AND created_at > datetime('now', '-30 minutes')",
                (f"%{basin['river'].split(' ')[0]}%",)
            ).fetchone()
            if recent:
                continue

            risk_level = "CRITICAL" if basin["status"] == "DANGER" else "HIGH"
            analysis = await asyncio.to_thread(
                analyze_risk,
                city=basin["river"],
                rainfall_mm=random.uniform(80, 180),
                slope_deg=35.0,
                elevation_m=1500.0,
                risk_score=75 if risk_level == "CRITICAL" else 55,
                risk_level=risk_level,
                is_cloudburst=False,
            )
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, ai_analysis, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "RIVER ALERT",
                f"{basin['river']} at {basin['current_level']}m — {basin['trend']} — Exceeding threshold.",
                basin["river"],
                risk_level,
                basin["lat"],
                basin["lng"],
                75 if risk_level == "CRITICAL" else 55,
                analysis,
                now,
            ))
            conn.commit()
            logger.info("AI incident logged for %s", basin["river"])

        conn.close()

        # Push live update to WebSocket clients
        await _broadcast_ws({
            "type": "incident_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "River basin status refreshed.",
        })

    except Exception as exc:
        logger.error("AI alert tick error: %s", exc)


async def sensor_simulation_loop():
    """
    Main background loop — runs continuously.
    - Every 8s:  Tick river basin levels (sensor simulation)
    - Every 30s: Push live state summary to WebSocket clients
    - Every 15min: Refresh weather cache
    - Every 20min: Generate AI alerts for risky basins
    """
    logger.info("[Background] Sensor simulation loop started.")
    weather_counter = 0
    ai_counter = 0

    while True:
        # ── River basin tick (every 8 seconds)
        await _tick_river_basins()

        weather_counter += 8
        ai_counter += 8

        # ── Push live snapshot to WebSocket clients (every 30 seconds)
        if weather_counter % 30 == 0:
            try:
                from backend.core.database import get_db
                conn = get_db()
                basins = [dict(r) for r in conn.execute("SELECT river, current_level, status, trend FROM river_basins").fetchall()]
                sos_count = conn.execute("SELECT COUNT(*) FROM sos_signals WHERE status='PENDING'").fetchone()[0]
                conn.close()
                await _broadcast_ws({
                    "type": "live_state",
                    "river_basins": basins,
                    "pending_sos": sos_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as exc:
                logger.error("WS broadcast error: %s", exc)

        # ── Weather refresh (every 15 minutes)
        if weather_counter >= 900:
            await _tick_weather_fetch()
            weather_counter = 0

        # ── AI alert generation (every 20 minutes)
        if ai_counter >= 1200:
            await _tick_ai_alert()
            ai_counter = 0

        await asyncio.sleep(8)

