"""
Project Rakshak — Geospatial Engine
Haversine distance, bearing calculation, ETA estimation, and auto-responder assignment.
"""

import math
from typing import Optional, Dict, Any, List, Tuple


EARTH_RADIUS_KM = 6371.0

# Average road-speed estimates in mountain terrain (km/h)
UNIT_SPEEDS_KMPH = {
    "NDRF": 45,   # River inflatables + jeeps on mountain roads
    "SDRF": 50,   # High-altitude jeeps
    "IAF": 180,   # Helicopter
    "BRO": 25,    # Heavy machinery
    "POLICE": 55,
    "DEFAULT": 40,
}

# Terrain difficulty multiplier (mountain roads are ~1.4× slower than straight-line distance)
TERRAIN_FACTOR = 1.4


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Returns the great-circle distance in kilometers between two GPS coordinates.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return round(EARTH_RADIUS_KM * c, 2)


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Returns compass bearing (degrees, 0=North) from point 1 to point 2.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    angle = math.degrees(math.atan2(x, y))
    return (angle + 360) % 360


def eta_minutes(distance_km: float, unit_type: str = "DEFAULT") -> int:
    """
    Returns ETA in minutes factoring mountain terrain multiplier.
    """
    speed = UNIT_SPEEDS_KMPH.get(unit_type, UNIT_SPEEDS_KMPH["DEFAULT"])
    road_dist = distance_km * TERRAIN_FACTOR
    return max(5, int((road_dist / speed) * 60))


def cardinal_direction(degrees: float) -> str:
    """Converts compass degrees to 8-point cardinal direction abbreviation."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((degrees + 22.5) / 45) % 8
    return dirs[idx]


def find_nearest_unit(
    sos_lat: float,
    sos_lng: float,
    units: List[Dict[str, Any]],
    exclude_statuses: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Returns the nearest available field unit to a given SOS coordinate.
    Excludes units whose status is in `exclude_statuses`.
    Each unit dict must have keys: id, lat, lng, unit_type, status.
    """
    if exclude_statuses is None:
        exclude_statuses = ["DEPLOYED", "OFFLINE"]

    best = None
    best_dist = float("inf")

    for unit in units:
        if unit.get("status") in exclude_statuses:
            continue
        dist = haversine(sos_lat, sos_lng, unit["lat"], unit["lng"])
        if dist < best_dist:
            best_dist = dist
            best = {
                **unit,
                "distance_km": dist,
                "eta_minutes": eta_minutes(dist, unit.get("unit_type", "DEFAULT")),
                "bearing": bearing(unit["lat"], unit["lng"], sos_lat, sos_lng),
                "direction": cardinal_direction(
                    bearing(unit["lat"], unit["lng"], sos_lat, sos_lng)
                ),
            }
    return best


def calculate_runoff_velocity(
    rainfall_mm: float,
    slope_degrees: float,
    soil_permeability: float = 0.3,
    catchment_area_sq_km: float = 25.0,
) -> Dict[str, float]:
    """
    Estimates surface runoff velocity and peak flow using a simplified
    rational method for steep Himalayan terrain.

    Returns: {"runoff_m3ps": float, "velocity_ms": float, "time_of_concentration_min": float}
    """
    slope_frac = math.tan(math.radians(slope_degrees))
    runoff_coeff = min(0.95, 0.4 + (1 - soil_permeability) * 0.3 + slope_frac * 0.2)
    rainfall_m_per_hr = rainfall_mm / 1000
    area_sq_m = catchment_area_sq_km * 1e6
    runoff_m3ps = (runoff_coeff * rainfall_m_per_hr * area_sq_m) / 3600
    velocity_ms = 2.5 * math.sqrt(slope_frac) * (rainfall_mm / 50) ** 0.3
    tc_min = 0.0195 * (catchment_area_sq_km ** 0.77) / (slope_frac ** 0.385)
    return {
        "runoff_m3ps": round(runoff_m3ps, 2),
        "velocity_ms": round(velocity_ms, 3),
        "time_of_concentration_min": round(tc_min, 1),
    }


def risk_matrix(
    rainfall_mm: float,
    slope_deg: float,
    elevation_m: float,
    is_cloudburst: bool = False,
    pop_density: float = 1.0,
) -> Tuple[int, str]:
    """
    Returns (risk_score 0-100, risk_level 'LOW'|'MEDIUM'|'HIGH'|'CRITICAL')
    based on a weighted multi-factor risk matrix for Himalayan terrain.
    """
    # ── Rainfall factor (weight 35%)
    if rainfall_mm > 200:
        r = 35
    elif rainfall_mm > 100:
        r = 28
    elif rainfall_mm > 50:
        r = 18
    elif rainfall_mm > 20:
        r = 10
    else:
        r = 4

    # ── Slope factor (weight 30%)
    if slope_deg > 45:
        s = 30
    elif slope_deg > 35:
        s = 24
    elif slope_deg > 25:
        s = 16
    elif slope_deg > 15:
        s = 9
    else:
        s = 4

    # ── Elevation factor (weight 20%) — high elevation = more glacial melt risk
    if elevation_m > 4000:
        e = 20
    elif elevation_m > 3000:
        e = 15
    elif elevation_m > 2000:
        e = 10
    elif elevation_m > 1000:
        e = 6
    else:
        e = 3

    # ── Cloudburst bonus (weight 15%)
    cb = 15 if is_cloudburst else 0

    score = r + s + e + cb
    score = min(100, int(score * pop_density))

    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 25:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level

