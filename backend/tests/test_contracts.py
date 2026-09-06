import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.models.contracts import (
    ImmutableContract,
    NormalizedArtifact,
    ExtractedEntity,
    SourceReliabilityAssessment,
    DimensionSignal,
    ContradictionFinding,
    AttributionAssessment,
    AuditEvent,
    ArtifactType,
    EntityType,
    DimensionType,
    ReliabilityClass,
    ScanStatus,
    SignalStatus,
    ContradictionLevel,
    AttributionState,
    ConfidenceBand,
    AuditEventType,
)

VALID_HEX64 = "a" * 64
VALID_HEX64_B = "b" * 64
GENESIS_HASH = "0" * 64


def test_immutable_mutation_rejected():
    """Verify that attempting to mutate any contract field raises a ValidationError."""
    signal = DimensionSignal(
        dimension=DimensionType.CRYPTOGRAPHIC,
        raw_score=0.95,
        reliability_factor=1.0,
        adjusted_score=0.95,
        status=SignalStatus.VALID,
    )
    with pytest.raises(ValidationError):
        signal.raw_score = 0.50


def test_extra_fields_rejected():
    """Verify that extra='forbid' rejects any undeclared field."""
    with pytest.raises(ValidationError) as excinfo:
        ExtractedEntity(
            entity_id="ENT-001",
            entity_type=EntityType.PERSONA,
            value="DarkOperator",
            evidence_id="EV-100",
            confidence=0.90,
            unauthorized_extra_field="malicious_payload",
        )
    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_numeric_ranges_rejected():
    """Verify that float fields strictly enforce [0.0, 1.0] bounds."""
    # Test below 0.0
    with pytest.raises(ValidationError):
        DimensionSignal(
            dimension=DimensionType.FINANCIAL,
            raw_score=-0.01,
            reliability_factor=1.0,
            adjusted_score=0.0,
        )

    # Test above 1.0
    with pytest.raises(ValidationError):
        DimensionSignal(
            dimension=DimensionType.FINANCIAL,
            raw_score=1.05,
            reliability_factor=1.0,
            adjusted_score=1.0,
        )

    # Test confidence out of bounds
    with pytest.raises(ValidationError):
        ExtractedEntity(
            entity_id="ENT-002",
            entity_type=EntityType.WALLET,
            value="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            evidence_id="EV-101",
            confidence=1.2,
        )


def test_hex64_pattern_validation():
    """Verify that SHA-256 hashes must be exactly 64 hexadecimal characters."""
    now = datetime.now(timezone.utc)

    # Valid 64-char hex
    artifact = NormalizedArtifact(
        evidence_id="EV-001",
        investigation_id="INV-001",
        artifact_type=ArtifactType.PGP_KEY,
        source_uri="https://darknet.example/thread/1",
        collected_at=now,
        content_hash=VALID_HEX64,
        raw_payload={"key": "val"},
        normalized_payload={"key": "val"},
    )
    assert artifact.content_hash == VALID_HEX64

    # Invalid: 63 characters
    with pytest.raises(ValidationError):
        NormalizedArtifact(
            evidence_id="EV-002",
            investigation_id="INV-001",
            artifact_type=ArtifactType.PGP_KEY,
            source_uri="https://darknet.example/thread/2",
            collected_at=now,
            content_hash="a" * 63,
            raw_payload={},
            normalized_payload={},
        )

    # Invalid: non-hex characters
    with pytest.raises(ValidationError):
        NormalizedArtifact(
            evidence_id="EV-003",
            investigation_id="INV-001",
            artifact_type=ArtifactType.PGP_KEY,
            source_uri="https://darknet.example/thread/3",
            collected_at=now,
            content_hash=("g" * 64),
            raw_payload={},
            normalized_payload={},
        )


def test_enum_values_validated():
    """Verify that invalid enum strings are rejected with ValidationError."""
    with pytest.raises(ValidationError):
        DimensionSignal(
            dimension="INVALID_DIMENSION",  # type: ignore
            raw_score=0.8,
            reliability_factor=1.0,
            adjusted_score=0.8,
        )


def test_json_round_trip_and_datetime_serialization():
    """Verify that models serialize to JSON and deserialize back with identical fields."""
    now = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
    rel = SourceReliabilityAssessment(
        source_uri="synthetic-forum-feed-01",
        reliability_score=0.85,
        reliability_class=ReliabilityClass.HIGH,
        factors={"reputation": 0.90, "freshness": 0.80, "corroboration": 0.85, "consistency": 0.85},
        last_scan=now,
        scan_status=ScanStatus.HEALTHY,
    )

    json_str = rel.model_dump_json()
    reconstructed = SourceReliabilityAssessment.model_validate_json(json_str)

    assert reconstructed == rel
    assert reconstructed.last_scan == now
    assert reconstructed.reliability_class == ReliabilityClass.HIGH


def test_nested_contract_serialization():
    """Verify composite AttributionAssessment containing nested DimensionSignals and Contradictions."""
    now = datetime(2026, 3, 6, 12, 30, 0, tzinfo=timezone.utc)

    signals = {
        DimensionType.CRYPTOGRAPHIC: DimensionSignal(
            dimension=DimensionType.CRYPTOGRAPHIC,
            raw_score=0.95,
            reliability_factor=1.0,
            adjusted_score=0.95,
            evidence_ids=["EV-PGP-01"],
        ),
        DimensionType.FINANCIAL: DimensionSignal(
            dimension=DimensionType.FINANCIAL,
            raw_score=0.90,
            reliability_factor=0.60,
            adjusted_score=0.54,
            evidence_ids=["EV-TX-01"],
        ),
        DimensionType.STYLOMETRIC: DimensionSignal(
            dimension=DimensionType.STYLOMETRIC,
            raw_score=0.84,
            reliability_factor=1.0,
            adjusted_score=0.84,
            evidence_ids=["EV-POST-01"],
        ),
        DimensionType.INFRASTRUCTURE: DimensionSignal(
            dimension=DimensionType.INFRASTRUCTURE,
            raw_score=0.65,
            reliability_factor=1.0,
            adjusted_score=0.65,
            evidence_ids=["EV-INFRA-01"],
        ),
        DimensionType.BEHAVIORAL_TEMPORAL: DimensionSignal(
            dimension=DimensionType.BEHAVIORAL_TEMPORAL,
            raw_score=0.80,
            reliability_factor=1.0,
            adjusted_score=0.80,
            evidence_ids=["EV-BURST-01"],
        ),
    }

    contradictions = [
        ContradictionFinding(
            level=ContradictionLevel.LEVEL_1_CHANNEL_DAMPENING,
            contradiction_type="POTENTIAL_COINJOIN",
            target_dimension=DimensionType.FINANCIAL,
            dampening_factor=0.60,
            trigger_hard_gate=False,
            explanation="Equal-denomination collaborative transaction detected.",
            evidence_ids=["EV-TX-01"],
        )
    ]

    assessment = AttributionAssessment(
        assessment_id="ASSESS-INV-001",
        investigation_id="INV-001",
        attribution_state=AttributionState.LIKELY_LINK,
        confidence_band=ConfidenceBand.HIGH,
        base_score=0.7655,
        real_world_identity="NOT ESTABLISHED",
        dimension_signals=signals,
        contradictions=contradictions,
        hard_gate_applied=False,
        rationale="Strong multi-modal evidence convergence with financial channel dampening.",
        is_current=True,
        created_at=now,
    )

    json_data = assessment.model_dump_json()
    restored = AttributionAssessment.model_validate_json(json_data)
    assert restored == assessment
    assert restored.base_score == 0.7655
    assert restored.dimension_signals[DimensionType.FINANCIAL].adjusted_score == 0.54


def test_audit_event_hash_chain_contract():
    """Verify first event has genesis hash ('0'*64) and subsequent event links previous hash."""
    now = datetime(2026, 3, 6, 13, 0, 0, tzinfo=timezone.utc)

    # First event uses '0'*64
    event1 = AuditEvent(
        event_id="AUDIT-001",
        investigation_id="INV-001",
        event_type=AuditEventType.EVIDENCE_INGESTED,
        actor_id="ANALYST-001",
        timestamp=now,
        canonical_event_data='{"action":"INGEST"}',
        previous_event_hash=GENESIS_HASH,
        event_hash=VALID_HEX64,
    )
    assert event1.previous_event_hash == "0" * 64

    # Subsequent event references previous event_hash
    event2 = AuditEvent(
        event_id="AUDIT-002",
        investigation_id="INV-001",
        event_type=AuditEventType.ANALYST_DECISION,
        actor_id="ANALYST-001",
        timestamp=now,
        canonical_event_data='{"action":"CONFIRMED"}',
        previous_event_hash=event1.event_hash,
        event_hash=VALID_HEX64_B,
    )
    assert event2.previous_event_hash == event1.event_hash


def test_benchmark_fixtures_deterministic(frozen_benchmark_case_1, frozen_benchmark_case_2):
    """Verify that frozen benchmark fixtures load properly and contain expected persona targets."""
    assert frozen_benchmark_case_1["investigation_id"] == "INV-SIH-001"
    assert len(frozen_benchmark_case_1["artifacts"]) > 0
    assert frozen_benchmark_case_2["investigation_id"] == "INV-SIH-002"
    assert len(frozen_benchmark_case_2["artifacts"]) > 0


def test_canonical_weights_sum_to_one(canonical_weights):
    """Verify that canonical attribution weights sum exactly to 1.0."""
    total_weight = sum(canonical_weights.values())
    assert round(total_weight, 6) == 1.0
