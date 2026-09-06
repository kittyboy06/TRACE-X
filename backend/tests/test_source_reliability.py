import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.contracts import (
    SourceReliabilityAssessment,
    ReliabilityClass,
    ScanStatus,
    EntityType,
    ArtifactType
)
from app.models.database import (
    SessionLocal,
    InvestigationModel,
    SourceReliabilityModel,
    EvidenceRecordModel,
    ExtractedEntityModel
)
from app.services.source_reliability_service import (
    SourceReliabilityService,
    SourceTrustTier,
    TRUST_TIER_REPUTATION,
    WEIGHT_REPUTATION,
    WEIGHT_FRESHNESS,
    WEIGHT_CORROBORATION,
    WEIGHT_CONSISTENCY
)
from app.services.normalization_service import NormalizationService
from app.services.entity_extraction_service import EntityExtractionService

client = TestClient(app)


@pytest.fixture
def analyst_token():
    resp = client.post("/api/v1/auth/token", json={"username": "analyst", "password": "tracex2026"})
    return resp.json()["access_token"]


@pytest.fixture
def lead_auditor_token():
    resp = client.post("/api/v1/auth/token", json={"username": "lead_auditor", "password": "auditor2026"})
    return resp.json()["access_token"]


@pytest.fixture
def analyst_headers(analyst_token):
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def auditor_headers(lead_auditor_token):
    return {"Authorization": f"Bearer {lead_auditor_token}"}


def test_decision_10_weights_sum_to_one():
    """Verify that Decision #10 4-factor reliability weights sum exactly to 1.0."""
    total = WEIGHT_REPUTATION + WEIGHT_FRESHNESS + WEIGHT_CORROBORATION + WEIGHT_CONSISTENCY
    assert round(total, 6) == 1.0


def test_decision_10_channel_modifier_invariants():
    """
    Verify Decision #10 channel modifier mathematical invariants:
    adjusted = raw * (0.5 + 0.5 * R)
    Invariants:
    1. 0.5 * raw <= adjusted <= raw
    2. When R == 1.0: adjusted == raw
    3. When R == 0.0: adjusted == 0.5 * raw
    4. Monotonically non-decreasing with respect to R
    """
    raw_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    rel_values = [0.0, 0.2, 0.5, 0.75, 1.0]

    for raw in raw_values:
        # Boundary: R = 1.0
        adj_max = SourceReliabilityService.apply_channel_modifier(raw, 1.0)
        assert adj_max == pytest.approx(raw, abs=1e-4)

        # Boundary: R = 0.0
        adj_min = SourceReliabilityService.apply_channel_modifier(raw, 0.0)
        assert adj_min == pytest.approx(0.5 * raw, abs=1e-4)

        prev_adj = -1.0
        for rel in rel_values:
            adj = SourceReliabilityService.apply_channel_modifier(raw, rel)
            # Invariant 1: 0.5 * raw <= adj <= raw
            assert (0.5 * raw) - 1e-4 <= adj <= raw + 1e-4
            # Monotonicity check
            assert adj >= prev_adj - 1e-4
            prev_adj = adj

    # Clamping checks for out-of-bounds inputs
    assert SourceReliabilityService.apply_channel_modifier(0.8, -0.5) == pytest.approx(0.4, abs=1e-4)
    assert SourceReliabilityService.apply_channel_modifier(0.8, 1.5) == pytest.approx(0.8, abs=1e-4)


def test_exponential_decay_freshness():
    """
    Verify exponential decay freshness: 2^(-delta_t / 90.0).
    - delta_t = 0d   -> 1.00
    - delta_t = 90d  -> 0.50
    - delta_t = 180d -> 0.25
    - delta_t = 360d -> 0.0625
    - Future timestamps -> 1.00
    """
    ref_time = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    # 0 days
    f_0 = SourceReliabilityService.calculate_freshness(ref_time, reference_time=ref_time)
    assert f_0 == 1.0

    # 90 days
    t_90 = ref_time - timedelta(days=90)
    f_90 = SourceReliabilityService.calculate_freshness(t_90, reference_time=ref_time)
    assert f_90 == pytest.approx(0.50, abs=1e-3)

    # 180 days
    t_180 = ref_time - timedelta(days=180)
    f_180 = SourceReliabilityService.calculate_freshness(t_180, reference_time=ref_time)
    assert f_180 == pytest.approx(0.25, abs=1e-3)

    # 360 days
    t_360 = ref_time - timedelta(days=360)
    f_360 = SourceReliabilityService.calculate_freshness(t_360, reference_time=ref_time)
    assert f_360 == pytest.approx(0.0625, abs=1e-3)

    # Future date (clock skew / advance publication)
    t_future = ref_time + timedelta(days=5)
    f_future = SourceReliabilityService.calculate_freshness(t_future, reference_time=ref_time)
    assert f_future == 1.0


def test_source_trust_tier_classification():
    """Verify registry classification of source domains into SourceTrustTier."""
    gov_uris = [
        "https://cisa.gov/advisories/AA23-001",
        "https://cert.in/security-bulletin/2026",
        "https://fbi.gov/wanted/cyber"
    ]
    for u in gov_uris:
        assert SourceReliabilityService.classify_source_uri(u) == SourceTrustTier.VERIFIED_GOV_FED
        assert TRUST_TIER_REPUTATION[SourceTrustTier.VERIFIED_GOV_FED] == 0.95

    comm_uris = [
        "https://virustotal.com/gui/file/12345",
        "https://blockchain.info/tx/abcde",
        "https://etherscan.io/address/0x123",
        "https://github.com/torproject"
    ]
    for u in comm_uris:
        assert SourceReliabilityService.classify_source_uri(u) == SourceTrustTier.ESTABLISHED_COMMERCIAL
        assert TRUST_TIER_REPUTATION[SourceTrustTier.ESTABLISHED_COMMERCIAL] == 0.85

    onion_uris = [
        "http://darkmarketxyz7890.onion/listings",
        "https://dread.forum/post/999",
        "https://breached.vc/thread/123"
    ]
    for u in onion_uris:
        assert SourceReliabilityService.classify_source_uri(u) == SourceTrustTier.ADVERSARY_CONTROLLED_SUSPECTED
        assert TRUST_TIER_REPUTATION[SourceTrustTier.ADVERSARY_CONTROLLED_SUSPECTED] == 0.15

    comm_open_uris = [
        "https://reddit.com/r/cybersecurity/post",
        "https://twitter.com/threat_intel/status/123",
        "https://bitcointalk.org/index.php?topic=123"
    ]
    for u in comm_open_uris:
        assert SourceReliabilityService.classify_source_uri(u) == SourceTrustTier.OPEN_COMMUNITY
        assert TRUST_TIER_REPUTATION[SourceTrustTier.OPEN_COMMUNITY] == 0.60

    assert SourceReliabilityService.classify_source_uri("https://unknown-blog-12345.xyz") == SourceTrustTier.UNVERIFIED_UNKNOWN


def test_four_factor_evaluation_and_contract_validation():
    """Verify evaluation generates compliant SourceReliabilityAssessment contract."""
    db = SessionLocal()
    try:
        ref_time = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
        assessment, tier, diag = SourceReliabilityService.evaluate_source(
            db=db,
            investigation_id="INV-TEST-REL-001",
            source_uri="https://cisa.gov/advisories/aa-26",
            reference_time=ref_time
        )

        assert isinstance(assessment, SourceReliabilityAssessment)
        assert assessment.source_uri == "https://cisa.gov/advisories/aa-26"
        assert 0.0 <= assessment.reliability_score <= 1.0
        assert assessment.reliability_class in {ReliabilityClass.HIGH, ReliabilityClass.MEDIUM, ReliabilityClass.LOW}
        assert assessment.scan_status in {ScanStatus.HEALTHY, ScanStatus.STALE, ScanStatus.FAILED, ScanStatus.NEVER_SCANNED}
        assert "reputation" in assessment.factors
        assert "freshness" in assessment.factors
        assert "corroboration" in assessment.factors
        assert "consistency" in assessment.factors

        # High tier gov source with fresh timestamp should be HIGH
        assert assessment.reliability_score >= 0.80
        assert assessment.reliability_class == ReliabilityClass.HIGH
    finally:
        db.close()


def test_investigation_scoped_corroboration_isolation():
    """
    Verify corroboration is strictly isolated per investigation.
    Case A entities must not corroborate against Case B entities.
    """
    db = SessionLocal()
    try:
        inv_a = "INV-CORR-A"
        inv_b = "INV-CORR-B"

        # Cleanup existing
        db.query(ExtractedEntityModel).filter(
            ExtractedEntityModel.investigation_id.in_([inv_a, inv_b])
        ).delete(synchronize_session=False)
        db.query(EvidenceRecordModel).filter(
            EvidenceRecordModel.investigation_id.in_([inv_a, inv_b])
        ).delete(synchronize_session=False)
        db.commit()

        # In Investigation A: Source 1 observes Persona "Specter" and Wallet "1A1z"
        ev_a1 = EvidenceRecordModel(
            evidence_id="EV-A1",
            investigation_id=inv_a,
            source_uri="https://source-1.com/intel",
            artifact_type="FORUM_POST",
            content_hash="a"*64,
            raw_payload={},
            extractor_version="1.0.0",
            provenance_chain=[],
            collected_at=datetime.now(timezone.utc)
        )
        db.add(ev_a1)

        ent_a1 = ExtractedEntityModel(
            entity_id="ENT-A1",
            evidence_id="EV-A1",
            investigation_id=inv_a,
            entity_type=EntityType.PERSONA.value,
            value="Specter",
            confidence=0.9
        )
        ent_a2 = ExtractedEntityModel(
            entity_id="ENT-A2",
            evidence_id="EV-A1",
            investigation_id=inv_a,
            entity_type=EntityType.WALLET.value,
            value="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            confidence=0.9
        )
        db.add_all([ent_a1, ent_a2])

        # In Investigation A: Source 2 ALSO observes Persona "Specter"
        ev_a2 = EvidenceRecordModel(
            evidence_id="EV-A2",
            investigation_id=inv_a,
            source_uri="https://source-2.com/intel",
            artifact_type="BLOCKCHAIN_TX",
            content_hash="b"*64,
            raw_payload={},
            extractor_version="1.0.0",
            provenance_chain=[],
            collected_at=datetime.now(timezone.utc)
        )
        db.add(ev_a2)

        ent_a3 = ExtractedEntityModel(
            entity_id="ENT-A3",
            evidence_id="EV-A2",
            investigation_id=inv_a,
            entity_type=EntityType.PERSONA.value,
            value="Specter",
            confidence=0.9
        )
        db.add(ent_a3)
        db.commit()

        # In Investigation B: Source 3 observes Persona "Specter"
        ev_b1 = EvidenceRecordModel(
            evidence_id="EV-B1",
            investigation_id=inv_b,
            source_uri="https://source-3.com/intel",
            artifact_type="FORUM_POST",
            content_hash="c"*64,
            raw_payload={},
            extractor_version="1.0.0",
            provenance_chain=[],
            collected_at=datetime.now(timezone.utc)
        )
        db.add(ev_b1)
        ent_b1 = ExtractedEntityModel(
            entity_id="ENT-B1",
            evidence_id="EV-B1",
            investigation_id=inv_b,
            entity_type=EntityType.PERSONA.value,
            value="Specter",
            confidence=0.9
        )
        db.add(ent_b1)
        db.commit()

        # Source 1 in Inv A: observed 2 entities ("Specter", "1A1z").
        # Other source in Inv A (Source 2) observed "Specter". Overlap is 1/2 = 0.50
        corr_a1 = SourceReliabilityService.calculate_corroboration(db, inv_a, "https://source-1.com/intel")
        assert corr_a1 == 0.50

        # Source 2 in Inv A: observed 1 entity ("Specter").
        # Other source in Inv A (Source 1) observed "Specter". Overlap is 1/1 = 1.00
        corr_a2 = SourceReliabilityService.calculate_corroboration(db, inv_a, "https://source-2.com/intel")
        assert corr_a2 == 1.00

        # Source 3 in Inv B: only source in Inv B, so no other sources in Inv B exist -> neutral fallback 0.50!
        corr_b1 = SourceReliabilityService.calculate_corroboration(db, inv_b, "https://source-3.com/intel")
        assert corr_b1 == 0.50
    finally:
        db.close()


def test_reliability_persistence_and_upsert():
    """Verify upsert semantics on (investigation_id, source_uri)."""
    db = SessionLocal()
    try:
        inv_id = "INV-UPSERT-TEST"
        source_uri = "https://virustotal.com/api/v3"

        # 1st evaluation
        assess1, tier1, diag1 = SourceReliabilityService.evaluate_source(
            db=db,
            investigation_id=inv_id,
            source_uri=source_uri
        )
        p1 = SourceReliabilityService.persist_assessment(
            db=db,
            assessment=assess1,
            investigation_id=inv_id,
            trust_tier=tier1,
            diagnostic_status=diag1
        )
        rec_id = p1.id

        # 2nd evaluation with updated diagnostic
        p2 = SourceReliabilityService.persist_assessment(
            db=db,
            assessment=assess1,
            investigation_id=inv_id,
            trust_tier=tier1,
            diagnostic_status="Updated status check"
        )
        assert p2.id == rec_id
        assert p2.diagnostic_status == "Updated status check"

        # Ensure single record exists
        count = db.query(SourceReliabilityModel).filter(
            SourceReliabilityModel.investigation_id == inv_id,
            SourceReliabilityModel.source_uri == source_uri
        ).count()
        assert count == 1
    finally:
        db.close()


def test_reliability_endpoints_rbac(analyst_headers, auditor_headers):
    """Verify authorization and RBAC for /api/v1/reliability endpoints."""
    # 1. Unauthenticated -> 401
    r_unauth = client.post("/api/v1/reliability/evaluate", json={
        "investigation_id": "INV-SIH-001",
        "source_uri": "https://blockchain.info"
    })
    assert r_unauth.status_code == 401

    # 2. Unauthorized analyst -> 403
    r_forbidden = client.post(
        "/api/v1/reliability/evaluate",
        json={
            "investigation_id": "INV-RESTRICTED-002",
            "source_uri": "https://blockchain.info"
        },
        headers=analyst_headers
    )
    assert r_forbidden.status_code == 403

    # 3. Authorized analyst on assigned case -> 200
    r_analyst = client.post(
        "/api/v1/reliability/evaluate",
        json={
            "investigation_id": "INV-SIH-001",
            "source_uri": "https://blockchain.info"
        },
        headers=analyst_headers
    )
    assert r_analyst.status_code == 200
    data = r_analyst.json()
    assert data["investigation_id"] == "INV-SIH-001"
    assert data["trust_tier"] == "ESTABLISHED_COMMERCIAL"
    assert data["assessment"]["reliability_class"] in ["HIGH", "MEDIUM", "LOW"]

    # 4. Lead auditor on restricted case -> 200
    r_auditor = client.post(
        "/api/v1/reliability/evaluate",
        json={
            "investigation_id": "INV-RESTRICTED-002",
            "source_uri": "https://cisa.gov"
        },
        headers=auditor_headers
    )
    assert r_auditor.status_code == 200

    # 5. GET /api/v1/reliability/{investigation_id}/sources
    r_sources = client.get("/api/v1/reliability/INV-SIH-001/sources", headers=analyst_headers)
    assert r_sources.status_code == 200
    res_data = r_sources.json()
    assert res_data["investigation_id"] == "INV-SIH-001"
    assert res_data["count"] >= 1
    assert any(s["source_uri"] == "https://blockchain.info" for s in res_data["sources"])
