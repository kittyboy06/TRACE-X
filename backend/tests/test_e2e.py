import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def auth_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in data["identity_scope"]


def test_e2e_case_1_convergence(auth_headers):
    # 1. Load Benchmark Case 1 (Protected)
    load_res = client.post("/api/v1/ingestion/benchmark/case_1", headers=auth_headers)
    assert load_res.status_code == 200
    load_data = load_res.json()
    assert load_data["investigation_id"] == "INV-SIH-001"

    # 2. Run analysis pipeline
    from app.models.database import SessionLocal
    from app.api.endpoints.pipeline import execute_analysis_pipeline
    db = SessionLocal()
    pipeline_res = execute_analysis_pipeline("INV-SIH-001", db)
    db.close()

    assessment = pipeline_res["assessment"]
    assert assessment.attribution_state.value == "LIKELY_LINK"
    assert assessment.base_score >= 0.70
    assert assessment.real_world_identity == "NOT ESTABLISHED"

    # 3. Verify Cytoscape graph payload
    graph_res = client.get("/api/v1/graph/INV-SIH-001", headers=auth_headers)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert len(graph_data["graph"]["nodes"]) > 0
    assert len(graph_data["graph"]["edges"]) > 0

    # 4. Verify Protected Sensitivity Recalculation
    recalc_res = client.post("/api/v1/attribution/recalculate", json={
        "investigation_id": "INV-SIH-001",
        "weight_cryptographic": 0.10,
        "weight_financial": 0.20,
        "weight_stylometric": 0.10,
        "weight_infrastructure": 0.30,
        "weight_behavioral": 0.30
    }, headers=auth_headers)
    assert recalc_res.status_code == 200
    assert "attribution_state" in recalc_res.json()


def test_e2e_case_2_contradiction_clash(auth_headers):
    # 1. Load Benchmark Case 2 (Protected)
    load_res = client.post("/api/v1/ingestion/benchmark/case_2", headers=auth_headers)
    assert load_res.status_code == 200
    load_data = load_res.json()
    assert load_data["investigation_id"] == "INV-SIH-002"

    # 2. Run analysis pipeline
    from app.models.database import SessionLocal
    from app.api.endpoints.pipeline import execute_analysis_pipeline
    db = SessionLocal()
    pipeline_res = execute_analysis_pipeline("INV-SIH-002", db)
    db.close()

    assessment = pipeline_res["assessment"]
    assert assessment.attribution_state.value == "INCONCLUSIVE"
    assert assessment.base_score <= 0.40
    assert assessment.hard_gate_applied is True
    assert assessment.assessment_rationale.hard_gate_applied is True


def test_sensitivity_recalculation(auth_headers):
    # Unauthenticated recalculation -> 401
    unauth_res = client.post("/api/v1/attribution/recalculate", json={
        "investigation_id": "INV-SIH-001",
        "weight_cryptographic": 0.30,
        "weight_financial": 0.25,
        "weight_stylometric": 0.20,
        "weight_infrastructure": 0.15,
        "weight_behavioral": 0.10
    })
    assert unauth_res.status_code == 401


def test_e2e_ephemeral_sse_ticket_flow(auth_headers):
    """
    Verifies Phase 1 / Phase 7 ephemeral SSE ticket flow:
    JWT -> POST /auth/sse-ticket -> ticket -> pipeline stream
    """
    ticket_res = client.post("/api/v1/auth/sse-ticket", json={
        "investigation_id": "INV-SIH-001"
    }, headers=auth_headers)
    assert ticket_res.status_code == 200
    ticket_data = ticket_res.json()
    assert "ticket" in ticket_data
    assert len(ticket_data["ticket"]) >= 32
    assert ticket_data["investigation_id"] == "INV-SIH-001"
    assert ticket_data["expires_in"] == 60


def test_e2e_sources_reliability_flow(auth_headers):
    """
    Verifies Decision #10 sources endpoint consumed by SourcesPanel.
    """
    res = client.get("/api/v1/reliability/INV-SIH-001/sources", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["investigation_id"] == "INV-SIH-001"
    assert "sources" in data
    assert len(data["sources"]) > 0

    # Verify Decision #10 4-factor breakdown fields
    src = data["sources"][0]
    assert "trust_tier" in src
    assert "reliability_score" in src
    assert "reliability_class" in src
    assert "factors" in src
    assert "reputation" in src["factors"]
    assert "freshness" in src["factors"]
    assert "corroboration" in src["factors"]
    assert "consistency" in src["factors"]


def test_e2e_extracted_entities_flow(auth_headers):
    """
    Verifies extracted technical indicators endpoint consumed by EvidenceDrawer.
    """
    res = client.get("/api/v1/ingestion/INV-SIH-001/entities", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["investigation_id"] == "INV-SIH-001"
    assert "entities" in data
    assert len(data["entities"]) > 0

    ent = data["entities"][0]
    assert "entity_id" in ent
    assert "entity_type" in ent
    assert "value" in ent
    assert "evidence_id" in ent
    assert "confidence" in ent


def test_e2e_commit_weights_and_audit_event_flow(auth_headers):
    """
    Verifies Sensitivity Tuner commit weights flow generating immutable AuditEvent.
    """
    commit_res = client.post("/api/v1/attribution/commit-weights", json={
        "investigation_id": "INV-SIH-001",
        "weight_cryptographic": 0.20,
        "weight_financial": 0.20,
        "weight_stylometric": 0.20,
        "weight_infrastructure": 0.20,
        "weight_behavioral": 0.20
    }, headers=auth_headers)
    assert commit_res.status_code == 200
    commit_data = commit_res.json()
    assert commit_data["status"] == "COMMITTED"
    assert "audit_event" in commit_data
    assert "event_hash" in commit_data["audit_event"]
    assert len(commit_data["audit_event"]["event_hash"]) == 64
    assert commit_data["assessment"]["evidence_dimensions"]["cryptographic"]["configured_weight"] == 0.20

