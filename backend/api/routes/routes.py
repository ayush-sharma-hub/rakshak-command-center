"""Safe-route API. New endpoint; does not modify the legacy route or map feeds."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.route_engine import calculate_safe_route

router = APIRouter(prefix="/api/routes", tags=["Safe Routing"])


class MapPoint(BaseModel):
    lat: float = Field(ge=26.0, le=33.0)
    lng: float = Field(ge=76.0, le=82.0)


class SafeRouteRequest(BaseModel):
    start: MapPoint
    destination: MapPoint


@router.post("/safe")
async def safe_route(payload: SafeRouteRequest):
    try:
        return await calculate_safe_route(
            (payload.start.lat, payload.start.lng),
            (payload.destination.lat, payload.destination.lng),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

