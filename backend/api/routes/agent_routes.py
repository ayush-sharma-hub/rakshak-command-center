"""
================================================================================
          RAKSHAK SEOC BACKEND  --  agent_routes.py
  FastAPI Router: Autonomous Disaster Intelligence & Dispatch Coordination
================================================================================

Exposes:
    POST /api/agent/analyze
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from backend.services.agent_service import run_disaster_analysis

logger = logging.getLogger("rakshak.agent.routes")

# ── Router Initialization ─────────────────────────────────────────────────────
# Note: When included in main.py with prefix="/api/agent" and tags=["Autonomous Agent"],
# this route will serve POST /api/agent/analyze.
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

    try:
        # Non-blocking async execution using FastAPI / Starlette threadpool
        assessment: Dict[str, Any] = await run_in_threadpool(
            run_disaster_analysis,
            location=location,
            verbose=False,
        )
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

