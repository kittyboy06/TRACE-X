import pytest
from app.models.schemas import (
    DimensionSignal,
    SignalStatus,
    GlobalContradiction,
    AttributionState,
    ConfidenceBand
)
from app.models.contracts import (
    DimensionSignal as ContractDimensionSignal,
    ContradictionFinding,
    ContradictionLevel,
    DimensionType,
    AttributionAssessment as ContractAttributionAssessment,
    AttributionState as ContractAttributionState,
    ConfidenceBand as ContractConfidenceBand,
    SignalStatus as ContractSignalStatus
)
from app.services.fusion_engine import EvidenceFusionEngine


def test_fusion_arithmetic_case1_convergence():
    """
    Tests that Level 1 CoinJoin dampening only reduces the financial score
    without globally penalizing unrelated crypto or stylometry signals.
    Verifies Case 1 convergence: S_base = 0.7655 -> LIKELY_LINK, HIGH confidence.
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
    assert assessment.attribution_state == AttributionState.LIKELY_LINK
    assert assessment.confidence_band == ConfidenceBand.HIGH
    assert assessment.hard_gate_applied is False
    assert assessment.assessment_rationale.hard_gate_applied is False
    assert assessment.real_world_identity == "NOT ESTABLISHED"
    assert len(assessment.channel_dampenings) == 1
    assert assessment.channel_dampenings[0].dimension == "financial"


def test_fusion_hard_gate_concurrency_clash():
    """
    Tests that a Level 2 Global Hard Gate (Temporal Concurrency Clash)
    immediately caps and overrides the attribution state to INCONCLUSIVE with LOW confidence,
    while preserving the calculated base_score for explainability.
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

    # Base score is preserved for analyst explainability (~0.769)
    assert assessment.base_score == pytest.approx(0.769, rel=1e-3)
    # Regardless of high base score, hard gate strictly forces INCONCLUSIVE and LOW confidence
    assert assessment.attribution_state == AttributionState.INCONCLUSIVE
    assert assessment.confidence_band == ConfidenceBand.LOW
    assert assessment.hard_gate_applied is True
    assert assessment.hard_gate_reason == "Active authenticated concurrency verified on separate exit nodes."
    assert assessment.assessment_rationale.hard_gate_applied is True
    assert "HARD GATE TRIGGERED" in assessment.assessment_rationale.summary
    assert assessment.real_world_identity == "NOT ESTABLISHED"


def test_hard_gate_cannot_be_bypassed_by_numeric_weights():
    """
    LOCKED INVARIANT: Analyst weight manipulation or extreme sensitivity tuning
    (e.g. boosting crypto weight to 1.0) can NEVER bypass a Level 2 hard gate.
    """
    # Create signals where crypto is boosted to 1.0 weight
    crypto_sig = DimensionSignal(
        dimension_name="cryptographic", raw_score=0.98, reliability_factor=1.0,
        adjusted_score=0.98, configured_weight=1.00, contribution=0.98
    )
    fin_sig = DimensionSignal(
        dimension_name="financial", raw_score=0.0, reliability_factor=1.0,
        adjusted_score=0.0, configured_weight=0.0, contribution=0.0
    )
    style_sig = DimensionSignal(
        dimension_name="stylometric", raw_score=0.0, reliability_factor=1.0,
        adjusted_score=0.0, configured_weight=0.0, contribution=0.0
    )
    infra_sig = DimensionSignal(
        dimension_name="infrastructure", raw_score=0.0, reliability_factor=1.0,
        adjusted_score=0.0, configured_weight=0.0, contribution=0.0
    )
    beh_sig = DimensionSignal(
        dimension_name="behavioral_temporal", raw_score=0.0, reliability_factor=1.0,
        adjusted_score=0.0, configured_weight=0.0, contribution=0.0
    )

    hard_gate = GlobalContradiction(
        contradiction_type="TEMPORAL_CONCURRENCY_CLASH",
        severity="CRITICAL",
        triggers_hard_gate=True,
        detail="Simultaneous administrative broadcast observed."
    )

    assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id="TEST-BYPASS-01",
        investigation_id="INV-BYPASS-01",
        persona_a="PersonaA",
        persona_b="PersonaB",
        crypto_signal=crypto_sig,
        financial_signal=fin_sig,
        stylometry_signal=style_sig,
        infra_signal=infra_sig,
        behavioral_signal=beh_sig,
        global_contradictions=[hard_gate]
    )

    # Even with S_base = 0.98 and crypto > 0.80, the hard gate CANNOT BE BYPASSED
    assert assessment.base_score == pytest.approx(0.98, rel=1e-3)
    assert assessment.attribution_state == AttributionState.INCONCLUSIVE
    assert assessment.confidence_band == ConfidenceBand.LOW
    assert assessment.hard_gate_applied is True


def test_level_1_channel_dampening_isolation():
    """
    Verifies that Level 1 CoinJoin dampening only reduces the financial channel
    and does NOT discount or penalize independent cryptographic or stylometric signals.
    """
    def make_signals(coinjoin: bool):
        c = DimensionSignal(dimension_name="cryptographic", raw_score=0.90, reliability_factor=1.0,
                            adjusted_score=0.90, configured_weight=0.30, contribution=0.27)
        f_rel = 0.60 if coinjoin else 1.0
        f = DimensionSignal(dimension_name="financial", raw_score=0.80, reliability_factor=f_rel,
                            adjusted_score=round(0.80 * f_rel, 4), configured_weight=0.25,
                            contribution=round(0.25 * 0.80 * f_rel, 4))
        s = DimensionSignal(dimension_name="stylometric", raw_score=0.85, reliability_factor=1.0,
                            adjusted_score=0.85, configured_weight=0.20, contribution=0.17)
        i = DimensionSignal(dimension_name="infrastructure", raw_score=0.60, reliability_factor=1.0,
                            adjusted_score=0.60, configured_weight=0.15, contribution=0.09)
        b = DimensionSignal(dimension_name="behavioral_temporal", raw_score=0.70, reliability_factor=1.0,
                            adjusted_score=0.70, configured_weight=0.10, contribution=0.07)
        return c, f, s, i, b

    # Run without CoinJoin
    c1, f1, s1, i1, b1 = make_signals(coinjoin=False)
    res_clean = EvidenceFusionEngine.fuse_evidence("A1", "INV-1", "P1", "P2", c1, f1, s1, i1, b1, [])

    # Run with CoinJoin
    c2, f2, s2, i2, b2 = make_signals(coinjoin=True)
    res_dampened = EvidenceFusionEngine.fuse_evidence("A2", "INV-1", "P1", "P2", c2, f2, s2, i2, b2, [])

    # Crypto and Stylometry signals must be exactly identical
    assert res_clean.evidence_dimensions.cryptographic.adjusted_score == res_dampened.evidence_dimensions.cryptographic.adjusted_score
    assert res_clean.evidence_dimensions.stylometric.adjusted_score == res_dampened.evidence_dimensions.stylometric.adjusted_score
    assert res_clean.evidence_dimensions.infrastructure.adjusted_score == res_dampened.evidence_dimensions.infrastructure.adjusted_score
    assert res_clean.evidence_dimensions.behavioral_temporal.adjusted_score == res_dampened.evidence_dimensions.behavioral_temporal.adjusted_score

    # Only financial score is modified
    assert res_clean.evidence_dimensions.financial.adjusted_score == 0.80
    assert res_dampened.evidence_dimensions.financial.adjusted_score == 0.48
    # Score difference is exactly the financial contribution difference: 0.25 * (0.80 - 0.48) = 0.08
    assert res_clean.base_score - res_dampened.base_score == pytest.approx(0.08, rel=1e-3)


def test_translation_dampening_isolation():
    """
    Verifies that Level 1 translation dampening (0.80x) modifies only the stylometric channel.
    """
    c = DimensionSignal(dimension_name="cryptographic", raw_score=0.90, reliability_factor=1.0,
                        adjusted_score=0.90, configured_weight=0.30, contribution=0.27)
    f = DimensionSignal(dimension_name="financial", raw_score=0.80, reliability_factor=1.0,
                        adjusted_score=0.80, configured_weight=0.25, contribution=0.20)
    s = DimensionSignal(dimension_name="stylometric", raw_score=0.85, reliability_factor=0.80,
                        adjusted_score=0.68, configured_weight=0.20, contribution=0.136)
    i = DimensionSignal(dimension_name="infrastructure", raw_score=0.60, reliability_factor=1.0,
                        adjusted_score=0.60, configured_weight=0.15, contribution=0.09)
    b = DimensionSignal(dimension_name="behavioral_temporal", raw_score=0.70, reliability_factor=1.0,
                        adjusted_score=0.70, configured_weight=0.10, contribution=0.07)

    assessment = EvidenceFusionEngine.fuse_evidence("A3", "INV-1", "P1", "P2", c, f, s, i, b, [])
    assert len(assessment.channel_dampenings) == 1
    assert assessment.channel_dampenings[0].dimension == "stylometric"
    assert assessment.channel_dampenings[0].factor_applied == 0.80


def test_state_thresholds_exact_boundary_matrix():
    """
    Asserts the exact state machine boundary matrix:
    - S = 0.85, crypto = 0.81 -> CONFIRMED_LINK (Band: HIGH)
    - S = 0.85, crypto = 0.80 -> LIKELY_LINK (crypto not strictly > 0.80, so NOT confirmed)
    - S = 0.70 -> LIKELY_LINK (Band: HIGH)
    - S = 0.6999 -> POSSIBLE_LINK (Band: MEDIUM)
    - S = 0.50 -> POSSIBLE_LINK (Band: MEDIUM)
    - S = 0.4999 -> INCONCLUSIVE (Band: LOW)
    - S = 0.20 with negative evidence -> INCONCLUSIVE (rule is < 0.20)
    - S = 0.1999 with validated negative evidence -> LIKELY_DIFFERENT (Band: LOW)
    - S = 0.1999 without negative evidence -> INCONCLUSIVE (Band: LOW)
    """
    def run_eval(s_base: float, crypto_adj: float, has_negative_evidence: bool = False):
        # Construct signals to produce exact s_base
        c_sig = DimensionSignal(
            dimension_name="cryptographic",
            raw_score=crypto_adj,
            reliability_factor=1.0,
            adjusted_score=crypto_adj,
            configured_weight=1.0,
            contribution=s_base,
            findings=[{"evidence_strength": "CONTRADICTORY", "rule": "INCONSISTENT_KEYPAIR_HYPOTHESIS"}] if has_negative_evidence else []
        )
        c_sig.adjusted_score = crypto_adj
        dummy = DimensionSignal(dimension_name="financial", raw_score=0.0, reliability_factor=1.0,
                                adjusted_score=0.0, configured_weight=0.0, contribution=0.0)
        
        # Override configured_weight and contribution so sum equals s_base
        c_sig.configured_weight = s_base / crypto_adj if crypto_adj > 0 else 0.0
        
        return EvidenceFusionEngine.fuse_evidence(
            assessment_id="TEST-BOUNDARY",
            investigation_id="INV-BOUNDARY",
            persona_a="PersonaA",
            persona_b="PersonaB",
            crypto_signal=c_sig,
            financial_signal=dummy,
            stylometry_signal=dummy,
            infra_signal=dummy,
            behavioral_signal=dummy,
            global_contradictions=[]
        )

    # 1. Boundary: S = 0.85, crypto = 0.81 -> CONFIRMED_LINK
    res1 = run_eval(0.85, 0.81)
    assert res1.base_score == 0.85
    assert res1.attribution_state == AttributionState.CONFIRMED_LINK
    assert res1.confidence_band == ConfidenceBand.HIGH

    # 2. Boundary: S = 0.85, crypto = 0.80 -> NOT CONFIRMED (must be strictly > 0.80) -> LIKELY_LINK
    res2 = run_eval(0.85, 0.80)
    assert res2.base_score == 0.85
    assert res2.attribution_state == AttributionState.LIKELY_LINK
    assert res2.confidence_band == ConfidenceBand.HIGH

    # 3. Boundary: S = 0.70 -> LIKELY_LINK
    res3 = run_eval(0.70, 0.60)
    assert res3.base_score == 0.70
    assert res3.attribution_state == AttributionState.LIKELY_LINK
    assert res3.confidence_band == ConfidenceBand.HIGH

    # 4. Boundary: S = 0.6999 -> POSSIBLE_LINK
    res4 = run_eval(0.6999, 0.60)
    assert res4.base_score == 0.6999
    assert res4.attribution_state == AttributionState.POSSIBLE_LINK
    assert res4.confidence_band == ConfidenceBand.MEDIUM

    # 5. Boundary: S = 0.50 -> POSSIBLE_LINK
    res5 = run_eval(0.50, 0.40)
    assert res5.base_score == 0.50
    assert res5.attribution_state == AttributionState.POSSIBLE_LINK
    assert res5.confidence_band == ConfidenceBand.MEDIUM

    # 6. Boundary: S = 0.4999 without negative evidence -> INCONCLUSIVE
    res6 = run_eval(0.4999, 0.40)
    assert res6.base_score == 0.4999
    assert res6.attribution_state == AttributionState.INCONCLUSIVE
    assert res6.confidence_band == ConfidenceBand.LOW

    # 7. Boundary: S = 0.20 with negative evidence -> INCONCLUSIVE (must be strictly < 0.20)
    res7 = run_eval(0.20, 0.15, has_negative_evidence=True)
    assert res7.base_score == 0.20
    assert res7.attribution_state == AttributionState.INCONCLUSIVE
    assert res7.confidence_band == ConfidenceBand.LOW

    # 8. Boundary: S = 0.1999 with validated negative evidence -> LIKELY_DIFFERENT
    res8 = run_eval(0.1999, 0.15, has_negative_evidence=True)
    assert res8.base_score == 0.1999
    assert res8.attribution_state == AttributionState.LIKELY_DIFFERENT
    assert res8.confidence_band == ConfidenceBand.LOW

    # 9. Boundary: S = 0.1999 WITHOUT negative evidence -> INCONCLUSIVE (low score alone != different)
    res9 = run_eval(0.1999, 0.15, has_negative_evidence=False)
    assert res9.base_score == 0.1999
    assert res9.attribution_state == AttributionState.INCONCLUSIVE
    assert res9.confidence_band == ConfidenceBand.LOW


def test_case_2_reproducible_arithmetic():
    """
    Verifies exact reproducible arithmetic for Benchmark Case 2:
    - Target: ShadowBroker_X vs PhantomAccess
    - Anti-False-Positive Scenario: High numerical similarity (S_base ≈ 0.75) across multiple channels,
      but overridden by a Level 2 Global Hard Gate (TEMPORAL_CONCURRENCY_CLASH).
    - Dimensions:
      - Crypto: raw = 0.85, w = 0.30 -> contribution = 0.2550
      - Financial: raw = 0.80, w = 0.25 -> contribution = 0.2000
      - Stylometric: raw = 0.90, w = 0.20 -> contribution = 0.1800
      - Infrastructure: raw = 0.70, w = 0.15 -> contribution = 0.1050
      - Behavioral: raw = 0.10, w = 0.10 -> contribution = 0.0100
      - S_base = 0.2550 + 0.2000 + 0.1800 + 0.1050 + 0.0100 = 0.7500
    - Triggers Level 2 Hard Gate TEMPORAL_CONCURRENCY_CLASH
    - Result: base_score preserved = 0.7500, state = INCONCLUSIVE, band = LOW, hard_gate_applied = True
    """
    crypto_sig = DimensionSignal(
        dimension_name="cryptographic", raw_score=0.85, reliability_factor=1.0,
        adjusted_score=0.85, configured_weight=0.30, contribution=0.2550
    )
    fin_sig = DimensionSignal(
        dimension_name="financial", raw_score=0.80, reliability_factor=1.0,
        adjusted_score=0.80, configured_weight=0.25, contribution=0.2000
    )
    style_sig = DimensionSignal(
        dimension_name="stylometric", raw_score=0.90, reliability_factor=1.0,
        adjusted_score=0.90, configured_weight=0.20, contribution=0.1800
    )
    infra_sig = DimensionSignal(
        dimension_name="infrastructure", raw_score=0.70, reliability_factor=1.0,
        adjusted_score=0.70, configured_weight=0.15, contribution=0.1050
    )
    beh_sig = DimensionSignal(
        dimension_name="behavioral_temporal", raw_score=0.10, reliability_factor=1.0,
        adjusted_score=0.10, configured_weight=0.10, contribution=0.0100
    )

    clash_gate = GlobalContradiction(
        contradiction_type="TEMPORAL_CONCURRENCY_CLASH",
        severity="CRITICAL",
        triggers_hard_gate=True,
        detail="Simultaneous activity confirmed within 30s across Frankfurt and Singapore exit nodes."
    )

    assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id="ASSESS-CASE-2",
        investigation_id="INV-SIH-002",
        persona_a="ShadowBroker_X",
        persona_b="PhantomAccess",
        crypto_signal=crypto_sig,
        financial_signal=fin_sig,
        stylometry_signal=style_sig,
        infra_signal=infra_sig,
        behavioral_signal=beh_sig,
        global_contradictions=[clash_gate]
    )

    # Exactly 0.7500 base score preserved for explainability
    assert assessment.base_score == pytest.approx(0.7500, rel=1e-3)
    assert assessment.attribution_state == AttributionState.INCONCLUSIVE
    assert assessment.confidence_band == ConfidenceBand.LOW
    assert assessment.hard_gate_applied is True
    assert assessment.hard_gate_reason == "Simultaneous activity confirmed within 30s across Frankfurt and Singapore exit nodes."
    assert assessment.assessment_rationale.hard_gate_applied is True


def test_permanent_identity_disclaimer():
    """
    Verifies that real_world_identity is permanently set to 'NOT ESTABLISHED'.
    """
    dummy = DimensionSignal(dimension_name="cryptographic", raw_score=0.90, reliability_factor=1.0,
                            adjusted_score=0.90, configured_weight=0.30, contribution=0.27)
    assessment = EvidenceFusionEngine.fuse_evidence("ID-1", "INV-1", "A", "B", dummy, dummy, dummy, dummy, dummy, [])
    assert assessment.real_world_identity == "NOT ESTABLISHED"


def test_fuse_contract_compliance():
    """
    Verifies that EvidenceFusionEngine.fuse_contract produces an immutable Phase 0
    ContractAttributionAssessment conforming strictly to contracts.py.
    """
    signals = {
        DimensionType.CRYPTOGRAPHIC: ContractDimensionSignal(
            dimension=DimensionType.CRYPTOGRAPHIC, raw_score=0.95, reliability_factor=1.0,
            adjusted_score=0.95, status=ContractSignalStatus.VALID, evidence_ids=["EV-PGP-1"]
        ),
        DimensionType.FINANCIAL: ContractDimensionSignal(
            dimension=DimensionType.FINANCIAL, raw_score=0.90, reliability_factor=0.60,
            adjusted_score=0.54, status=ContractSignalStatus.VALID, evidence_ids=["EV-TX-1"]
        ),
        DimensionType.STYLOMETRIC: ContractDimensionSignal(
            dimension=DimensionType.STYLOMETRIC, raw_score=0.84, reliability_factor=1.0,
            adjusted_score=0.84, status=ContractSignalStatus.VALID, evidence_ids=["EV-POST-1"]
        ),
        DimensionType.INFRASTRUCTURE: ContractDimensionSignal(
            dimension=DimensionType.INFRASTRUCTURE, raw_score=0.65, reliability_factor=1.0,
            adjusted_score=0.65, status=ContractSignalStatus.VALID, evidence_ids=["EV-INFRA-1"]
        ),
        DimensionType.BEHAVIORAL_TEMPORAL: ContractDimensionSignal(
            dimension=DimensionType.BEHAVIORAL_TEMPORAL, raw_score=0.80, reliability_factor=1.0,
            adjusted_score=0.80, status=ContractSignalStatus.VALID, evidence_ids=["EV-TIME-1"]
        ),
    }

    contra = ContradictionFinding(
        level=ContradictionLevel.LEVEL_1_CHANNEL_DAMPENING,
        contradiction_type="POTENTIAL_COINJOIN",
        target_dimension=DimensionType.FINANCIAL,
        dampening_factor=0.60,
        trigger_hard_gate=False,
        explanation="Equal denomination collaborative transactions detected.",
        evidence_ids=["EV-TX-1"]
    )

    assessment = EvidenceFusionEngine.fuse_contract(
        assessment_id="CONTRACT-ASSESS-01",
        investigation_id="INV-001",
        signals=signals,
        contradictions=[contra]
    )

    assert isinstance(assessment, ContractAttributionAssessment)
    assert assessment.base_score == pytest.approx(0.7655, rel=1e-3)
    assert assessment.attribution_state == ContractAttributionState.LIKELY_LINK
    assert assessment.confidence_band == ContractConfidenceBand.HIGH
    assert assessment.hard_gate_applied is False
    assert assessment.real_world_identity == "NOT ESTABLISHED"

