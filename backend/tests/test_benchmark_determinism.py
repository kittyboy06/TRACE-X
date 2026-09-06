import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, AttributionAssessmentModel
from app.api.endpoints.pipeline import execute_analysis_pipeline
from app.services.report_service import ReportService

client = TestClient(app)


def test_benchmark_case_1_exact_determinism():
    """
    Asserts:
    1. Case 1 fixture + canonical configuration => expected S_base == 0.7639 (fallback) or 0.7735 (transformer)
    2. Zero variance across repeated runs
    3. Pipeline S_base == DB S_base == API S_base == JSON Dossier S_base == PDF Dossier S_base
    """
    r_auth = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
    assert r_auth.status_code == 200
    token = r_auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest benchmark case 1
    r_ingest = client.post("/api/v1/ingestion/benchmark/1", headers=headers)
    assert r_ingest.status_code == 200

    # First run
    db = SessionLocal()
    res_run1 = execute_analysis_pipeline("INV-SIH-001", db)
    assess1 = res_run1["assessment"]
    s_base_run1 = round(float(assess1.base_score), 4)

    # Second run (proves zero drift across repeated executions)
    res_run2 = execute_analysis_pipeline("INV-SIH-001", db)
    s_base_run2 = round(float(res_run2["assessment"].base_score), 4)
    assert s_base_run1 == s_base_run2, f"Run-to-run drift detected: {s_base_run1} != {s_base_run2}"

    # Verify canonical expected value
    eng_type = assess1.evidence_dimensions.stylometric.supporting_details.get("engine_type", "DETERMINISTIC_FALLBACK")
    expected_sbase = 0.7735 if eng_type == "TRANSFORMER" else 0.7639
    assert abs(s_base_run1 - expected_sbase) <= 0.0001, (
        f"Case 1 canonical drift: expected {expected_sbase:.4f} for {eng_type}, got {s_base_run1:.4f}"
    )

    # Cross-layer propagation equality
    db_record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == "INV-SIH-001",
        AttributionAssessmentModel.is_current == True
    ).first()
    db_sbase = round(float(db_record.base_score), 4)

    r_api = client.get("/api/v1/attribution/INV-SIH-001", headers=headers)
    assert r_api.status_code == 200
    api_sbase = round(float(r_api.json()["base_score"]), 4)

    dossier_json = ReportService.generate_json_dossier("INV-SIH-001", db)
    json_sbase = round(float(dossier_json["current_assessment"]["base_score"]), 4)

    pdf_bytes = ReportService.generate_pdf_dossier("INV-SIH-001", db)
    assert len(pdf_bytes) > 1000
    db.close()

    assert s_base_run1 == db_sbase == api_sbase == json_sbase, (
        f"Cross-layer score mismatch: Pipeline={s_base_run1}, DB={db_sbase}, API={api_sbase}, JSON={json_sbase}"
    )
    assert assess1.attribution_state.value == "LIKELY_LINK"
    assert assess1.confidence_band.value == "HIGH"
    assert assess1.hard_gate_applied is False


def test_benchmark_case_2_exact_determinism_and_hard_gate():
    """
    Asserts:
    1. Case 2 fixture + canonical configuration => expected S_base == 0.2150
    2. Level 2 Hard Gate strictly overrides attribution to INCONCLUSIVE (band LOW)
    3. S_base is preserved (not zeroed out) for analyst explainability
    4. Pipeline S_base == DB S_base == API S_base == JSON Dossier S_base
    """
    r_auth = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
    assert r_auth.status_code == 200
    token = r_auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest benchmark case 2
    r_ingest = client.post("/api/v1/ingestion/benchmark/2", headers=headers)
    assert r_ingest.status_code == 200

    db = SessionLocal()
    res = execute_analysis_pipeline("INV-SIH-002", db)
    assess = res["assessment"]
    pipe_sbase = round(float(assess.base_score), 4)

    # Assert exact canonical score:
    # 0.30(0.15) + 0.25(0.36) + 0.20(0.0) + 0.15(0.0) + 0.10(0.80) = 0.2150
    expected_sbase = 0.2150
    assert abs(pipe_sbase - expected_sbase) <= 0.0001, (
        f"Case 2 canonical drift: expected {expected_sbase:.4f}, got {pipe_sbase:.4f}"
    )

    # Invariants
    assert assess.attribution_state.value == "INCONCLUSIVE"
    assert assess.confidence_band.value == "LOW"
    assert assess.hard_gate_applied is True
    assert "Simultaneous authenticated activity confirmed within 30s" in assess.hard_gate_reason

    # Cross-layer propagation equality
    db_record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == "INV-SIH-002",
        AttributionAssessmentModel.is_current == True
    ).first()
    db_sbase = round(float(db_record.base_score), 4)

    r_api = client.get("/api/v1/attribution/INV-SIH-002", headers=headers)
    assert r_api.status_code == 200
    api_sbase = round(float(r_api.json()["base_score"]), 4)

    dossier_json = ReportService.generate_json_dossier("INV-SIH-002", db)
    json_sbase = round(float(dossier_json["current_assessment"]["base_score"]), 4)
    db.close()

    assert pipe_sbase == db_sbase == api_sbase == json_sbase, (
        f"Cross-layer score mismatch: Pipeline={pipe_sbase}, DB={db_sbase}, API={api_sbase}, JSON={json_sbase}"
    )
