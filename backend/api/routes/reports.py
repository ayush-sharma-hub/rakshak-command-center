"""Crowdsourced incident intake, verification, and map-safe hazard feed."""

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.database import get_db
from backend.services.gemini_service import extract_crowd_report

router = APIRouter(prefix="/api/reports", tags=["Crowdsourced Verification"])
PUBLIC_CONFIDENCE_THRESHOLD = 76


class CrowdReportCreate(BaseModel):
    description: str = Field(min_length=8, max_length=1200)
    lat: float = Field(ge=26.0, le=33.0, description="Uttarakhand-region latitude")
    lng: float = Field(ge=76.0, le=82.0, description="Uttarakhand-region longitude")
    location_name: str = Field(default="", max_length=200)
    has_voice: bool = False  # Placeholder metadata; no media bytes are stored.
    has_photo: bool = False  # Placeholder metadata; no media bytes are stored.


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance; avoids a spatial DB dependency."""
    radius_m = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(a))


def _calibrate_confidence(model_score: int, report: CrowdReportCreate, corroborations: int) -> int:
    """Keep Gemini confidence explainable and do not let a model alone publish hazards."""
    evidence_bonus = 8 if report.has_photo else 0
    evidence_bonus += 5 if report.has_voice else 0
    evidence_bonus += min(18, max(0, corroborations - 1) * 9)
    location_bonus = 10 if report.location_name.strip() else 4
    return max(0, min(99, round(model_score * 0.70 + evidence_bonus + location_bonus)))


@router.post("")
def submit_report(payload: CrowdReportCreate):
    """Submit a report without contaminating authoritative incident data.

    Nearby same-type reports are merged into a single corroborated record. Only
    records at or above 76 confidence become visible to the dashboard/map feed.
    """
    extracted = extract_crowd_report(
        payload.description, payload.location_name, payload.has_voice, payload.has_photo
    )
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        candidates = conn.execute(
            "SELECT * FROM crowd_reports WHERE incident_type=? AND status!='RESOLVED' ORDER BY created_at DESC LIMIT 100",
            (extracted["incident_type"],),
        ).fetchall()
        duplicate = next(
            (row for row in candidates if _distance_m(payload.lat, payload.lng, row["lat"], row["lng"]) <= 850),
            None,
        )
        if duplicate:
            corroborations = duplicate["corroboration_count"] + 1
            confidence = max(
                duplicate["confidence_score"],
                _calibrate_confidence(extracted["model_confidence"], payload, corroborations),
            )
            status = "VERIFIED" if confidence >= PUBLIC_CONFIDENCE_THRESHOLD else "PENDING_REVIEW"
            conn.execute(
                "UPDATE crowd_reports SET corroboration_count=?, confidence_score=?, status=?, updated_at=? WHERE id=?",
                (corroborations, confidence, status, now, duplicate["id"]),
            )
            conn.commit()
            return {
                "success": True, "deduplicated": True, "report_id": duplicate["id"],
                "confidence_score": confidence, "status": status,
                "publicly_visible": status == "VERIFIED",
            }

        confidence = _calibrate_confidence(extracted["model_confidence"], payload, 1)
        status = "VERIFIED" if confidence >= PUBLIC_CONFIDENCE_THRESHOLD else "PENDING_REVIEW"
        report_id = f"CR-{uuid.uuid4().hex[:8].upper()}"
        conn.execute("""
            INSERT INTO crowd_reports (
                id, description, incident_type, location_name, severity, confidence_score,
                lat, lng, has_voice, has_photo, ai_source, corroboration_count, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """, (
            report_id, payload.description.strip(), extracted["incident_type"],
            extracted.get("location_hint") or payload.location_name.strip(), extracted["severity"], confidence,
            payload.lat, payload.lng, int(payload.has_voice), int(payload.has_photo), extracted["source"],
            status, now, now,
        ))
        conn.commit()
        return {
            "success": True, "deduplicated": False, "report_id": report_id,
            "incident_type": extracted["incident_type"], "severity": extracted["severity"],
            "confidence_score": confidence, "status": status, "publicly_visible": status == "VERIFIED",
        }
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Could not process crowd report") from exc
    finally:
        conn.close()


@router.get("/verified")
def verified_reports(limit: int = 50):
    """Map/dashboard feed: deliberately excludes reports below the safety threshold."""
    safe_limit = max(1, min(limit, 100))
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, incident_type, location_name, severity, confidence_score, lat, lng,
                   has_voice, has_photo, corroboration_count, created_at
            FROM crowd_reports
            WHERE status='VERIFIED' AND confidence_score >= ?
            ORDER BY confidence_score DESC, created_at DESC LIMIT ?
        """, (PUBLIC_CONFIDENCE_THRESHOLD, safe_limit)).fetchall()
        return {"threshold": PUBLIC_CONFIDENCE_THRESHOLD, "reports": [dict(row) for row in rows]}
    finally:
        conn.close()

