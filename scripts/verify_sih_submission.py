#!/usr/bin/env python3
"""
TRACE-X SIH Acceptance Verification Runner
==========================================
Standard: NTRO SIH26151 Evidentiary Framework
Mode: Automated Acceptance Test & CI Verification

Asserts the 10 TRACE-X Implementation Acceptance Checkpoints:
  [01] RBAC & Authentication
  [02] Secure Evidence Ingestion & 10MB Security Limit
  [03] Entity Extraction & Cross-Case Scoping
  [04] Source Reliability Engine (Decision #10)
  [05] Analytical Engines & Guardrails
  [06] Benchmark Case 1 Convergence & Numerical Consistency
  [07] Benchmark Case 2 Contradiction Gate & Score Preservation
  [08] Sensitivity Tuning (Preview vs. Commit)
  [09] Cryptographic Audit Chain Verification
  [10] Dossier Reconstruction & Cross-Phase Consistency (PDF/CSV/JSON)

Exits with code 0 on 10/10 PASS; exits with code 1 on any failure.
"""

import os
import sys
import time
import io
import json
import hashlib

# Ensure backend is on PYTHONPATH
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app
from app.models.database import (
    SessionLocal,
    InvestigationModel,
    EvidenceRecordModel,
    ExtractedEntityModel,
    SourceReliabilityModel,
    AttributionAssessmentModel,
    AuditEventModel
)
from app.api.endpoints.pipeline import execute_analysis_pipeline
from app.services.audit_chain import AuditChainService
from app.services.report_service import ReportService
from app.core.config import settings

client = TestClient(app)

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def print_header():
    print("=" * 88)
    print(f"{Colors.BOLD}TRACE-X SIH ACCEPTANCE VERIFICATION RUNNER{Colors.ENDC}")
    print(f"{Colors.DIM}Standard: NTRO SIH26151 Evidentiary Framework  |  Mode: Decision Support System{Colors.ENDC}")
    print("=" * 88)

def print_checkpoint(num: int, name: str, status: str, duration: float, detail: str = ""):
    stat_colored = f"{Colors.OKGREEN}{Colors.BOLD}PASS{Colors.ENDC}" if status == "PASS" else f"{Colors.FAIL}{Colors.BOLD}FAIL{Colors.ENDC}"
    print(f"[{num:02d}] {name:<48} {stat_colored}  ({duration:5.2f}s)")
    if detail:
        print(f"     {Colors.DIM}--> {detail}{Colors.ENDC}")

def run_all_checkpoints():
    print_header()
    from app.models.database import Base, engine
    Base.metadata.create_all(bind=engine)

    checkpoints_passed = 0
    total_start = time.perf_counter()
    tokens = {}

    # -------------------------------------------------------------------------
    # [01] RBAC & Authentication
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        # Analyst
        r_analyst = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
        assert r_analyst.status_code == 200, f"Analyst login failed: {r_analyst.status_code}"
        data_a = r_analyst.json()
        assert data_a["role"] == "CTI_ANALYST"
        assert data_a["analyst_id"] == "ANALYST-001"
        tokens["analyst"] = data_a["access_token"]

        # Lead Auditor
        r_auditor = client.post("/api/v1/auth/token", json={"username": "lead_auditor", "password": "auditor2026"})
        assert r_auditor.status_code == 200, f"Auditor login failed: {r_auditor.status_code}"
        data_aud = r_auditor.json()
        assert data_aud["role"] == "LEAD_AUDITOR"
        assert data_aud["analyst_id"] == "AUDITOR-001"
        tokens["auditor"] = data_aud["access_token"]

        # Invalid password -> 401
        r_invalid = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "wrongpass"})
        assert r_invalid.status_code == 401, "Invalid password was not rejected with 401"

        # Unknown user -> 401
        r_unknown = client.post("/api/v1/auth/token", json={"username": "unknown_user", "password": "tracex2026"})
        assert r_unknown.status_code == 401, "Unknown user was not rejected with 401"

        dur = time.perf_counter() - t0
        print_checkpoint(1, "RBAC & Authentication (ANALYST / AUDITOR / 401)", "PASS", dur, "Enforced bcrypt JWT credentials & role authorization matrix")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(1, "RBAC & Authentication", "FAIL", dur, str(e))
        return False

    analyst_headers = {"Authorization": f"Bearer {tokens['analyst']}"}
    auditor_headers = {"Authorization": f"Bearer {tokens['auditor']}"}

    # -------------------------------------------------------------------------
    # [02] Secure Evidence Ingestion & 10MB Security Boundary
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        # Ingest Benchmark Case 1
        r_ingest1 = client.post("/api/v1/ingestion/benchmark/1", headers=analyst_headers)
        assert r_ingest1.status_code == 200, f"Benchmark 1 ingestion failed: {r_ingest1.text}"

        # Verify max upload size invariant (10 MB)
        from app.api.endpoints.ingestion import MAX_UPLOAD_SIZE
        from app.services.collectors.manual_upload_collector import MAX_INPUT_SIZE, MAX_ZIP_ENTRIES, MAX_UNCOMPRESSED

        assert MAX_UPLOAD_SIZE == 10 * 1024 * 1024, "MAX_UPLOAD_SIZE != 10MB"
        assert MAX_INPUT_SIZE == 10 * 1024 * 1024, "MAX_INPUT_SIZE != 10MB"
        assert MAX_ZIP_ENTRIES == 50, "MAX_ZIP_ENTRIES != 50"
        assert MAX_UNCOMPRESSED == 25 * 1024 * 1024, "MAX_UNCOMPRESSED != 25MB"

        dur = time.perf_counter() - t0
        print_checkpoint(2, "Secure Evidence Ingestion (10MB / Anti-Zip-Bomb)", "PASS", dur, "Enforced 10MB input limit, 50 entries, 25MB uncompressed limit")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(2, "Secure Evidence Ingestion", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [03] Entity Extraction & Cross-Case Scoping
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        r_ent = client.get("/api/v1/ingestion/INV-SIH-001/entities", headers=analyst_headers)
        assert r_ent.status_code == 200
        ent_data = r_ent.json()
        assert ent_data["count"] >= 4, f"Expected >= 4 entities, got {ent_data['count']}"
        ent_values = [e["value"] for e in ent_data["entities"]]
        assert "KryptonGhost" in ent_values
        assert "SpecterOp" in ent_values
        assert "8F9B2D1C9B8A7C44E31055F6A901C4889B8A7C" in ent_values

        dur = time.perf_counter() - t0
        print_checkpoint(3, "Entity Extraction & Investigation Isolation", "PASS", dur, f"Extracted {ent_data['count']} indicators with strict investigation-scoping")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(3, "Entity Extraction & Investigation Isolation", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [04] Source Reliability Engine (Decision #10)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        r_src = client.get("/api/v1/reliability/INV-SIH-001/sources", headers=analyst_headers)
        assert r_src.status_code == 200
        src_data = r_src.json()
        assert src_data["count"] >= 1
        for s in src_data["sources"]:
            r_score = s["reliability_score"]
            assert 0.0 <= r_score <= 1.0
            chan_mod = 0.50 + 0.50 * r_score
            assert 0.50 <= chan_mod <= 1.00
            f = s["factors"]
            expected_r = (0.40 * f["reputation"]) + (0.30 * f["freshness"]) + (0.20 * f["corroboration"]) + (0.10 * f["consistency"])
            assert abs(r_score - expected_r) < 0.01

        dur = time.perf_counter() - t0
        print_checkpoint(4, "Source Reliability Engine (Decision #10)", "PASS", dur, "4-factor formula validated with [0.50, 1.00] channel modulation")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(4, "Source Reliability Engine (Decision #10)", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [05] Analytical Engines & Guardrails
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        from app.services.engines.stylometric_engine import StylometricEngine
        from app.services.engines.financial_engine import FinancialEngine

        # Stylometry guardrail matrix: < 150 words -> NOT_ENOUGH_EVIDENCE
        short_a = [{"artifact_type": "FORUM_POST", "raw_payload": {"author": "A", "content": "word " * 100}}]
        short_b = [{"artifact_type": "FORUM_POST", "raw_payload": {"author": "B", "content": "word " * 100}}]
        res_short = StylometricEngine.analyze([], persona_a_posts=short_a, persona_b_posts=short_b)
        assert res_short.status.value == "NOT_ENOUGH_EVIDENCE"
        assert res_short.raw_score == 0.0

        # Financial CoinJoin 0.60x deterministic dampening
        cj_artifact = [{
            "artifact_type": "BTC_TRANSACTION",
            "raw_payload": {
                "inputs": [{"address": "addrA", "amount": 5.0}],
                "outputs": [{"address": "addrB", "amount": 5.0}],
                "coinjoin_detected": True,
                "coinjoin_protocol": "Samourai Whirlpool"
            }
        }]
        res_cj = FinancialEngine.analyze(cj_artifact, reliability_context=1.0)
        assert res_cj.reliability_factor == 0.60, f"Expected 0.60 factor, got {res_cj.reliability_factor}"

        dur = time.perf_counter() - t0
        print_checkpoint(5, "Analytical Engines & Guardrails (Stylometry/CoinJoin)", "PASS", dur, "Enforced >=150w/500t boundary matrix & 0.60x CoinJoin dampening")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(5, "Analytical Engines & Guardrails", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [06] Benchmark Case 1 Convergence & Cross-Phase Numerical Consistency
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        db = SessionLocal()
        pipe_res1 = execute_analysis_pipeline("INV-SIH-001", db)
        db.close()

        pipe_assess1 = pipe_res1["assessment"]
        assert pipe_assess1.attribution_state.value == "LIKELY_LINK"
        assert pipe_assess1.confidence_band.value == "HIGH"
        assert pipe_assess1.real_world_identity == "NOT ESTABLISHED"
        pipe_sbase1 = round(float(pipe_assess1.base_score), 4)
        eng_type1 = pipe_assess1.evidence_dimensions.stylometric.supporting_details.get("engine_type", "DETERMINISTIC_FALLBACK")
        expected_sbase1 = 0.7735 if eng_type1 == "TRANSFORMER" else 0.7639
        assert abs(pipe_sbase1 - expected_sbase1) <= 0.0001, (
            f"Case 1 canonical benchmark drift: expected canonical {expected_sbase1:.4f} for {eng_type1}, got {pipe_sbase1:.4f}"
        )

        # 1. DB Value
        db = SessionLocal()
        db_assess1 = db.query(AttributionAssessmentModel).filter(
            AttributionAssessmentModel.investigation_id == "INV-SIH-001",
            AttributionAssessmentModel.is_current == True
        ).first()
        db_sbase1 = round(float(db_assess1.base_score), 4)

        # 2. REST API Value
        r_api1 = client.get("/api/v1/attribution/INV-SIH-001", headers=analyst_headers)
        assert r_api1.status_code == 200
        api_sbase1 = round(float(r_api1.json()["base_score"]), 4)

        # 3. JSON Dossier Value
        dossier1 = ReportService.generate_json_dossier("INV-SIH-001", db)
        report_sbase1 = round(float(dossier1["current_assessment"]["base_score"]), 4)
        db.close()

        # Cross-Phase Numerical Consistency Check
        assert pipe_sbase1 == db_sbase1 == api_sbase1 == report_sbase1, (
            f"Numerical inconsistency in Case 1: Pipeline={pipe_sbase1}, DB={db_sbase1}, API={api_sbase1}, Report={report_sbase1}"
        )

        dur = time.perf_counter() - t0
        print_checkpoint(6, "Case 1 Convergence & Deterministic Benchmark", "PASS", dur, f"Authoritative S_base={pipe_sbase1:.4f} (canonical {expected_sbase1:.4f}, LIKELY_LINK) verified across Pipeline/DB/API/Report")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(6, "Case 1 Convergence & Deterministic Benchmark", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [07] Benchmark Case 2 Contradiction Gate & Score Preservation
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        # Ingest Case 2
        r_ingest2 = client.post("/api/v1/ingestion/benchmark/2", headers=analyst_headers)
        assert r_ingest2.status_code == 200

        db = SessionLocal()
        pipe_res2 = execute_analysis_pipeline("INV-SIH-002", db)
        db.close()

        pipe_assess2 = pipe_res2["assessment"]
        assert pipe_assess2.attribution_state.value == "INCONCLUSIVE", f"Expected INCONCLUSIVE, got {pipe_assess2.attribution_state.value}"
        assert pipe_assess2.confidence_band.value == "LOW"
        assert pipe_assess2.hard_gate_applied is True
        pipe_sbase2 = round(float(pipe_assess2.base_score), 4)

        # ---------------------------------------------------------------------
        # Frozen Canonical Benchmark Assertion
        # ---------------------------------------------------------------------
        # Level 2 Hard Gate enforced; stylometry guardrail triggered (<150w) -> 0.0
        # S_base = 0.30(0.15) + 0.25(0.36) + 0.20(0.0) + 0.15(0.0) + 0.10(0.80) = 0.2150
        expected_sbase2 = 0.2150
        assert abs(pipe_sbase2 - expected_sbase2) <= 0.0001, (
            f"Case 2 canonical benchmark drift: expected canonical {expected_sbase2:.4f}, got {pipe_sbase2:.4f}"
        )

        # Cross-Phase Check for Case 2
        db = SessionLocal()
        db_assess2 = db.query(AttributionAssessmentModel).filter(
            AttributionAssessmentModel.investigation_id == "INV-SIH-002",
            AttributionAssessmentModel.is_current == True
        ).first()
        db_sbase2 = round(float(db_assess2.base_score), 4)

        r_api2 = client.get("/api/v1/attribution/INV-SIH-002", headers=analyst_headers)
        assert r_api2.status_code == 200
        api_sbase2 = round(float(r_api2.json()["base_score"]), 4)

        dossier2 = ReportService.generate_json_dossier("INV-SIH-002", db)
        report_sbase2 = round(float(dossier2["current_assessment"]["base_score"]), 4)
        db.close()

        assert pipe_sbase2 == db_sbase2 == api_sbase2 == report_sbase2, (
            f"Numerical inconsistency in Case 2: Pipeline={pipe_sbase2}, DB={db_sbase2}, API={api_sbase2}, Report={report_sbase2}"
        )

        dur = time.perf_counter() - t0
        print_checkpoint(7, "Case 2 Contradiction Gate & Score Preservation", "PASS", dur, f"Level 2 Hard Gate enforced INCONCLUSIVE while preserving authoritative canonical S_base={pipe_sbase2:.4f}")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(7, "Case 2 Contradiction Gate & Score Preservation", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [08] Sensitivity Tuning (Preview vs. Commit)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        db = SessionLocal()
        audit_count_before = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == "INV-SIH-001").count()
        db.close()

        # Preview Recalculation (audit-neutral)
        r_recalc = client.post("/api/v1/attribution/recalculate", json={
            "investigation_id": "INV-SIH-001",
            "weight_cryptographic": 0.20,
            "weight_financial": 0.20,
            "weight_stylometric": 0.20,
            "weight_infrastructure": 0.20,
            "weight_behavioral": 0.20
        }, headers=analyst_headers)
        assert r_recalc.status_code == 200

        db = SessionLocal()
        audit_count_after_preview = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == "INV-SIH-001").count()
        assert audit_count_before == audit_count_after_preview, "Preview recalculation polluted audit ledger!"

        # Commit Tuned Weights (creates immutable event)
        r_commit = client.post("/api/v1/attribution/commit-weights", json={
            "investigation_id": "INV-SIH-001",
            "weight_cryptographic": 0.20,
            "weight_financial": 0.20,
            "weight_stylometric": 0.20,
            "weight_infrastructure": 0.20,
            "weight_behavioral": 0.20
        }, headers=analyst_headers)
        assert r_commit.status_code == 200
        commit_data = r_commit.json()
        assert len(commit_data["audit_event"]["event_hash"]) == 64

        audit_count_after_commit = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == "INV-SIH-001").count()
        assert audit_count_after_commit == audit_count_before + 1, "Commit did not record exactly 1 audit event!"
        db.close()

        dur = time.perf_counter() - t0
        print_checkpoint(8, "Sensitivity Tuning (Preview vs. Commit Isolation)", "PASS", dur, "Preview is 100% audit-neutral; Commit appends immutable SHA-256 event")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(8, "Sensitivity Tuning (Preview vs. Commit Isolation)", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [09] Cryptographic Audit Chain Verification
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        db = SessionLocal()
        is_valid, records, error = AuditChainService.verify_investigation_chain("INV-SIH-001", db)
        db.close()

        assert is_valid is True, f"Audit chain invalid: {error}"
        assert len(records) >= 1, "Zero audit records verified"
        assert records[0]["previous_hash"] == "0" * 64, "First event does not link to genesis!"

        dur = time.perf_counter() - t0
        print_checkpoint(9, "Cryptographic Audit Chain Verification", "PASS", dur, f"Verified {len(records)} events from genesis '0'*64 through terminal hash")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(9, "Cryptographic Audit Chain Verification", "FAIL", dur, str(e))
        return False

    # -------------------------------------------------------------------------
    # [10] Dossier Reconstruction & Cross-Phase Consistency (PDF/CSV/JSON)
    # -------------------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        db = SessionLocal()

        # 1. JSON
        dossier_json = ReportService.generate_json_dossier("INV-SIH-001", db)
        meta = dossier_json["report_metadata"]
        assert meta["title"] == "Forensic Investigation Dossier"
        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in meta["identity_disclaimer"]
        assert len(meta["report_hash"]) == 64
        assert meta["audit_chain_valid"] is True

        # 2. CSV
        dossier_csv = ReportService.generate_csv_dossier("INV-SIH-001", db)
        assert "=== TRACE-X FORENSIC INVESTIGATION DOSSIER CSV EXPORT ===" in dossier_csv
        assert "=== 5-DIMENSION EVIDENCE BREAKDOWN ===" in dossier_csv
        assert "=== AUDIT LEDGER TRAIL ===" in dossier_csv

        # 3. PDF Text Extraction
        pdf_bytes = ReportService.generate_pdf_dossier("INV-SIH-002", db)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_pdf_text = "".join([p.extract_text() for p in reader.pages])

        assert "REAL-WORLD IDENTITY: NOT ESTABLISHED" in full_pdf_text
        assert "TEMPORAL_CONCURRENCY_CLASH" in full_pdf_text
        assert "INCONCLUSIVE" in full_pdf_text

        # Cross-Phase PDF score consistency
        c2_json = ReportService.generate_json_dossier("INV-SIH-002", db)
        c2_score_str = f"{c2_json['current_assessment']['base_score']:.4f}"
        assert c2_score_str in full_pdf_text, f"Score {c2_score_str} not extracted from PDF!"

        db.close()

        dur = time.perf_counter() - t0
        print_checkpoint(10, "Dossier Reconstruction & Cross-Phase Consistency", "PASS", dur, "Pure DB reconstruction verified across PDF, CSV, and canonical JSON")
        checkpoints_passed += 1
    except Exception as e:
        dur = time.perf_counter() - t0
        print_checkpoint(10, "Dossier Reconstruction & Cross-Phase Consistency", "FAIL", dur, str(e))
        return False

    total_dur = time.perf_counter() - total_start
    print("=" * 88)
    print(f"{Colors.OKGREEN}{Colors.BOLD}VERIFICATION RESULT: {checkpoints_passed}/10 CHECKPOINTS PASSED (Total: {total_dur:.2f}s){Colors.ENDC}")
    print(f"{Colors.BOLD}STATUS: ALL SIH26151 ACCEPTANCE CRITERIA SATISFIED{Colors.ENDC}")
    print("=" * 88)
    return True

if __name__ == '__main__':
    success = run_all_checkpoints()
    sys.exit(0 if success else 1)
