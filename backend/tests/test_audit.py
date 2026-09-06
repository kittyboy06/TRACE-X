import pytest
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, AuditEventModel, AttributionAssessmentModel
from app.services.audit_chain import AuditChainService, GENESIS_HASH

client = TestClient(app)


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def analyst_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
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
        "analyst_id": "SPOOFED_IMPERSONATOR_999",  # Should be ignored; derived from JWT
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
    assert len(data1["previous_hash"]) == 64

    # 3. Record second decision and verify cryptographic hash chaining
    req2 = {
        "investigation_id": inv_id,
        "assessment_id": "ASSESS-001",
        "action": "INVESTIGATE",
        "rationale": "Requesting additional VASP KYC subpoena."
    }
    resp2 = client.post("/api/v1/audit/decision", json=req2, headers=lead_auditor_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["event_hash"] != data1["event_hash"]
    assert data2["resulting_state"] == "UNDER_FURTHER_INVESTIGATION"
    # Unbroken cryptographic hash chain
    assert data2["previous_hash"] == data1["event_hash"]

    # 4. Verify chain integrity via verify endpoint
    verify_resp = client.get(f"/api/v1/audit/verify/{inv_id}", headers=lead_auditor_headers)
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["is_valid"] is True
    assert verify_data["terminal_hash"] == data2["event_hash"]

    # 5. Export dossier (Unauthenticated -> 401, Authenticated -> 200)
    resp_unauth = client.get(f"/api/v1/audit/export/{inv_id}")
    assert resp_unauth.status_code == 401

    dossier_resp = client.get(f"/api/v1/audit/export/{inv_id}", headers=lead_auditor_headers)
    assert dossier_resp.status_code == 200
    dossier = dossier_resp.json()
    assert len(dossier["audit_trail"]) >= 2
    assert dossier["export_metadata"]["audit_chain_valid"] is True
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
    assert len(commit_data["audit_event"]["previous_hash"]) == 64


def test_concurrent_audit_writes_maintain_linear_chain():
    """Verify that multiple concurrent threads appending to an investigation's audit chain do not fork the chain."""
    inv_id = "INV-CONCURRENT-CHAIN-001"
    db = SessionLocal()

    # Ensure clean state for this investigation
    db.query(AuditEventModel).filter(AuditEventModel.investigation_id == inv_id).delete()
    db.commit()
    AuditChainService.reset_chain_state(inv_id)

    def append_worker(worker_id: int):
        worker_db = SessionLocal()
        try:
            AuditChainService.append_event(
                db=worker_db,
                investigation_id=inv_id,
                assessment_id=f"ASSESS-CONCURRENT-{worker_id}",
                action=f"ACTION_CONCURRENT_{worker_id}",
                analyst_id=f"ANALYST-{worker_id:03d}",
                rationale=f"Concurrent test entry from worker {worker_id}",
                prior_state="ACTIVE",
                resulting_state="UPDATED"
            )
            worker_db.commit()
            return True
        finally:
            worker_db.close()

    # Execute 8 concurrent appends
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(append_worker, i) for i in range(8)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 8
    assert all(r is True for r in results)

    # Cryptographically verify the entire chain
    is_valid, records, error = AuditChainService.verify_investigation_chain(inv_id, db)
    assert is_valid is True, f"Chain verification failed: {error}"
    assert len(records) == 8

    # First event must have genesis hash
    assert records[0]["previous_hash"] == GENESIS_HASH

    # Every subsequent event must cleanly link to its predecessor
    for i in range(1, 8):
        assert records[i]["previous_hash"] == records[i - 1]["event_hash"]

    db.close()


def test_atomic_persistence_rollback():
    """Verify that an uncommitted or failed audit append transaction rolls back cleanly without leaving orphan records."""
    db = SessionLocal()
    inv_id = "INV-ROLLBACK-TEST"

    # Count initial records
    initial_audits = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == inv_id).count()

    try:
        # Simulate a transaction failure
        AuditChainService.append_event(
            db=db,
            investigation_id=inv_id,
            assessment_id="ASSESS-FAIL",
            action="SHOULD_ROLLBACK",
            analyst_id="ANALYST-001",
            rationale="This should be rolled back",
            prior_state="ACTIVE",
            resulting_state="FAILED"
        )
        # Explicit rollback without commit
        db.rollback()
    finally:
        db.close()

    # Verify count is unchanged
    verify_db = SessionLocal()
    final_audits = verify_db.query(AuditEventModel).filter(AuditEventModel.investigation_id == inv_id).count()
    verify_db.close()

    assert final_audits == initial_audits
