"""OSRM-backed route planning with a local verified-hazard exclusion check."""

import math
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from backend.core.database import get_db

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
HAZARD_RADIUS_M = 700


def _distance_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    radius_m = 6_371_000
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    hav = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(hav))


def _point_to_segment_distance_m(point: Tuple[float, float], start: Tuple[float, float], end: Tuple[float, float]) -> float:
    """Local equirectangular approximation; accurate enough for sub-km exclusion zones."""
    mean_lat = math.radians((point[0] + start[0] + end[0]) / 3)
    scale_lat, scale_lng = 111_320.0, 111_320.0 * math.cos(mean_lat)
    px, py = (point[1] - start[1]) * scale_lng, (point[0] - start[0]) * scale_lat
    ex, ey = (end[1] - start[1]) * scale_lng, (end[0] - start[0]) * scale_lat
    length_sq = ex * ex + ey * ey
    if not length_sq:
        return math.hypot(px, py)
    t = max(0.0, min(1.0, (px * ex + py * ey) / length_sq))
    return math.hypot(px - t * ex, py - t * ey)


def active_hazards() -> List[Dict[str, Any]]:
    """Return only trusted crowd reports plus authoritative danger-basin zones."""
    conn = get_db()
    try:
        reports = [dict(row) for row in conn.execute("""
            SELECT id, incident_type AS type, location_name AS name, severity, confidence_score, lat, lng
            FROM crowd_reports WHERE status='VERIFIED' AND confidence_score >= 76
        """).fetchall()]
        basins = [dict(row) for row in conn.execute("""
            SELECT id, 'FLOOD_BASIN' AS type, river AS name, status AS severity, 100 AS confidence_score, lat, lng
            FROM river_basins WHERE status IN ('WARNING', 'DANGER') AND lat IS NOT NULL AND lng IS NOT NULL
        """).fetchall()]
        return reports + basins
    finally:
        conn.close()


def _route_intersections(coordinates: List[List[float]], hazards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hits = []
    for hazard in hazards:
        point = (hazard["lat"], hazard["lng"])
        for current, following in zip(coordinates, coordinates[1:]):
            # OSRM uses [longitude, latitude].
            distance = _point_to_segment_distance_m(point, (current[1], current[0]), (following[1], following[0]))
            if distance <= HAZARD_RADIUS_M:
                hits.append({**hazard, "clearance_m": round(distance)})
                break
    return hits


def _detour_waypoint(start: Tuple[float, float], end: Tuple[float, float], hazard: Dict[str, Any]) -> Tuple[float, float]:
    """Place a point 1.4 km perpendicular to the hazard, on the less direct side."""
    lat, lng = hazard["lat"], hazard["lng"]
    scale_lng = 111_320.0 * math.cos(math.radians(lat))
    dx, dy = (end[1] - start[1]) * scale_lng, (end[0] - start[0]) * 111_320.0
    length = max(math.hypot(dx, dy), 1.0)
    # Perpendicular unit vector. Pick direction away from route midpoint.
    nx, ny = -dy / length, dx / length
    mid_lat, mid_lng = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    toward_mid = (mid_lng - lng) * nx * scale_lng + (mid_lat - lat) * ny * 111_320.0
    if toward_mid > 0:
        nx, ny = -nx, -ny
    offset_m = HAZARD_RADIUS_M * 2
    return (lat + (ny * offset_m / 111_320.0), lng + (nx * offset_m / scale_lng))


async def calculate_safe_route(start: Tuple[float, float], destination: Tuple[float, float]) -> Dict[str, Any]:
    """Request OSRM candidates, reject any that intersect active exclusion zones.

    OSRM does not accept custom avoid-polygons on its public endpoint, therefore
    the engine adds deterministic detour waypoints and validates the returned
    geometry locally. If it cannot find a clear geometry it *refuses* to label
    the route safe rather than returning a hazardous route.
    """
    hazards = active_hazards()
    candidate_waypoints: List[Tuple[float, float]] = []
    attempts = 0
    route: Optional[Dict[str, Any]] = None
    intersections: List[Dict[str, Any]] = []

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
        while attempts < 3:
            points = [start, *candidate_waypoints, destination]
            coordinate_string = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in points)
            url = f"{OSRM_BASE_URL}/{coordinate_string}?overview=full&geometries=geojson&alternatives=true&steps=false"
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"OSRM routing service returned {response.status}")
                payload = await response.json()
            candidates = payload.get("routes", [])
            if not candidates:
                raise RuntimeError("OSRM could not find a drivable route")
            safe = None
            for candidate in candidates:
                hits = _route_intersections(candidate["geometry"]["coordinates"], hazards)
                if not hits:
                    safe = candidate
                    intersections = []
                    break
                intersections = hits
            if safe:
                route = safe
                break
            if not intersections:
                break
            detour = _detour_waypoint(start, destination, intersections[0])
            if any(_distance_m(detour, point) < 100 for point in candidate_waypoints):
                break
            candidate_waypoints.append(detour)
            attempts += 1

    if not route:
        return {
            "safe": False, "route_confidence": 0, "reason": "No verified-safe route could be calculated.",
            "hazards_on_route": intersections, "hazard_count": len(hazards),
        }

    confidence = max(55, 100 - len(candidate_waypoints) * 9 - max(0, len(hazards) - 1) * 2)
    return {
        "safe": True, "route_confidence": confidence, "distance_m": round(route["distance"]),
        "duration_s": round(route["duration"]), "geometry": route["geometry"],
        "hazards_on_route": [], "hazard_count": len(hazards), "detour_count": len(candidate_waypoints),
        "routing_provider": "OSRM public demo service",
    }
