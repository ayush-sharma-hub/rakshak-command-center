"""Routes: LoRa Mesh Networking & Hydrodynamic Wave Lead-Time API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from backend.services.lora_engine import get_all_nodes, get_recent_packets, transmit_lora_packet, broadcast_lora_mesh
from backend.services.hydro_wave import calculate_wave_propagation

router = APIRouter(prefix="/api", tags=["LoRa Mesh & Wave Modeling"])


class LoRaTransmitRequest(BaseModel):
    source_node: str = Field(..., description="Node ID initiating transmission (e.g. LORA-ND-01)")
    packet_type: str = Field(default="SENSOR_TELEMETRY", description="SENSOR_TELEMETRY, SOS_DISTRESS, BEACON")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON sensor/SOS payload")
    max_hops: Optional[int] = Field(default=5, ge=1, le=10)


class LoRaBroadcastRequest(BaseModel):
    message: str = Field(..., description="Emergency message to broadcast over LoRa mesh")
    priority: Optional[str] = Field(default="HIGH", description="HIGH, CRITICAL, or EMERGENCY")


@router.post("/lora/broadcast")
def post_lora_broadcast(req: LoRaBroadcastRequest):
    """
    Broadcast an emergency civil warning across all mountain LoRa mesh repeater nodes.
    Triggered by SEOC incident controllers or as automated fallback when WebPush fails.
    """
    try:
        res = broadcast_lora_mesh(message=req.message, priority=req.priority or "HIGH")
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/lora/nodes")
def get_lora_nodes():
    """Returns all active Himalayan LoRa mesh repeater & gateway nodes."""
    return {
        "network": "Rakshak-LoRaMesh-UK",
        "frequency_band": "865-867 MHz (India License-Free ISM)",
        "protocol": "LoRaWAN / Meshtastic P2P Overlay",
        "nodes": get_all_nodes(),
    }


@router.get("/lora/packets")
def get_lora_packets(limit: int = 30):
    """Returns recent decoded RF packet stream."""
    return {
        "packets": get_recent_packets(limit=limit)
    }


@router.post("/lora/transmit")
def post_lora_transmit(req: LoRaTransmitRequest):
    """
    Transmit an RF packet across the mountain mesh network.
    Automatically traverses downstream hops toward Gateway and records in DB.
    Emergency SOS packets are automatically triaged into SEOC distress queue.
    """
    try:
        res = transmit_lora_packet(
            source_node_id=req.source_node,
            packet_type=req.packet_type,
            payload=req.payload,
            max_hops=req.max_hops
        )
        return res
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/wave-propagation")
def get_wave_propagation(
    corridor: str = "Mandakini",
    rainfall_mm: float = 120.0,
    cloudburst: bool = True
):
    """
    Computes downstream hydrodynamic wave arrival countdowns and evacuation lead times
    for settlements along Himalayan river networks (SIH #2619 Core Requirement).
    """
    return calculate_wave_propagation(
        corridor=corridor,
        rainfall_mm=rainfall_mm,
        cloudburst=cloudburst
    )

