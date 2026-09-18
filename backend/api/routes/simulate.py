"""Routes: POST /api/simulate — Run disaster risk simulation with AI analysis."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from backend.core.database import get_db
from backend.services.geo_engine import risk_matrix, calculate_runoff_velocity
from backend.services.gemini_service import analyze_risk

router = APIRouter(prefix="/api", tags=["Simulation"])

# Soil permeability presets (fraction 0–1; 1 = fully permeable)
SOIL_PERMEABILITY = {
    "Sandy Loam":   0.55,
    "Clay":         0.15,
    "Rocky Scree":  0.10,
    "Forest Humus": 0.70,
    "Saturated":    0.05,
}

# Population at risk estimate (people per sq km × area)
POPULATION_DENSITY = {  # persons/sq km for Uttarakhand city zones
    "Dehradun": 840, "Rishikesh": 1200, "Haridwar": 2200, "Haldwani": 1800,
    "Nainital": 650, "Almora": 240, "Pithoragarh": 180, "Tehri": 140,
    "Kedarnath": 300, "Badrinath": 120, "Joshimath": 220, "Chamoli": 160,
    "Rudraprayag": 190, "Uttarkashi": 210, "Gauchar": 170, "Guptkashi": 130,
    "DEFAULT": 200,
}


class SimulateRequest(BaseModel):
    city: str
    rainfall: float       # mm in 6h
    slope: float          # degrees
    elevation: float      # metres
    soil: Optional[str] = "Clay"
    cloudburst: Optional[bool] = False
    operator_id: Optional[str] = "SEOC-DUTY-OFFICER"


@router.post("/simulate")
async def run_simulation(payload: SimulateRequest):
    soil_perm = SOIL_PERMEABILITY.get(payload.soil or "Clay", 0.15)
    pop_density = POPULATION_DENSITY.get(payload.city, POPULATION_DENSITY["DEFAULT"])

    # ── 1. Risk matrix
    risk_score, risk_level = risk_matrix(
        rainfall_mm=payload.rainfall,
        slope_deg=payload.slope,
        elevation_m=payload.elevation,
        is_cloudburst=payload.cloudburst,
        pop_density=max(0.8, pop_density / 400),
    )

    # ── 2. Runoff velocity physics
    runoff = calculate_runoff_velocity(
        rainfall_mm=payload.rainfall,
        slope_degrees=payload.slope,
        soil_permeability=soil_perm,
    )

    # ── 3. Population at risk estimate (simplified area-based)
    area_sq_km = max(5.0, 25.0 - payload.elevation / 500)
    pop_at_risk = int(pop_density * area_sq_km * (risk_score / 100))

    # ── 4. Lead time before impact
    if runoff["velocity_ms"] > 0:
        distance_to_settlement_m = max(500, 3000 - payload.slope * 20)
        lead_time_s = distance_to_settlement_m / runoff["velocity_ms"]
        lead_time_min = max(3, int(lead_time_s / 60))
    else:
        lead_time_min = 90

    # ── 5. AI analysis (runs in thread-pool)
    import asyncio
    explanation = await asyncio.to_thread(
        analyze_risk,
        city=payload.city,
        rainfall_mm=payload.rainfall,
        slope_deg=payload.slope,
        elevation_m=payload.elevation,
        risk_score=risk_score,
        risk_level=risk_level,
        is_cloudburst=payload.cloudburst,
    )

    # ── 6. Persist to DB
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute("""
        INSERT INTO simulation_sessions
        (city_name, rainfall, slope, elevation, soil, cloudburst, risk_score, risk_level,
         pop_at_risk, runoff_velocity, lead_time_minutes, explanation, operator_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.city, payload.rainfall, payload.slope, payload.elevation,
        payload.soil, int(payload.cloudburst or False), risk_score, risk_level,
        pop_at_risk, runoff["velocity_ms"], lead_time_min,
        explanation, payload.operator_id, now,
    ))

    # Also log as incident if HIGH/CRITICAL
    if risk_level in ("HIGH", "CRITICAL"):
        conn.execute("""
            INSERT INTO incidents (type, msg, zone, priority, risk_score, is_simulated, ai_analysis, created_at)
            VALUES ('SIMULATION', ?, ?, ?, ?, 1, ?, ?)
        """, (
            f"[SIM] {risk_level} risk simulated at {payload.city}: {payload.rainfall}mm rainfall, {payload.slope}° slope.",
            payload.city, risk_level, risk_score, explanation, now,
        ))

    conn.commit()
    conn.close()

    return {
        "city": payload.city,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "populationAtRisk": pop_at_risk,
        "runoff": runoff,
        "leadTimeMinutes": lead_time_min,
        "explanation": explanation,
        "parameters": {
            "rainfall": payload.rainfall,
            "slope": payload.slope,
            "elevation": payload.elevation,
            "soil": payload.soil,
            "cloudburst": payload.cloudburst,
        },
        "timestamp": now,
    }


@router.get("/simulate/history")
def simulation_history(limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM simulation_sessions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

