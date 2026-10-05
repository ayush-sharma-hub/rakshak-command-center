"""
================================================================================
     TEST SUITE: Autonomous Sentinel System (backend/services/sentinel_service.py)
================================================================================
"""

import sys
import asyncio
from unittest.mock import AsyncMock, patch

sys.path.insert(0, r"C:\Users\rikwa\rakshak-new")

from fastapi.testclient import TestClient
from main import app
from backend.services.sentinel_service import (
    HIGH_RISK_ZONES,
    get_sentinel_status,
    log_severe_threat_terminal,
    create_sentinel_alert,
    run_sentinel_cycle,
)
from backend.core.database import get_db

client = TestClient(app)

mock_severe_assessment = {
    "location": "Kedarnath, Uttarakhand",
    "threat_level": "Severe",
    "confidence": "High",
    "active_hazards": ["Glacial lake outburst flood", "Debris avalanche"],
    "summary": "Rapid surge in Mandakini headwaters detected by acoustic sensors.",
    "action_plan": [
        "Sound temple siren network immediately",
        "Dispatch SDRF mountain team from Lincheli",
        "Evacuate Kedarnath base camp to higher terraces"
    ],
    "resources_needed": {
        "ndrf_teams": 2,
        "helicopters": 1,
        "medical_units": 2,
        "relief_camps": 1
    },
    "contact_agencies": ["NDMA", "SDRF", "SEOC", "District Magistrate"]
}

def test_sentinel_status_endpoint():
    resp = client.get("/api/agent/sentinel-status")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "status" in data
    assert "monitored_zones" in data
    assert data["monitored_zones"] == HIGH_RISK_ZONES
    assert "scanned_zones" in data
    assert "active_threats" in data

def test_rich_terminal_warning():
    # Should render without raising any encoding or formatting exception
    log_severe_threat_terminal("Kedarnath, Uttarakhand", mock_severe_assessment)

def test_alert_creation():
    async def _inner():
        with patch("backend.tasks.background._broadcast_ws", new_callable=AsyncMock) as mock_ws, \
             patch("backend.core.push_service.send_push_to_all", return_value={"sent": 1, "failed": 0, "total": 1}) as mock_push, \
             patch("backend.services.lora_engine.broadcast_lora_mesh") as mock_lora:

            incident_id = await create_sentinel_alert("Kedarnath, Uttarakhand", mock_severe_assessment)
            assert incident_id is not None, "Failed to get incident ID"

            # Verify DB insertion
            conn = get_db()
            row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
            assert row is not None, "Incident not found in database!"
            assert row["type"] == "SENTINEL_SEVERE"
            assert row["priority"] == "CRITICAL"
            assert "Kedarnath" in row["zone"]

            # Verify Broadcasts table insertion
            b_row = conn.execute("SELECT * FROM broadcasts WHERE target_city=?", ("Kedarnath, Uttarakhand",)).fetchone()
            assert b_row is not None, "Broadcast record not found in database!"
            conn.close()

            # Verify WebSocket broadcast
            mock_ws.assert_called_once()
            ws_payload = mock_ws.call_args[0][0]
            assert ws_payload["type"] == "emergency_broadcast"
            assert "Kedarnath" in ws_payload["title"]

            # Verify Push notification
            mock_push.assert_called_once()

            # Verify LoRa Mesh fallback
            mock_lora.assert_called_once()

    asyncio.run(_inner())

mock_results_by_zone = {
    "Kedarnath, Uttarakhand": mock_severe_assessment,
    "Joshimath, Uttarakhand": {
        "location": "Joshimath, Uttarakhand",
        "threat_level": "Normal",
        "confidence": "High",
        "active_hazards": ["None"],
        "summary": "Slope stability indicators nominal.",
        "action_plan": ["Routine monitoring"],
        "resources_needed": {"ndrf_teams": 0, "helicopters": 0, "medical_units": 0, "relief_camps": 0},
        "contact_agencies": ["IMD"]
    },
    "Pithoragarh, Uttarakhand": {
        "location": "Pithoragarh, Uttarakhand",
        "threat_level": "Elevated",
        "confidence": "Medium",
        "active_hazards": ["Light rain"],
        "summary": "Monsoon drizzle across valley.",
        "action_plan": ["Check culverts"],
        "resources_needed": {"ndrf_teams": 0, "helicopters": 0, "medical_units": 0, "relief_camps": 0},
        "contact_agencies": ["IMD"]
    }
}

def fake_disaster_analysis(location, verbose=False):
    return mock_results_by_zone.get(location, mock_severe_assessment)

def test_sentinel_cycle_and_cached_status():
    async def _inner():
        with patch("backend.services.agent_service.run_disaster_analysis", side_effect=fake_disaster_analysis), \
             patch("backend.tasks.background._broadcast_ws", new_callable=AsyncMock), \
             patch("backend.core.push_service.send_push_to_all"), \
             patch("backend.services.lora_engine.broadcast_lora_mesh"):

            res = await run_sentinel_cycle()
            assert res["status"] == "idle"
            assert res["total_scans_completed"] >= 1
            assert "Kedarnath, Uttarakhand" in res["scanned_zones"]
            assert len(res["active_threats"]) == 1
            assert res["active_threats"][0]["zone"] == "Kedarnath, Uttarakhand"

    asyncio.run(_inner())

    # Verify cached status via HTTP endpoint
    resp2 = client.get("/api/agent/sentinel-status")
    data2 = resp2.json()
    assert data2["total_scans_completed"] >= 1
    assert data2["last_scan_timestamp"] is not None
    assert "Kedarnath, Uttarakhand" in data2["scanned_zones"]
