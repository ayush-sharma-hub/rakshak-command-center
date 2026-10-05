"""
================================================================================
          RAKSHAK SEOC BACKEND  --  agent_routes.py
  FastAPI Router: Autonomous Disaster Intelligence & Dispatch Coordination
================================================================================

Exposes:
    POST /api/agent/analyze
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from backend.services.agent_service import run_disaster_analysis

logger = logging.getLogger("rakshak.agent.routes")

# ── WebSocket Connection Manager for Agent Telemetry ─────────────────────────
class AgentStreamManager:
    """Manages real-time telemetry streaming to tactical command center clients."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("[Agent WS] Client connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("[Agent WS] Client disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, data: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

agent_stream_manager = AgentStreamManager()

# ── Router Initialization ─────────────────────────────────────────────────────
# When included in main.py with prefix="/api/agent", exposes:
# POST /api/agent/analyze
# WS   /api/agent/stream
router = APIRouter()


# ── Pydantic Request & Response Schemas ────────────────────────────────────────

class AgentAnalysisRequest(BaseModel):
    """
    Request payload for autonomous disaster analysis.
    Validates location string length and strips whitespace.
    """
    location: str = Field(
        ...,
        description="Target location for real-time disaster intelligence & threat assessment",
        json_schema_extra={"example": "Roorkee, Uttarakhand"},
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "location": "Roorkee, Uttarakhand"
            }
        }
    }


class ResourceNeeds(BaseModel):
    ndrf_teams: int = 0
    helicopters: int = 0
    medical_units: int = 0
    relief_camps: int = 0


class AgentAnalysisResponse(BaseModel):
    location: str
    threat_level: str
    confidence: Optional[str] = "Medium"
    active_hazards: Optional[List[str]] = []
    summary: str
    action_plan: List[str]
    resources_needed: Optional[ResourceNeeds] = None
    contact_agencies: Optional[List[str]] = []


# ── Route Implementation ──────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AgentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Autonomous Disaster Risk & Dispatch Assessment",
    description=(
        "Executes live DuckDuckGo weather and emergency news searches, applies "
        "Google Gemini reasoning under NDMA/SEOC disaster criteria, and returns "
        "a verified threat level, situational overview, prioritized action plan, "
        "and emergency resource allocation. Runs asynchronously in a thread pool "
        "to prevent blocking the server event loop."
    ),
    responses={
        200: {
            "description": "Successful autonomous assessment",
            "model": AgentAnalysisResponse,
        },
        400: {
            "description": "Invalid location parameter (empty or malformed)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "InvalidLocation",
                        "message": "Location parameter cannot be empty or whitespace only.",
                    }
                }
            },
        },
        500: {
            "description": "Analysis engine execution failure",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AgentAnalysisFailed",
                        "message": "Disaster analysis engine could not complete the request. Please retry shortly.",
                    }
                }
            },
        },
    },
)
async def analyze_location(request: AgentAnalysisRequest):
    """
    POST /api/agent/analyze
    Delegates heavy synchronous LLM generation and web retrieval to a non-blocking
    worker thread via `starlette.concurrency.run_in_threadpool`.
    """
    location = (request.location or "").strip()
    if not location or len(location) < 2 or len(location) > 150:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "InvalidLocation",
                "message": "Location parameter cannot be empty or whitespace only, and must be between 2 and 150 characters.",
            },
        )

    logger.info("Received autonomous assessment request for location: '%s'", location)

    loop = asyncio.get_running_loop()

    def sync_thought_callback(msg: str, level: str = "info"):
        asyncio.run_coroutine_threadsafe(
            agent_stream_manager.broadcast({
                "type": "thought",
                "level": level,
                "log": msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }),
            loop,
        )

    # Initial broadcast of analysis initiation
    await agent_stream_manager.broadcast({
        "type": "thought",
        "level": "info",
        "log": f"[AI AGENT] Autonomous threat assessment initiated for '{location}'...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        # Non-blocking async execution using FastAPI / Starlette threadpool
        assessment: Dict[str, Any] = await run_in_threadpool(
            run_disaster_analysis,
            location=location,
            verbose=False,
            on_thought=sync_thought_callback,
        )

        # Broadcast assessment result to connected tactical terminals
        await agent_stream_manager.broadcast({
            "type": "result",
            "data": assessment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return assessment

    except Exception as exc:
        # Log the full traceback internally for SEOC operations debugging
        logger.error(
            "Agent analysis unhandled exception for location '%s': %s",
            location,
            exc,
            exc_info=True,
        )

        # Return a safe, clean HTTP 500 without leaking file paths or internal credentials
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "AgentAnalysisFailed",
                "message": "Disaster analysis engine could not complete the request. Please retry shortly.",
            },
        )


# ── Autonomous Agent Real-Time Telemetry WebSocket ───────────────────────────

@router.websocket("/stream")
async def websocket_agent_stream(websocket: WebSocket):
    """
    WebSocket endpoint: /api/agent/stream
    Streams real-time Smolagents thoughts, tool invocations, and live risk evaluations
    line-by-line to connected C4ISR Tactical Command Center terminals.
    """
    await agent_stream_manager.connect(websocket)
    try:
        # Handshake frame
        await websocket.send_json({
            "type": "thought",
            "level": "sys",
            "log": "[C4ISR UPLINK] Real-time Autonomous Agent WebSocket telemetry connected.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                target_loc = data.get("location") or data.get("target") or str(raw_text)
            except Exception:
                target_loc = raw_text.strip()

            if target_loc:
                loop = asyncio.get_running_loop()

                def sync_ws_cb(msg: str, level: str = "info"):
                    asyncio.run_coroutine_threadsafe(
                        agent_stream_manager.broadcast({
                            "type": "thought",
                            "level": level,
                            "log": msg,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }),
                        loop,
                    )

                await agent_stream_manager.broadcast({
                    "type": "thought",
                    "level": "info",
                    "log": f"[AI AGENT] Autonomous risk assessment requested for '{target_loc}'...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                assessment = await run_in_threadpool(
                    run_disaster_analysis,
                    location=target_loc,
                    verbose=False,
                    on_thought=sync_ws_cb,
                )

                await agent_stream_manager.broadcast({
                    "type": "result",
                    "data": assessment,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        agent_stream_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("[Agent WS] Connection closed: %s", exc)
        agent_stream_manager.disconnect(websocket)


# ── Autonomous Sentinel System Endpoints ─────────────────────────────────────

@router.get(
    "/sentinel-status",
    status_code=status.HTTP_200_OK,
    summary="Get Autonomous Sentinel System Status and Latest Scan",
    description=(
        "Returns the operational status of the background sentinel daemon, "
        "timestamp of the last scan cycle, and cached threat assessments for "
        "high-risk Himalayan zones."
    ),
)
async def get_sentinel_daemon_status():
    """
    GET /api/agent/sentinel-status
    Returns the latest cached autonomous scan results and the timestamp of the last scan.
    """
    from backend.services.sentinel_service import get_sentinel_status
    return get_sentinel_status()


@router.post(
    "/sentinel-scan",
    status_code=status.HTTP_200_OK,
    summary="Trigger Immediate Autonomous Sentinel Scan Cycle",
    description="Forces an on-demand background sentinel cycle across all monitored high-risk zones.",
)
async def trigger_manual_sentinel_scan():
    """
    POST /api/agent/sentinel-scan
    Triggers an immediate sentinel scan cycle and returns the scan results.
    """
    from backend.services.sentinel_service import trigger_sentinel_scan
    return await trigger_sentinel_scan()

