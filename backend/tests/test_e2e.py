import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in data["identity_scope"]


def test_e2e_case_1_convergence():
    # 1. Load Benchmark Case 1
    load_res = client.post("/api/v1/ingestion/benchmark/case_1")
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
    assert assessment.evidence_score >= 0.70
    assert assessment.real_world_identity == "NOT ESTABLISHED"

    # 3. Verify Cytoscape graph payload
    graph_res = client.get("/api/v1/graph/INV-SIH-001")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert len(graph_data["graph"]["nodes"]) > 0
    assert len(graph_data["graph"]["edges"]) > 0

    # 4. Verify Sensitivity Recalculation
    recalc_res = client.post("/api/v1/attribution/recalculate", json={
        "investigation_id": "INV-SIH-001",
        "weight_cryptographic": 0.10,
        "weight_financial": 0.20,
        "weight_stylometric": 0.10,
        "weight_infrastructure": 0.30,
        "weight_behavioral": 0.30
    })
    assert recalc_res.status_code == 200
    assert "attribution_state" in recalc_res.json()


def test_e2e_case_2_contradiction_clash():
    # 1. Load Benchmark Case 2
    load_res = client.post("/api/v1/ingestion/benchmark/case_2")
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
    # Verify that hard gate forces INCONCLUSIVE
    assert assessment.attribution_state.value == "INCONCLUSIVE"
    assert assessment.assessment_rationale.hard_cap_applied is True
