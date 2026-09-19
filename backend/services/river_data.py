"""
Project Rakshak — Real River Basin Data Service
================================================
Fetches LIVE data from:
1. Open-Meteo API (FREE, no key) — upstream precipitation for each river basin
2. Physics-based river level estimation using rational method hydrology
3. CWC danger/warning/normal levels (hardcoded from official CWC bulletins)
4. USGS/Global Runoff Data Centre constants for Himalayan basins

This replaces simulated river data with real atmospheric observations.
River LEVEL is derived from upstream catchment rainfall using:
    Q = C × I × A  (Rational Method)
    H = f(Q, channel geometry) (Manning's equation)

No API key required. Completely FREE and open.
"""

import urllib.request
import json
import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("rakshak.river")

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 8

# ── RIVER BASIN DEFINITIONS ────────────────────────────────────────────────────
# Each river basin: upstream catchment monitoring points + CWC official thresholds
# CWC MSL (Mean Sea Level) elevations in meters
RIVER_BASINS: Dict[str, Dict] = {
    "Mandakini": {
        "db_name": "Mandakini at Rudraprayag",
        "gauge_station": "Rudraprayag Gauge Station CWC",
        "lat": 30.2844, "lng": 78.9811,
        "catchment_km2": 2050,          # Mandakini basin area
        "channel_width_m": 65,          # avg at Rudraprayag
        "runoff_coeff": 0.62,           # Himalayan steep rocky terrain
        "msl_datum_m": 623.0,           # Bed level datum (m MSL)
        "normal_level_m": 1.8,
        "warning_level_m": 625.5,       # CWC official warning (m MSL)
        "danger_level_m": 627.0,        # CWC official danger (m MSL)
        "extreme_level_m": 629.0,       # CWC high flood level (m MSL)
        # Upstream monitoring points for precipitation fetch
        "upstream_points": [
            {"name": "Kedarnath", "lat": 30.7346, "lng": 79.0669, "weight": 0.45},
            {"name": "Gaurikund",  "lat": 30.6558, "lng": 79.0289, "weight": 0.35},
            {"name": "Sonprayag", "lat": 30.6375, "lng": 78.9950, "weight": 0.20},
        ]
    },
    "Alaknanda": {
        "db_name": "Alaknanda at Joshimath",
        "gauge_station": "Joshimath Gauge Station",
        "lat": 30.5506, "lng": 79.5660,
        "catchment_km2": 5795,
        "channel_width_m": 120,
        "runoff_coeff": 0.55,
        "msl_datum_m": 1146.0,
        "normal_level_m": 2.2,
        "warning_level_m": 1150.0,
        "danger_level_m": 1152.5,
        "extreme_level_m": 1155.0,
        "upstream_points": [
            {"name": "Badrinath",  "lat": 30.7433, "lng": 79.4938, "weight": 0.40},
            {"name": "Chamoli",    "lat": 30.4095, "lng": 79.3344, "weight": 0.35},
            {"name": "Joshimath", "lat": 30.5506, "lng": 79.5660, "weight": 0.25},
        ]
    },
    "Bhagirathi": {
        "db_name": "Bhagirathi at Uttarkashi",
        "gauge_station": "Uttarkashi CWC Station",
        "lat": 30.7268, "lng": 78.4354,
        "catchment_km2": 7040,
        "channel_width_m": 90,
        "runoff_coeff": 0.50,
        "msl_datum_m": 1118.0,
        "normal_level_m": 2.0,
        "warning_level_m": 1122.0,
        "danger_level_m": 1125.0,
        "extreme_level_m": 1127.5,
        "upstream_points": [
            {"name": "Uttarkashi", "lat": 30.7268, "lng": 78.4354, "weight": 0.50},
            {"name": "Tehri",      "lat": 30.3804, "lng": 78.4800, "weight": 0.30},
            {"name": "Mussoorie", "lat": 30.4598, "lng": 78.0644, "weight": 0.20},
        ]
    },
    "Tehri": {
        "db_name": "Tehri Dam Reservoir",
        "gauge_station": "THDC Tehri Control Room",
        "lat": 30.3804, "lng": 78.4800,
        "catchment_km2": 7500,
        "channel_width_m": 350,
        "runoff_coeff": 0.45,
        "msl_datum_m": 815.0,
        "normal_level_m": 3.5,
        "warning_level_m": 825.0,
        "danger_level_m": 830.0,
        "extreme_level_m": 835.0,
        "upstream_points": [
            {"name": "Tehri",     "lat": 30.3804, "lng": 78.4800, "weight": 0.50},
            {"name": "Mussoorie", "lat": 30.4598, "lng": 78.0644, "weight": 0.50},
        ]
    },
    "Kali": {
        "db_name": "Kali at Dharchula",
        "gauge_station": "SSB Dharchula Station",
        "lat": 29.8519, "lng": 80.5284,
        "catchment_km2": 4500,
        "channel_width_m": 70,
        "runoff_coeff": 0.55,
        "msl_datum_m": 938.5,
        "normal_level_m": 1.7,
        "warning_level_m": 941.5,
        "danger_level_m": 943.0,
        "extreme_level_m": 945.5,
        "upstream_points": [
            {"name": "Dharchula",   "lat": 29.8519, "lng": 80.5284, "weight": 0.50},
            {"name": "Pithoragarh", "lat": 29.5829, "lng": 80.2182, "weight": 0.50},
        ]
    },
}


# In-memory cache: river -> {data, fetched_at}
_river_cache: Dict[str, Any] = {}
# Point-level cache: (lat, lng) -> (precip_mm, timestamp)
_point_cache: Dict[str, tuple[float, datetime]] = {}
CACHE_TTL_SECONDS = 600  # 10 min

from concurrent.futures import ThreadPoolExecutor


def _fetch_single_point_precip(point: Dict) -> float:
    """Fetch precipitation for a single point with caching and timeout resilience."""
    cache_key = f"{point['lat']:.4f},{point['lng']:.4f}"
    now = datetime.now(timezone.utc)
    if cache_key in _point_cache:
        val, ts = _point_cache[cache_key]
        if (now - ts).total_seconds() < CACHE_TTL_SECONDS:
            return val

    try:
        url = (
            f"{OPEN_METEO_BASE}?"
            f"latitude={point['lat']}&longitude={point['lng']}"
            f"&hourly=precipitation,rain&current_weather=true"
            f"&timezone=Asia%2FKolkata&forecast_days=1"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "RakshakSEOC/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode())

        hourly = raw.get("hourly", {})
        now_hour = datetime.now(timezone.utc).hour
        precip_list = hourly.get("precipitation", [])
        precip = precip_list[now_hour] if now_hour < len(precip_list) else 0.0

        # Check last 3 hours for accumulated effect
        recent_hours = precip_list[max(0, now_hour - 3):now_hour + 1]
        avg_recent = sum(recent_hours) / len(recent_hours) if recent_hours else precip
        effective_precip = round(max(precip, avg_recent), 2)

        _point_cache[cache_key] = (effective_precip, now)
        return effective_precip
    except Exception as e:
        logger.warning(f"[River] Error fetching precip for {point['name']}: {e}")
        # If cached value exists even if old, return it
        if cache_key in _point_cache:
            return _point_cache[cache_key][0]
        return 0.0


def _fetch_upstream_precip(upstream_points: List[Dict]) -> float:
    """
    Fetch weighted average precipitation (mm/hr) from upstream monitoring points
    using Open-Meteo API in parallel. Returns weighted average across all catchment points.
    """
    total_precip = 0.0
    total_weight = sum(p["weight"] for p in upstream_points)

    with ThreadPoolExecutor(max_workers=min(4, len(upstream_points))) as executor:
        results = list(executor.map(_fetch_single_point_precip, upstream_points))

    for point, precip in zip(upstream_points, results):
        total_precip += precip * point["weight"]

    if total_weight > 0:
        return total_precip / total_weight
    return 0.0


def _estimate_river_level(basin: Dict, precip_mmhr: float) -> Dict[str, float]:
    """
    Estimate river discharge and water level using the Rational Method.

    Q = C × I × A / 360   (Q in m³/s, I in mm/hr, A in km²)
    H = (Q / (W × sqrt(S) / n)) ^ (3/5)  — Manning's approximation

    Parameters based on Himalayan river studies (IMD/NIH publications).
    """
    C = basin["runoff_coeff"]
    A = basin["catchment_km2"]
    W = basin["channel_width_m"]

    # Rational method: Q = C × I × A / 360
    discharge_m3s = (C * precip_mmhr * A) / 360.0

    # Add baseflow (dry season minimum discharge for perennial Himalayan rivers)
    baseflow = A * 0.008  # ~8 L/s per km² baseflow
    total_q = discharge_m3s + baseflow

    # Manning's equation simplified: H = (Q × n) / (W × S^0.5) ^ (3/5)
    # Using n=0.04 (natural mountain channel), S=0.012 (steep Himalayan slope)
    n_manning = 0.04
    slope = 0.012
    H = (total_q * n_manning / (W * math.sqrt(slope))) ** (3 / 5)

    # Add natural baseline level offset
    gauge_height = H + basin["normal_level_m"] * 0.4
    msl_level = round(basin["msl_datum_m"] + gauge_height, 2)

    return {
        "discharge_m3s": round(total_q, 1),
        "gauge_height_m": round(gauge_height, 2),
        "water_level_m": msl_level,
        "precip_upstream_mmhr": round(precip_mmhr, 2),
    }


def _get_alert_status(basin: Dict, level_msl: float) -> Dict[str, str]:
    """Classify water level against CWC official thresholds (m MSL)."""
    if level_msl >= basin["extreme_level_m"]:
        return {
            "status": "EXTREME_FLOOD",
            "color": "red",
            "action": "IMMEDIATE EVACUATION — All downstream zones. Extreme flood level exceeded.",
            "risk": "CRITICAL"
        }
    elif level_msl >= basin["danger_level_m"]:
        return {
            "status": "DANGER",
            "color": "orange",
            "action": "EVACUATE lower settlements. Danger level breached. SDRF on standby.",
            "risk": "HIGH"
        }
    elif level_msl >= basin["warning_level_m"]:
        return {
            "status": "WARNING",
            "color": "yellow",
            "action": "Alert all riverside villages. Warning level reached. Monitor closely.",
            "risk": "MEDIUM"
        }
    else:
        return {
            "status": "NORMAL",
            "color": "green",
            "action": "Normal river flow. Continue regular monitoring.",
            "risk": "LOW"
        }


def fetch_river_data(basin_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch real-time river data for a given basin using upstream precipitation
    from Open-Meteo API + hydrological estimation.
    """
    # Check cache
    cached = _river_cache.get(basin_name)
    if cached:
        elapsed = (datetime.now(timezone.utc) - cached["_cached_at"]).total_seconds()
        if elapsed < CACHE_TTL_SECONDS:
            return {k: v for k, v in cached.items() if k != "_cached_at"}

    basin = RIVER_BASINS.get(basin_name)
    if not basin:
        logger.warning(f"[River] Unknown basin: {basin_name}")
        return None

    logger.info(f"[River] Fetching real upstream precipitation for {basin_name}...")

    # Fetch real precipitation from upstream points via Open-Meteo
    precip = _fetch_upstream_precip(basin["upstream_points"])

    # Estimate river level using hydrology
    hydro = _estimate_river_level(basin, precip)
    level_msl = hydro["water_level_m"]
    discharge = hydro["discharge_m3s"]

    # Classify alert status
    alert = _get_alert_status(basin, level_msl)

    result = {
        "basin": basin_name,
        "db_name": basin.get("db_name", basin_name),
        "river": basin.get("db_name", basin_name),
        "gauge_station": basin["gauge_station"],
        "lat": basin["lat"],
        "lng": basin["lng"],
        "current_level": level_msl,
        "water_level_m": level_msl,
        "gauge_height_m": hydro["gauge_height_m"],
        "discharge_m3s": discharge,
        "upstream_precip_mmhr": precip,
        "normal_level_m": basin["normal_level_m"],
        "warning_level_m": basin["warning_level_m"],
        "danger_level_m": basin["danger_level_m"],
        "extreme_level_m": basin["extreme_level_m"],
        "status": alert["status"],
        "risk": alert["risk"],
        "color": alert["color"],
        "action_required": alert["action"],
        "data_source": "Open-Meteo (upstream precip) + Rational Method hydrology",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    # Cache it
    _river_cache[basin_name] = {**result, "_cached_at": datetime.now(timezone.utc)}
    return result



def fetch_all_rivers() -> List[Dict[str, Any]]:
    """Fetch real-time data for all monitored river basins."""
    results = []
    for basin_name in RIVER_BASINS:
        data = fetch_river_data(basin_name)
        if data:
            results.append(data)
    return results


def get_basin_names() -> List[str]:
    return list(RIVER_BASINS.keys())

