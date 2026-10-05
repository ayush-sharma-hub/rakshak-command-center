"""
Test suite for FastAPI route POST /api/agent/analyze
"""

import sys
sys.path.insert(0, r"C:\Users\rikwa\rakshak-new")

from fastapi.testclient import TestClient
from main import app
import unittest
from unittest.mock import patch

client = TestClient(app)

print("\n--- TEST 1: Validation - Empty/Whitespace Location ---")
resp_empty = client.post("/api/agent/analyze", json={"location": "   "})
print("Status code:", resp_empty.status_code)
print("Response:", resp_empty.json())
assert resp_empty.status_code in (400, 422), f"Expected 400 or 422, got {resp_empty.status_code}"
print("[PASS] Empty/whitespace validation rejected properly")

print("\n--- TEST 2: Validation - Short Location ---")
resp_short = client.post("/api/agent/analyze", json={"location": "A"})
print("Status code:", resp_short.status_code)
print("Response:", resp_short.json())
assert resp_short.status_code in (400, 422), f"Expected 400 or 422, got {resp_short.status_code}"
print("[PASS] Short location rejected properly")

print("\n--- TEST 3: Mock Error Handling (HTTP 500 without leaking internals) ---")
with patch("backend.api.routes.agent_routes.run_disaster_analysis", side_effect=RuntimeError("Secret database error /path/secret")):
    resp_err = client.post("/api/agent/analyze", json={"location": "Roorkee, Uttarakhand"})
    print("Status code:", resp_err.status_code)
    print("Response:", resp_err.json())
    assert resp_err.status_code == 500, f"Expected 500, got {resp_err.status_code}"
    body = resp_err.json()
    assert body["error"] == "AgentAnalysisFailed"
    assert "Secret" not in str(body), "Leaked internal details!"
    print("[PASS] Internal error returns clean HTTP 500 without leaking secrets")

print("\n--- TEST 4: Successful Mock Response Execution ---")
mock_result = {
    "location": "Roorkee, Uttarakhand",
    "threat_level": "Normal",
    "confidence": "High",
    "active_hazards": ["Localized drainage congestion"],
    "summary": "Roorkee is experiencing stable conditions.",
    "action_plan": ["Monitor river levels", "Check culverts"],
    "resources_needed": {"ndrf_teams": 0, "helicopters": 0, "medical_units": 1, "relief_camps": 0},
    "contact_agencies": ["USDMA", "IMD"]
}

with patch("backend.api.routes.agent_routes.run_disaster_analysis", return_value=mock_result):
    resp_ok = client.post("/api/agent/analyze", json={"location": "Roorkee, Uttarakhand"})
    print("Status code:", resp_ok.status_code)
    print("Response:", resp_ok.json())
    assert resp_ok.status_code == 200, f"Expected 200, got {resp_ok.status_code}"
    data = resp_ok.json()
    assert data["location"] == "Roorkee, Uttarakhand"
    assert data["threat_level"] == "Normal"
    assert "summary" in data
    assert len(data["action_plan"]) == 2
    print("[PASS] Valid analysis returns HTTP 200 with structured assessment")

print("\n=======================================================")
print("ALL ROUTE UNIT TESTS PASSED SUCCESSFULLY!")
print("=======================================================")
