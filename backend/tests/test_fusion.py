import pytest
from app.models.schemas import (
    DimensionSignal,
    SignalStatus,
    GlobalContradiction,
    AttributionState,
    ConfidenceBand
)
from app.services.fusion_engine import EvidenceFusionEngine


def test_fusion_arithmetic_case1_convergence():
    """
    Tests that Level 1 CoinJoin dampening only reduces the financial score
    without globally penalizing unrelated crypto or stylometry signals.
    """
    crypto_sig = DimensionSignal(
        dimension_name="cryptographic",
        raw_score=0.95,
        reliability_factor=1.0,
        adjusted_score=0.95,
        configured_weight=0.30,
        contribution=0.285
    )
    
    # Financial signal with 40% CoinJoin dampening (reliability = 0.60, adjusted = 0.90 * 0.60 = 0.54)
    fin_sig = DimensionSignal(
        dimension_name="financial",
        raw_score=0.90,
        reliability_factor=0.60,
        adjusted_score=0.54,
        configured_weight=0.25,
        contribution=0.135
    )
    
    style_sig = DimensionSignal(
        dimension_name="stylometric",
        raw_score=0.84,
        reliability_factor=1.0,
        adjusted_score=0.84,
        configured_weight=0.20,
        contribution=0.168
    )
    
    infra_sig = DimensionSignal(
        dimension_name="infrastructure",
        raw_score=0.65,
        reliability_factor=1.0,
        adjusted_score=0.65,
        configured_weight=0.15,
        contribution=0.0975
    )
    
    beh_sig = DimensionSignal(
        dimension_name="behavioral_temporal",
        raw_score=0.80,
        reliability_factor=1.0,
        adjusted_score=0.80,
        configured_weight=0.10,
        contribution=0.080
    )

    assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id="TEST-ASSESS-01",
        investigation_id="INV-TEST-01",
        persona_a="KryptonGhost",
        persona_b="SpecterOp",
        crypto_signal=crypto_sig,
        financial_signal=fin_sig,
        stylometry_signal=style_sig,
        infra_signal=infra_sig,
        behavioral_signal=beh_sig,
        global_contradictions=[]
    )

    # Base sum = 0.285 + 0.135 + 0.168 + 0.0975 + 0.080 = 0.7655 -> 0.7655
    assert assessment.base_score == pytest.approx(0.7655, rel=1e-3)
    assert assessment.evidence_score == pytest.approx(0.7655, rel=1e-3)
    assert assessment.attribution_state == AttributionState.LIKELY_LINK
    assert assessment.confidence_band == ConfidenceBand.HIGH
    assert assessment.assessment_rationale.hard_cap_applied is False
    assert len(assessment.channel_dampenings) == 1
    assert assessment.channel_dampenings[0].dimension == "financial"


def test_fusion_hard_gate_concurrency_clash():
    """
    Tests that a Level 2 Global Hard Gate (Temporal Concurrency Clash)
    immediately caps and overrides the attribution state to INCONCLUSIVE.
    """
    # High base signals that would otherwise qualify for CONFIRMED/LIKELY
    crypto_sig = DimensionSignal(
        dimension_name="cryptographic", raw_score=0.90, reliability_factor=1.0,
        adjusted_score=0.90, configured_weight=0.30, contribution=0.27
    )
    fin_sig = DimensionSignal(
        dimension_name="financial", raw_score=0.80, reliability_factor=1.0,
        adjusted_score=0.80, configured_weight=0.25, contribution=0.20
    )
    style_sig = DimensionSignal(
        dimension_name="stylometric", raw_score=0.92, reliability_factor=1.0,
        adjusted_score=0.92, configured_weight=0.20, contribution=0.184
    )
    infra_sig = DimensionSignal(
        dimension_name="infrastructure", raw_score=0.70, reliability_factor=1.0,
        adjusted_score=0.70, configured_weight=0.15, contribution=0.105
    )
    beh_sig = DimensionSignal(
        dimension_name="behavioral_temporal", raw_score=0.10, reliability_factor=1.0,
        adjusted_score=0.10, configured_weight=0.10, contribution=0.01
    )

    hard_contradiction = GlobalContradiction(
        contradiction_type="TEMPORAL_CONCURRENCY_CLASH",
        severity="CRITICAL",
        penalty=0.0,
        triggers_hard_gate=True,
        detail="Active authenticated concurrency verified on separate exit nodes."
    )

    assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id="TEST-ASSESS-02",
        investigation_id="INV-TEST-02",
        persona_a="ShadowBroker_X",
        persona_b="PhantomAccess",
        crypto_signal=crypto_sig,
        financial_signal=fin_sig,
        stylometry_signal=style_sig,
        infra_signal=infra_sig,
        behavioral_signal=beh_sig,
        global_contradictions=[hard_contradiction]
    )

    # Regardless of high base score (~0.769), hard gate forces INCONCLUSIVE
    assert assessment.attribution_state == AttributionState.INCONCLUSIVE
    assert assessment.confidence_band == ConfidenceBand.INCONCLUSIVE
    assert assessment.assessment_rationale.hard_cap_applied is True
    assert "HARD GATE TRIGGERED" in assessment.assessment_rationale.summary
