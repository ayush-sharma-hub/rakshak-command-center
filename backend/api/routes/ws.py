"""Routes: WebSocket /ws/live — Real-time state streaming to connected clients."""

import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.tasks.background import register_ws_client, deregister_ws_client
from backend.core.database import get_db
from datetime import datetime, timezone

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("rakshak.ws")


@router.websocket("/ws/live")
async def live_stream(websocket: WebSocket):
    """
    WebSocket endpoint. Sends an initial state snapshot on connect,
    then receives live push updates from the background loop.
    """
    await websocket.accept()
    register_ws_client(websocket)
    logger.info("New WebSocket client connected.")

    # ── Send initial state snapshot
    try:
        conn = get_db()
        basins = [dict(r) for r in conn.execute("SELECT * FROM river_basins").fetchall()]
        units = [dict(r) for r in conn.execute("SELECT * FROM field_units").fetchall()]
        sos = [dict(r) for r in conn.execute(
            "SELECT * FROM sos_signals WHERE status!='CLEARED' ORDER BY created_at DESC LIMIT 10"
        ).fetchall()]
        conn.close()

        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "river_basins": basins,
            "field_units": units,
            "active_sos": sos,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
    except Exception as e:
        logger.error("WS initial state send failed: %s", e)

    # ── Keep connection alive (background loop pushes updates)
    try:
        while True:
            msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            # Echo ping/pong
            if msg == "ping":
                await websocket.send_text("pong")
    except asyncio.TimeoutError:
        await websocket.send_text(json.dumps({"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()}))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        deregister_ws_client(websocket)

