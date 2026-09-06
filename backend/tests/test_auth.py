import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, InvestigationModel

client = TestClient(app)


@pytest.fixture
def analyst_token():
    resp = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
    return resp.json()["access_token"]


@pytest.fixture
def lead_auditor_token():
    resp = client.post("/api/v1/auth/token", json={"username": "lead_auditor", "password": "auditor2026"})
    return resp.json()["access_token"]


def test_auth_success_analyst():
    response = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "CTI_ANALYST"
    assert data["analyst_id"] == "ANALYST-001"


def test_auth_success_lead_auditor():
    response = client.post("/api/v1/auth/token", json={"username": "lead_auditor", "password": "auditor2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "LEAD_AUDITOR"


def test_auth_failure_invalid_password():
    response = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "wrong_password_xyz"})
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_auth_failure_unknown_user():
    response = client.post("/api/v1/auth/token", json={"username": "hacker_unknown", "password": "any_password"})
    assert response.status_code == 401


def test_protected_profile_endpoint():
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    login_resp = client.post("/api/v1/auth/token", json={"username": "ntro_evaluator", "password": "ntro2026"})
    token = login_resp.json()["access_token"]

    resp_auth = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_auth.status_code == 200
    assert resp_auth.json()["username"] == "ntro_evaluator"
    assert resp_auth.json()["role"] == "LEAD_AUDITOR"


def test_investigation_reads_require_auth():
    """Verify 401 across all investigation read endpoints when unauthenticated or token is invalid."""
    endpoints = [
        "/api/v1/ingestion/INV-SIH-001/artifacts",
        "/api/v1/graph/INV-SIH-001",
        "/api/v1/attribution/INV-SIH-001",
        "/api/v1/audit/export/INV-SIH-001",
        "/api/v1/pipeline/stream/INV-SIH-001",
    ]

    for ep in endpoints:
        # 1. No JWT
        r_no_jwt = client.get(ep)
        assert r_no_jwt.status_code == 401, f"Expected 401 for {ep} without token, got {r_no_jwt.status_code}"

        # 2. Invalid JWT
        r_bad_jwt = client.get(ep, headers={"Authorization": "Bearer invalid.fake.token"})
        assert r_bad_jwt.status_code == 401, f"Expected 401 for {ep} with invalid token, got {r_bad_jwt.status_code}"


def test_investigation_authorization_matrix(analyst_token, lead_auditor_token):
    """
    Verifies full authorization matrix:
    - 404 for non-existent case
    - 403 when CTI_ANALYST accesses an investigation assigned to another analyst
    - 200 when CTI_ANALYST accesses assigned investigation
    - 200 when LEAD_AUDITOR accesses any investigation (unrestricted oversight)
    """
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    auditor_headers = {"Authorization": f"Bearer {lead_auditor_token}"}

    # 1. Seed benchmark 1 (assigned to ANALYST-001)
    seed_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auditor_headers)
    assert seed_resp.status_code == 200

    # 2. Create restricted investigation in DB assigned to ANALYST-002
    db = SessionLocal()
    try:
        inv_restricted = db.query(InvestigationModel).filter(InvestigationModel.id == "INV-RESTRICTED-002").first()
        if not inv_restricted:
            inv_restricted = InvestigationModel(
                id="INV-RESTRICTED-002",
                title="Restricted Internal Probe",
                target_persona_a="RedActor",
                target_persona_b="BlueActor",
                assigned_analyst_id="ANALYST-002",  # Not ANALYST-001
                classification="RESTRICTED",
            )
            db.add(inv_restricted)
            db.commit()
    finally:
        db.close()

    # 3. Non-existent investigation -> 404
    r_404 = client.get("/api/v1/ingestion/INV-DOES-NOT-EXIST/artifacts", headers=analyst_headers)
    assert r_404.status_code == 404

    # 4. Assigned case -> 200 for ANALYST-001
    r_assigned = client.get("/api/v1/ingestion/INV-SIH-001/artifacts", headers=analyst_headers)
    assert r_assigned.status_code == 200

    # 5. Restricted / unassigned case -> 403 for ANALYST-001
    r_forbidden = client.get("/api/v1/ingestion/INV-RESTRICTED-002/artifacts", headers=analyst_headers)
    assert r_forbidden.status_code == 403
    assert "not authorized" in r_forbidden.json()["detail"]

    # 6. Restricted case -> 200 for LEAD_AUDITOR (supervisory role)
    r_auditor = client.get("/api/v1/ingestion/INV-RESTRICTED-002/artifacts", headers=auditor_headers)
    assert r_auditor.status_code == 200


def test_sse_ticket_endpoint_and_scoping(analyst_token):
    """Verify ephemeral SSE ticket issuance, expiry, and scope validation."""
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Unauthenticated ticket request -> 401
    r_unauth = client.post("/api/v1/auth/sse-ticket", json={"investigation_id": "INV-SIH-001"})
    assert r_unauth.status_code == 401

    # 2. Unauthorized investigation -> 403
    r_forbid = client.post(
        "/api/v1/auth/sse-ticket",
        json={"investigation_id": "INV-RESTRICTED-002"},
        headers=analyst_headers
    )
    assert r_forbid.status_code == 403

    # 3. Authorized request -> 200 with 60s ticket
    r_ok = client.post(
        "/api/v1/auth/sse-ticket",
        json={"investigation_id": "INV-SIH-001"},
        headers=analyst_headers
    )
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert "ticket" in data
    assert len(data["ticket"]) >= 32
    assert data["expires_in"] == 60
    assert data["investigation_id"] == "INV-SIH-001"
