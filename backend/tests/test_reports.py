import pytest
import io
import csv
import json
import hashlib
from pypdf import PdfReader
from fastapi.testclient import TestClient

from app.main import app
from app.services.report_service import ReportService
from app.api.endpoints.pipeline import execute_analysis_pipeline
from app.models.database import (
    SessionLocal,
    InvestigationModel,
    EvidenceRecordModel,
    ExtractedEntityModel,
    SourceReliabilityModel,
    AttributionAssessmentModel,
    AuditEventModel
)
from app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture
def analyst_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def unauthorized_analyst_headers():
    token = create_access_token({
        "sub": "foreign_analyst",
        "analyst_id": "ANALYST-FOREIGN-999",
        "role": "CTI_ANALYST"
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def initialized_cases(analyst_headers):
    """
    Cleans up any prior events, loads Benchmark Case 1 and Case 2, and runs the analysis pipeline for each,
    ensuring that assessments, evidence, sources, and audit events exist in SQLite in a clean hash chain.
    """
    from app.services.audit_chain import AuditChainService
    db = SessionLocal()
    try:
        db.query(AuditEventModel).filter(AuditEventModel.investigation_id.in_(["INV-SIH-001", "INV-SIH-002"])).delete()
        db.query(AttributionAssessmentModel).filter(AttributionAssessmentModel.investigation_id.in_(["INV-SIH-001", "INV-SIH-002"])).delete()
        for inv_id in ["INV-SIH-001", "INV-SIH-002"]:
            inv_obj = db.query(InvestigationModel).filter(InvestigationModel.id == inv_id).first()
            if inv_obj:
                inv_obj.assigned_analyst_id = "ANALYST-001"
                inv_obj.classification = "UNRESTRICTED"
        db.commit()
    finally:
        db.close()

    AuditChainService.reset_chain_state("INV-SIH-001")
    AuditChainService.reset_chain_state("INV-SIH-002")

    # Load Case 1
    client.post("/api/v1/ingestion/benchmark/1", headers=analyst_headers)
    db = SessionLocal()
    execute_analysis_pipeline("INV-SIH-001", db)

    # Load Case 2
    client.post("/api/v1/ingestion/benchmark/2", headers=analyst_headers)
    execute_analysis_pipeline("INV-SIH-002", db)
    db.close()

    return ["INV-SIH-001", "INV-SIH-002"]


def test_json_dossier_reconstruction(initialized_cases):
    """
    Verifies that ReportService reconstructs the complete investigation dossier
    purely from persisted database state without live pipeline execution.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-001"
        dossier = ReportService.generate_json_dossier(inv_id, db)

        # 1. Report Metadata
        meta = dossier["report_metadata"]
        assert meta["title"] == "Forensic Investigation Dossier"
        assert meta["standard"] == "NTRO SIH26151 Evidentiary Framework"
        assert len(meta["report_hash"]) == 64
        assert meta["audit_chain_valid"] is True
        assert meta["verified_event_count"] >= 1
        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in meta["identity_disclaimer"]
        assert "Not automatically legally admissible" in meta["legal_disclaimer"]

        # 2. Investigation Overview
        inv = dossier["investigation"]
        assert inv["id"] == inv_id
        assert inv["persona_a"] == "KryptonGhost"
        assert inv["persona_b"] == "SpecterOp"

        # 3. Assessment & Fused Score
        assess = dossier["current_assessment"]
        assert assess["attribution_state"] == "LIKELY_LINK"
        assert assess["confidence_band"] == "HIGH"
        assert round(assess["base_score"], 2) in (0.76, 0.77)

        # 4. 5 Dimensions
        dims = dossier["dimension_signals"]
        assert "CRYPTOGRAPHIC" in dims
        assert "FINANCIAL" in dims
        assert "STYLOMETRIC" in dims
        assert "INFRASTRUCTURE" in dims
        assert "BEHAVIORAL_TEMPORAL" in dims

        # 5. Evidence Inventory & Entities
        assert len(dossier["evidence_inventory"]) >= 4
        for ev in dossier["evidence_inventory"]:
            assert len(ev["content_hash"]) == 64
            assert ev["extractor_version"]
        assert len(dossier["extracted_entities"]) >= 4

        # 6. Source Reliabilities
        assert len(dossier["source_reliabilities"]) >= 1
        for s in dossier["source_reliabilities"]:
            assert 0.0 <= s["reliability_score"] <= 1.0
            assert 0.5 <= s["channel_modifier"] <= 1.0
    finally:
        db.close()


def test_dossier_integrity_hash_determinism(initialized_cases):
    """
    Verifies that report_hash is deterministic: consecutive reconstructions
    of the same persisted state yield the exact same SHA-256 hash.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-001"
        dossier_1 = ReportService.generate_json_dossier(inv_id, db)
        dossier_2 = ReportService.generate_json_dossier(inv_id, db)

        hash_1 = dossier_1["report_metadata"]["report_hash"]
        hash_2 = dossier_2["report_metadata"]["report_hash"]

        assert len(hash_1) == 64
        assert hash_1 == hash_2, "report_hash must be strictly deterministic"
    finally:
        db.close()


def test_csv_export_deterministic_format(initialized_cases):
    """
    Verifies that the CSV export has stable section headers, valid row structure,
    and deterministic ordering of items.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-001"
        csv_text = ReportService.generate_csv_dossier(inv_id, db)

        assert "=== TRACE-X FORENSIC INVESTIGATION DOSSIER CSV EXPORT ===" in csv_text
        assert "=== INVESTIGATION OVERVIEW ===" in csv_text
        assert "=== ATTRIBUTION ASSESSMENT ===" in csv_text
        assert "=== 5-DIMENSION EVIDENCE BREAKDOWN ===" in csv_text
        assert "=== NORMALIZED EVIDENCE INVENTORY ===" in csv_text
        assert "=== EXTRACTED TECHNICAL INDICATORS ===" in csv_text
        assert "=== EVIDENCE SOURCES & TRUST TIERS ===" in csv_text
        assert "=== AUDIT LEDGER TRAIL ===" in csv_text
        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in csv_text

        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) > 20
    finally:
        db.close()


def test_pdf_generation_content_extraction(initialized_cases):
    """
    Uses pypdf to extract real text from the generated PDF dossier and validates
    all required forensic headers, disclaimers, scores, and tables.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-001"
        pdf_bytes = ReportService.generate_pdf_dossier(inv_id, db)

        assert pdf_bytes.startswith(b"%PDF-"), "Generated document must be a valid PDF"
        assert len(pdf_bytes) > 2000

        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

        extracted_text = ""
        for page in reader.pages:
            extracted_text += page.extract_text() + "\n"

        # Mandatory Legal & Forensic Invariants
        assert "Forensic Investigation Dossier" in extracted_text
        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in extracted_text
        assert "NTRO SIH26151" in extracted_text
        assert "Report Hash" in extracted_text
        assert "Terminal Audit Hash" in extracted_text
        assert "Audit Chain Integrity" in extracted_text
        assert "VALID" in extracted_text
        assert "Assessment ID" in extracted_text
        assert "Attribution State" in extracted_text
        assert "LIKELY_LINK" in extracted_text
        assert "Base Score" in extracted_text or "S_base" in extracted_text
        assert "KryptonGhost" in extracted_text
        assert "SpecterOp" in extracted_text
        assert "Normalized Evidence Inventory" in extracted_text
    finally:
        db.close()


def test_pdf_case2_hard_gate_explanation(initialized_cases):
    """
    Verifies that Case 2 PDF explicitly highlights the Level 2 TEMPORAL_CONCURRENCY_CLASH
    hard gate, forced INCONCLUSIVE state, and operational concurrency explanation.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-002"
        pdf_bytes = ReportService.generate_pdf_dossier(inv_id, db)

        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = ""
        for page in reader.pages:
            extracted_text += page.extract_text() + "\n"

        assert "INCONCLUSIVE" in extracted_text
        assert "TEMPORAL_CONCURRENCY_CLASH" in extracted_text
        assert "ShadowBroker_X" in extracted_text
        assert "PhantomAccess" in extracted_text
        assert "Frankfurt" in extracted_text
        assert "Singapore" in extracted_text
        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in extracted_text
    finally:
        db.close()


def test_model_provenance_truthfulness(initialized_cases):
    """
    Verifies that the dossier data extracts model provenance truthfully from
    the persisted assessment metadata.
    """
    db = SessionLocal()
    try:
        inv_id = "INV-SIH-001"
        dossier = ReportService.generate_json_dossier(inv_id, db)
        prov = dossier["model_provenance"]

        assert prov["engine"] in ("TRANSFORMER", "DETERMINISTIC_FALLBACK")
        if prov["engine"] == "TRANSFORMER":
            assert prov["model_name"] == "sentence-transformers/all-mpnet-base-v2"
            assert prov["embedding_dimensions"] == 768
        else:
            assert prov["embedding_dimensions"] == 64
        assert "150 words" in prov["stylometry_guardrail"]
        assert "500" in prov["stylometry_guardrail"]
    finally:
        db.close()


def test_reports_endpoints_rest(initialized_cases, analyst_headers):
    """
    Tests REST API endpoints for JSON, CSV, and PDF dossier downloads.
    """
    inv_id = "INV-SIH-001"

    # 1. JSON
    res_json = client.get(f"/api/v1/reports/{inv_id}/json", headers=analyst_headers)
    assert res_json.status_code == 200
    json_data = res_json.json()
    assert json_data["report_metadata"]["title"] == "Forensic Investigation Dossier"

    # 2. CSV
    res_csv = client.get(f"/api/v1/reports/{inv_id}/csv", headers=analyst_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment" in res_csv.headers["content-disposition"]
    assert "=== TRACE-X FORENSIC INVESTIGATION DOSSIER CSV EXPORT ===" in res_csv.text

    # 3. PDF
    res_pdf = client.get(f"/api/v1/reports/{inv_id}/pdf", headers=analyst_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")


def test_reports_auth_and_isolation(initialized_cases, analyst_headers, unauthorized_analyst_headers):
    """
    Verifies that reports endpoints enforce 401 unauthenticated,
    403 unauthorized for cross-investigation access, and 404 for non-existent cases.
    """
    # 1. 401 Unauthenticated
    res_unauth = client.get("/api/v1/reports/INV-SIH-001/json")
    assert res_unauth.status_code == 401

    # 2. 404 Not Found
    res_not_found = client.get("/api/v1/reports/INV-NONEXISTENT/json", headers=analyst_headers)
    assert res_not_found.status_code == 404

    # 3. 403 Forbidden on Restricted Investigation
    db = SessionLocal()
    try:
        inv = db.query(InvestigationModel).filter(InvestigationModel.id == "INV-SIH-001").first()
        inv.assigned_analyst_id = "ANALYST-RESTRICTED-001"
        inv.classification = "RESTRICTED"
        db.commit()

        res_forbidden = client.get("/api/v1/reports/INV-SIH-001/json", headers=unauthorized_analyst_headers)
        assert res_forbidden.status_code == 403
    finally:
        inv = db.query(InvestigationModel).filter(InvestigationModel.id == "INV-SIH-001").first()
        if inv:
            inv.assigned_analyst_id = "ANALYST-001"
            inv.classification = "UNRESTRICTED"
            db.commit()
        db.close()
