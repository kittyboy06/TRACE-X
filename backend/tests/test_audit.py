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


def test_append_only_audit_event_and_spoof_prevention(lead_auditor_headers):
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=lead_auditor_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Record first analyst decision with spoofed analyst_id in body
    req1 = {
        "investigation_id": inv_id,
        "assessment_id": "ASSESS-001",
        "action": "CONFIRMED",
        "analyst_id": "SPOOFED_IMPERSONATOR_999",  # Should be overridden by JWT identity
        "rationale": "Corroborated across PGP and wallet CIOH cluster."
    }
    resp1 = client.post("/api/v1/audit/decision", json=req1, headers=lead_auditor_headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["event_hash"] is not None
    assert data1["action"] == "CONFIRMED"
    # Identity is securely bound to JWT token (AUDITOR-001)
    assert data1["analyst_id"] == "AUDITOR-001"
    assert "CONFIRMED" in data1["resulting_state"]
    assert data1["previous_hash"] is not None

    # 3. Record second decision and verify cryptographic hash chaining
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
    # Unbroken cryptographic hash chain
    assert data2["previous_hash"] == data1["event_hash"]

    # 4. Test protected export dossier
    # Unauthenticated export -> 401
    resp_unauth = client.get(f"/api/v1/audit/export/{inv_id}")
    assert resp_unauth.status_code == 401

    # Authenticated export -> 200
    dossier_resp = client.get(f"/api/v1/audit/export/{inv_id}", headers=lead_auditor_headers)
    assert dossier_resp.status_code == 200
    dossier = dossier_resp.json()
    assert len(dossier["audit_trail"]) >= 2
    # Verify chain link between last two events
    assert dossier["audit_trail"][-1]["previous_hash"] == data1["event_hash"]


def test_commit_weights_audit_provenance_and_validation(lead_auditor_headers):
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=lead_auditor_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Run analysis pipeline to establish initial assessment
    from app.models.database import SessionLocal
    from app.api.endpoints.pipeline import execute_analysis_pipeline
    db = SessionLocal()
    execute_analysis_pipeline(inv_id, db)
    db.close()

    # 3. Test invalid zero-sum weights rejection
    zero_req = {
        "investigation_id": inv_id,
        "weight_cryptographic": 0.0,
        "weight_financial": 0.0,
        "weight_stylometric": 0.0,
        "weight_infrastructure": 0.0,
        "weight_behavioral": 0.0
    }
    zero_resp = client.post("/api/v1/attribution/recalculate", json=zero_req, headers=lead_auditor_headers)
    assert zero_resp.status_code == 400
    assert "greater than zero" in zero_resp.json()["detail"]

    # 4. Commit valid tuned weights
    tune_req = {
        "investigation_id": inv_id,
        "weight_cryptographic": 0.35,
        "weight_financial": 0.20,
        "weight_stylometric": 0.20,
        "weight_infrastructure": 0.15,
        "weight_behavioral": 0.10
    }
    commit_resp = client.post("/api/v1/attribution/commit-weights", json=tune_req, headers=lead_auditor_headers)
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["status"] == "COMMITTED"
    assert "audit_event" in commit_data
    assert commit_data["audit_event"]["action"] == "WEIGHTS_COMMITTED"
    assert commit_data["audit_event"]["event_hash"] is not None
    assert commit_data["audit_event"]["previous_hash"] is not None
