import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_append_only_audit_event(lead_auditor_headers):
    # 1. Load benchmark 1
    bench_resp = client.post("/api/v1/ingestion/benchmark/1")
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Record first analyst decision
    req1 = {
        "investigation_id": inv_id,
        "assessment_id": "ASSESS-001",
        "action": "CONFIRMED",
        "analyst_id": "AUDITOR-001",
        "rationale": "Corroborated across PGP and wallet CIOH cluster."
    }
    resp1 = client.post("/api/v1/audit/decision", json=req1, headers=lead_auditor_headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["event_hash"] is not None
    assert data1["action"] == "CONFIRMED"
    assert "CONFIRMED" in data1["resulting_state"]

    # 3. Record second decision
    req2 = {
        "investigation_id": inv_id,
        "assessment_id": "ASSESS-001",
        "action": "INVESTIGATE",
        "analyst_id": "AUDITOR-001",
        "rationale": "Requesting additional VASP KYC subpoena."
    }
    resp2 = client.post("/api/v1/audit/decision", json=req2, headers=lead_auditor_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["event_hash"] != data1["event_hash"]
    assert data2["resulting_state"] == "UNDER_FURTHER_INVESTIGATION"

    # 4. Test export dossier
    dossier_resp = client.get(f"/api/v1/audit/export/{inv_id}")
    assert dossier_resp.status_code == 200
    dossier = dossier_resp.json()
    assert len(dossier["audit_trail"]) >= 2
