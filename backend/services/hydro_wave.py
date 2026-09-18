"""
Project Rakshak — Hydrodynamic Wave Propagation Engine
Calculates downstream flood wave arrival timelines, peak surge velocities,
and evacuation lead times across Himalayan river networks (Manning's Equation).
Directly satisfies SIH #2619 Actionable Evacuation Lead-Time requirements.
"""

import math
from typing import Dict, Any, List


# Calibrated Himalayan Valley Corridor Transects
MANDAKINI_CORRIDOR_TRANSECTS = [
    {
        "name": "Chorabari Glacial Catchment",
        "distance_km": 0.0,
        "elevation_m": 3850,
        "population": 0,
        "bridge_type": "None / Glacial Moraine",
        "safe_elevation_offset_m": 0,
        "is_origin": True
    },
    {
        "name": "Kedarnath Shrine Settlement",
        "distance_km": 2.5,
        "elevation_m": 3583,
        "population": 14000,
        "bridge_type": "Concrete Footbridge (Mandakini)",
        "safe_elevation_offset_m": 18,
        "is_origin": False
    },
    {
        "name": "Lincheli Mountain Camp",
        "distance_km": 6.8,
        "elevation_m": 3100,
        "population": 2500,
        "bridge_type": "Suspension Trail Bridge",
        "safe_elevation_offset_m": 22,
        "is_origin": False
    },
    {
        "name": "Rambara Gorge Bottleneck",
        "distance_km": 11.2,
        "elevation_m": 2800,
        "population": 3500,
        "bridge_type": "Pedestrian River Crossing",
        "safe_elevation_offset_m": 25,
        "is_origin": False
    },
    {
        "name": "Gaurikund Highway Gate",
        "distance_km": 18.0,
        "elevation_m": 1982,
        "population": 8500,
        "bridge_type": "Double-Lane Motor Bridge",
        "safe_elevation_offset_m": 30,
        "is_origin": False
    },
    {
        "name": "Sonprayag Confluence Base",
        "distance_km": 23.5,
        "elevation_m": 1829,
        "population": 7500,
        "bridge_type": "BRO Heavy Steel Girder Bridge",
        "safe_elevation_offset_m": 35,
        "is_origin": False
    },
    {
        "name": "Guptkashi / Kund Valley",
        "distance_km": 36.0,
        "elevation_m": 1319,
        "population": 22000,
        "bridge_type": "Major Highway Span NH-107",
        "safe_elevation_offset_m": 45,
        "is_origin": False
    },
    {
        "name": "Rudraprayag Sangam (Alaknanda Confluence)",
        "distance_km": 72.0,
        "elevation_m": 895,
        "population": 28000,
        "bridge_type": "Triple-Arch River Confluence Bridge",
        "safe_elevation_offset_m": 50,
        "is_origin": False
    },
]


def calculate_wave_propagation(
    corridor: str = "Mandakini",
    rainfall_mm: float = 120.0,
    cloudburst: bool = True,
    channel_roughness_n: float = 0.052  # Rough boulder bed typical of Garhwal
) -> Dict[str, Any]:
    """
    Computes flood wave front velocity and arrival times along downstream river transects.
    v = (1/n) * (R^(2/3)) * (S^(1/2))
    where S is channel bed slope (drop/distance), R is hydraulic radius.
    """
    transects = MANDAKINI_CORRIDOR_TRANSECTS
    results: List[Dict[str, Any]] = []

    # Discharge factor based on precipitation and cloudburst
    burst_multiplier = 2.4 if cloudburst else 1.0
    intensity_factor = min(3.5, max(0.5, (rainfall_mm / 75.0) * burst_multiplier))

    cumulative_minutes = 0.0
    prev_km = 0.0
    prev_elev = transects[0]["elevation_m"]

    for i, t in enumerate(transects):
        if i == 0:
            results.append({
                "settlement": t["name"],
                "distance_km": 0.0,
                "elevation_m": t["elevation_m"],
                "wave_arrival_minutes": 0,
                "lead_time_minutes": 0,
                "surge_velocity_mps": 0.0,
                "surge_height_m": 0.0,
                "inundation_prob_pct": 100 if cloudburst else 60,
                "evacuation_status": "ORIGIN_IMPACT",
                "evacuation_deadline": "IMMEDIATE",
                "bridge_status": "HIGH_SURGE",
                "population": t["population"],
            })
            continue

        dist_segment_m = (t["distance_km"] - prev_km) * 1000.0
        elev_drop_m = max(10.0, prev_elev - t["elevation_m"])
        slope = max(0.01, elev_drop_m / dist_segment_m)  # Bed slope S

        # Hydraulic radius R estimated from channel shape (narrow gorge = ~3.5 to 5.5m depth)
        hydraulic_radius_r = 3.2 * (intensity_factor ** 0.35)

        # Manning's equation velocity (m/s)
        velocity_mps = (1.0 / channel_roughness_n) * (hydraulic_radius_r ** (2.0 / 3.0)) * math.sqrt(slope)
        velocity_mps = round(min(18.5, max(3.5, velocity_mps * (intensity_factor ** 0.25))), 1)

        # Travel time for this segment (seconds -> minutes)
        segment_seconds = dist_segment_m / velocity_mps
        cumulative_minutes += (segment_seconds / 60.0)
        arrival_min = round(cumulative_minutes)

        # Surge height attenuation downstream
        attenuation = math.exp(-0.015 * t["distance_km"])
        peak_surge_height = round(max(1.8, (8.5 * intensity_factor * attenuation)), 1)

        # Inundation probability based on surge height and safe offset
        inundation_prob = min(98, max(15, int((peak_surge_height / max(1, t["safe_elevation_offset_m"] * 0.4)) * 100)))

        # Evacuation lead time window
        lead_time = max(0, arrival_min - 8)  # minus 8 minutes for warning relay delay

        if arrival_min <= 20:
            status = "IMMINENT_CRITICAL"
            deadline = f"Within {lead_time} mins"
            bridge = "IMPASSABLE / WASH RISK"
        elif arrival_min <= 60:
            status = "URGENT_EVACUATION"
            deadline = f"{lead_time} mins window"
            bridge = "RESTRICTED / EMERGENCY ONLY"
        elif arrival_min <= 150:
            status = "CONTROLLED_EGRESS"
            deadline = f"{lead_time} mins window"
            bridge = "CONVOY ESCORT ACTIVE"
        else:
            status = "DAM_SPILLWAY_PREP"
            deadline = f"{lead_time} mins window"
            bridge = "OPEN WITH SENSOR MONITOR"

        results.append({
            "settlement": t["name"],
            "distance_km": t["distance_km"],
            "elevation_m": t["elevation_m"],
            "wave_arrival_minutes": arrival_min,
            "lead_time_minutes": lead_time,
            "surge_velocity_mps": velocity_mps,
            "surge_height_m": peak_surge_height,
            "inundation_prob_pct": inundation_prob,
            "evacuation_status": status,
            "evacuation_deadline": deadline,
            "bridge_status": bridge,
            "population": t["population"],
        })

        prev_km = t["distance_km"]
        prev_elev = t["elevation_m"]

    return {
        "corridor": corridor,
        "origin": transects[0]["name"],
        "channel_roughness": channel_roughness_n,
        "rainfall_mm": rainfall_mm,
        "cloudburst": cloudburst,
        "total_reach_km": transects[-1]["distance_km"],
        "max_surge_velocity_mps": max(r["surge_velocity_mps"] for r in results),
        "total_population_at_risk": sum(r["population"] for r in results),
        "transects": results
    }
