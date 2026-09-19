"""
Project Rakshak — Gemini AI Service
Generates emergency broadcast text, situation summaries, and risk assessments
using Google Gemini API. Results are cached to avoid redundant API calls.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("rakshak.gemini")

# ─── Rate Limiting ────────────────────────────────────────────────────────────
_last_call_time: float = 0.0
_MIN_INTERVAL_S = 3.0   # Don't call API more than once every 3 seconds

# ─── Fallback templates (used when API is unavailable / no key) ───────────────
FALLBACK_ALERTS = {
    "CRITICAL": "⚠️ CRITICAL DISASTER ALERT — Immediate evacuation ordered. All residents in low-lying areas must move to designated higher-ground shelters immediately. Follow SEOC instructions. Do NOT cross rivers.",
    "HIGH":     "🔴 HIGH RISK WARNING — Heavy rainfall and landslide conditions detected. Restrict movement. Monitor river levels. Await further SEOC instructions.",
    "MEDIUM":   "🟡 CAUTION — Weather advisory in effect. Avoid river banks and loose-slope areas. Emergency helpline: 1077 / 112.",
    "LOW":      "🟢 ROUTINE ADVISORY — Conditions stable. Stay alert. Report any unusual activity to SEOC via helpline 1077.",
}


def _get_client():
    """Returns initialized Gemini client or None if API key not configured."""
    try:
        import google.genai as genai
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.error("Gemini client init failed: %s", exc)
        return None


def _rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL_S:
        time.sleep(_MIN_INTERVAL_S - elapsed)
    _last_call_time = time.time()


def generate_broadcast(
    risk_level: str,
    city: str,
    rainfall_mm: float,
    slope_deg: float,
    details: str = "",
    operator: str = "SEOC-DUTY-OFFICER",
) -> Dict[str, str]:
    """
    Generates a multi-language emergency broadcast message using Gemini.
    Returns: { "english": ..., "hindi": ..., "garhwali": ..., "kumaoni": ..., "source": "gemini"|"fallback" }
    """
    from backend.cache.ttl_cache import gemini_cache

    cache_key = f"broadcast:{risk_level}:{city}"
    cached = gemini_cache.get(cache_key)
    if cached:
        return cached

    client = _get_client()
    if not client:
        msg = FALLBACK_ALERTS.get(risk_level, FALLBACK_ALERTS["MEDIUM"])
        result = {
            "english": msg,
            "hindi": _hindi_fallback(risk_level, city),
            "garhwali": "⚠️ खतरो अलर्ट — SEOC निर्देश मानो।",
            "kumaoni": "⚠️ खतरे का सुचना — SEOC आदेश बटाणे।",
            "source": "fallback",
            "generated_at": datetime.utcnow().isoformat(),
        }
        gemini_cache.set(cache_key, result, ttl_seconds=300)
        return result

    prompt = f"""You are the AI Emergency Broadcast System for Uttarakhand SEOC (State Emergency Operations Centre), India.

SITUATION REPORT:
- Location: {city}, Uttarakhand (Himalayan region)
- Risk Level: {risk_level}
- Rainfall: {rainfall_mm:.1f} mm in last 6 hours
- Terrain Slope: {slope_deg:.0f}°
- Extra context: {details or "No additional details."}

TASK: Generate ONE concise, calm, authoritative emergency broadcast in EACH of these 4 languages:
1. English (clear, official, 2-3 sentences)
2. Hindi (in Devanagari script, 2-3 sentences)
3. Garhwali (Uttarakhand hill dialect, brief, 1-2 sentences using simple words)
4. Kumaoni (Uttarakhand hill dialect, brief, 1-2 sentences using simple words)

Rules:
- Do NOT use sensationalist language
- Include the emergency helpline number 1077 in at least the English version
- Mention the specific city name
- Appropriate to risk level (CRITICAL = evacuate NOW, LOW = stay alert)
- Return ONLY raw JSON — no markdown, no code blocks, no explanation

JSON format:
{{"english": "...", "hindi": "...", "garhwali": "...", "kumaoni": "..."}}"""

    try:
        _rate_limit()
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        parsed = json.loads(text)
        result = {
            **parsed,
            "source": "gemini",
            "generated_at": datetime.utcnow().isoformat(),
        }
        gemini_cache.set(cache_key, result, ttl_seconds=300)
        logger.info("Gemini broadcast generated for %s (%s)", city, risk_level)
        return result

    except json.JSONDecodeError:
        logger.error("Gemini returned non-JSON for broadcast")
        return generate_broadcast.__wrapped__(risk_level, city, rainfall_mm, slope_deg, details)  # type: ignore
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        fallback_msg = FALLBACK_ALERTS.get(risk_level, FALLBACK_ALERTS["MEDIUM"])
        return {
            "english": fallback_msg,
            "hindi": _hindi_fallback(risk_level, city),
            "garhwali": "⚠️ SEOC अलर्ट — निर्देश मानो।",
            "kumaoni": "⚠️ SEOC अलर्ट — आदेश बटाणे।",
            "source": "fallback_error",
            "generated_at": datetime.utcnow().isoformat(),
        }


def analyze_risk(
    city: str,
    rainfall_mm: float,
    slope_deg: float,
    elevation_m: float,
    risk_score: int,
    risk_level: str,
    is_cloudburst: bool,
) -> str:
    """
    Returns a short AI-generated situation analysis (2-3 sentences, English only).
    Used for simulation reports and incident cards.
    """
    from backend.cache.ttl_cache import gemini_cache

    cache_key = f"risk-analysis:{city}:{risk_score}"
    cached = gemini_cache.get(cache_key)
    if cached:
        return cached

    client = _get_client()
    if not client:
        return _fallback_analysis(risk_level, city, rainfall_mm)

    prompt = f"""As a Himalayan disaster risk analyst, write a 2-sentence technical assessment for a SEOC duty officer.

Parameters:
- City: {city}
- Rainfall: {rainfall_mm:.0f} mm (6h)
- Slope: {slope_deg:.0f}°, Elevation: {elevation_m:.0f} m
- Risk Score: {risk_score}/100
- Risk Level: {risk_level}
- Cloudburst Detected: {is_cloudburst}

Write like a field expert (no AI language). Be specific about the dominant hazard mechanism. End with recommended immediate action.
Maximum 60 words."""

    try:
        _rate_limit()
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        analysis = response.text.strip()
        gemini_cache.set(cache_key, analysis, ttl_seconds=300)
        return analysis
    except Exception as exc:
        logger.error("Gemini risk analysis failed: %s", exc)
        return _fallback_analysis(risk_level, city, rainfall_mm)


def _hindi_fallback(risk_level: str, city: str) -> str:
    templates = {
        "CRITICAL": f"⚠️ {city} में आपदा अलर्ट — तत्काल ऊँची भूमि पर जाएं। SEOC हेल्पलाइन: 1077।",
        "HIGH":     f"🔴 {city} में भारी वर्षा की चेतावनी। नदी किनारों से दूर रहें। हेल्पलाइन: 1077।",
        "MEDIUM":   f"🟡 {city} — मौसम सावधानी चेतावनी। सतर्क रहें। 1077 पर संपर्क करें।",
        "LOW":      f"🟢 {city} — स्थिति सामान्य। सतर्क रहें।",
    }
    return templates.get(risk_level, templates["MEDIUM"])


def _fallback_analysis(risk_level: str, city: str, rainfall: float) -> str:
    if risk_level in ("CRITICAL", "HIGH"):
        return (
            f"Sustained precipitation of {rainfall:.0f}mm over {city} has saturated hill slopes "
            f"beyond safe thresholds. Shallow landslide initiation and debris-flow mobilization "
            f"are imminent. Deploy NDRF/SDRF units and initiate mandatory evacuation of riverine settlements."
        )
    return (
        f"Rainfall of {rainfall:.0f}mm recorded near {city} remains within manageable range. "
        f"Monitor river gauge levels closely and maintain SDRF units on standby deployment readiness."
    )


# ─── Crowdsourced incident verification ──────────────────────────────────────
def extract_crowd_report(
    description: str,
    location_name: str,
    has_voice: bool = False,
    has_photo: bool = False,
) -> Dict[str, Any]:
    """Classify a public report into a small, safe JSON contract.

    Gemini is used only as an extractor; geographic coordinates remain supplied
    by the reporting client and confidence is calibrated by the route/report
    service. A deterministic fallback keeps the feature usable without a key.
    """
    fallback = _fallback_crowd_report(description, location_name)
    client = _get_client()
    if not client:
        return {**fallback, "source": "fallback"}

    prompt = f"""You classify disaster field reports for Uttarakhand SEOC.
Return ONLY a JSON object, no markdown. Do not invent facts.

Report text: {description[:1200]}
Location label: {location_name[:200] or 'not supplied'}
Voice evidence supplied: {has_voice}
Photo evidence supplied: {has_photo}

Use exactly these keys:
{{"incident_type":"ROAD_BLOCKED|BRIDGE_DAMAGED|LANDSLIDE|FLOOD|POWER_OUTAGE|SOS|OTHER", "severity":"LOW|MEDIUM|HIGH|CRITICAL", "location_hint":"short location or empty", "model_confidence":0}}
model_confidence must be an integer 0-100 reflecting only how clearly the report supports the classification."""
    try:
        _rate_limit()
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        parsed = json.loads(text)
        incident_type = str(parsed.get("incident_type", "OTHER")).upper()
        if incident_type not in {"ROAD_BLOCKED", "BRIDGE_DAMAGED", "LANDSLIDE", "FLOOD", "POWER_OUTAGE", "SOS", "OTHER"}:
            incident_type = "OTHER"
        severity = str(parsed.get("severity", "MEDIUM")).upper()
        if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            severity = "MEDIUM"
        return {
            "incident_type": incident_type,
            "severity": severity,
            "location_hint": str(parsed.get("location_hint", location_name))[:200],
            "model_confidence": max(0, min(100, int(parsed.get("model_confidence", 55)))),
            "source": "gemini",
        }
    except Exception as exc:
        logger.warning("Crowd report Gemini extraction failed: %s", exc)
        return {**fallback, "source": "fallback_error"}


def _fallback_crowd_report(description: str, location_name: str) -> Dict[str, Any]:
    """Conservative keyword classifier used when Gemini is offline."""
    text = description.lower()
    rules = [
        ("BRIDGE_DAMAGED", ("bridge", "pul", "collapse")),
        ("ROAD_BLOCKED", ("road blocked", "road closed", "highway", "traffic")),
        ("LANDSLIDE", ("landslide", "debris", "rockfall", "slope")),
        ("FLOOD", ("flood", "river", "water level", "flash flood")),
        ("POWER_OUTAGE", ("power", "electricity", "transformer")),
        ("SOS", ("help", "trapped", "injured", "sos")),
    ]
    incident_type = next((kind for kind, words in rules if any(word in text for word in words)), "OTHER")
    severity = "CRITICAL" if any(word in text for word in ("trapped", "collapsed", "life threatening")) else "HIGH" if any(word in text for word in ("blocked", "flood", "landslide")) else "MEDIUM"
    return {"incident_type": incident_type, "severity": severity, "location_hint": location_name[:200], "model_confidence": 58}
