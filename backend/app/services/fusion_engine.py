from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    AttributionAssessment,
    AttributionState,
    ConfidenceBand,
    EvidenceDimensionsBlock,
    DimensionSignal,
    ChannelDampening,
    GlobalContradiction,
    AssessmentRationale,
    SignalStatus
)
from app.models.contracts import (
    AttributionAssessment as ContractAttributionAssessment,
    DimensionSignal as ContractDimensionSignal,
    ContradictionFinding,
    ContradictionLevel,
    DimensionType,
    AttributionState as ContractAttributionState,
    ConfidenceBand as ContractConfidenceBand
)


class EvidenceFusionEngine:
    """
    Canonical Two-Level Contradiction Evidence Fusion Engine.
    
    LOCKED INVARIANTS:
    1. Five canonical default weights:
       - Cryptographic: 0.30
       - Financial: 0.25
       - Stylometric: 0.20
       - Infrastructure: 0.15
       - Behavioral / Temporal: 0.10
       Sum = 1.00.
    2. Strict Level 1 Channel Dampening:
       - Modifies only channel-specific reliability factor (e.g. CoinJoin affects financial * 0.60;
         translation affects stylometry * 0.80). Never subtracts globally from base_score.
    3. Fused S_base:
       S_base = sum(w_i * adjusted_score_i)
    4. Strict Level 2 Global Hard Gate (TEMPORAL_CONCURRENCY_CLASH):
       - Overrides attribution_state to INCONCLUSIVE.
       - Maps confidence_band to LOW (ConfidenceBand.INCONCLUSIVE does not exist).
       - Preserves calculated base_score for analyst explainability (never zeroed out).
       - Sets hard_gate_applied = True, hard_gate_reason = ...
       - Weight tuning / sensitivity recalculation CANNOT bypass a triggered hard gate.
    5. State Machine & Exact Threshold Boundaries:
       - Hard gate: INCONCLUSIVE (band LOW)
       - S_base >= 0.85 AND crypto_signal.adjusted_score > 0.80: CONFIRMED_LINK (band HIGH)
       - S_base >= 0.70: LIKELY_LINK (band HIGH)
       - S_base >= 0.50: POSSIBLE_LINK (band MEDIUM)
       - S_base < 0.20 AND validated_negative_evidence: LIKELY_DIFFERENT (band LOW)
       - Otherwise: INCONCLUSIVE (band LOW)
    6. Identity Invariant:
       - real_world_identity remains permanently "NOT ESTABLISHED".
    7. No evidence_score field; base_score is the canonical numerical assessment score.
    """
    CANONICAL_WEIGHTS = {
        "cryptographic": 0.30,
        "financial": 0.25,
        "stylometric": 0.20,
        "infrastructure": 0.15,
        "behavioral_temporal": 0.10,
    }

    @classmethod
    def fuse_evidence(
        cls,
        assessment_id: str,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        crypto_signal: DimensionSignal,
        financial_signal: DimensionSignal,
        stylometry_signal: DimensionSignal,
        infra_signal: DimensionSignal,
        behavioral_signal: DimensionSignal,
        global_contradictions: List[Any]
    ) -> AttributionAssessment:
        """
        Executes the Two-Level Contradiction Evidence Fusion Model.
        """
        # Collect Level 1 channel dampening explanations
        channel_dampenings: List[ChannelDampening] = []
        if financial_signal.reliability_factor < 1.0 or any(
            "COINJOIN" in str(f) for f in getattr(financial_signal, "findings", [])
        ):
            protocol = financial_signal.supporting_details.get("coinjoin_protocol") or "Collaborative transaction / CoinJoin pattern detected"
            for f in getattr(financial_signal, "findings", []):
                if isinstance(f, dict) and "protocol" in f:
                    protocol = f["protocol"]
            channel_dampenings.append(
                ChannelDampening(
                    dimension="financial",
                    factor_applied=financial_signal.reliability_factor,
                    reason=protocol
                )
            )

        if stylometry_signal.reliability_factor < 1.0 or any(
            "TRANSLATION" in str(f) for f in getattr(stylometry_signal, "findings", [])
        ):
            reason = "Cross-language syntax / translation variation"
            channel_dampenings.append(
                ChannelDampening(
                    dimension="stylometric",
                    factor_applied=stylometry_signal.reliability_factor,
                    reason=reason
                )
            )

        # 1. Base Weighted Score (Stage 1 with Level 1 adjustments)
        signals = [crypto_signal, financial_signal, stylometry_signal, infra_signal, behavioral_signal]
        base_score = sum(s.configured_weight * s.adjusted_score for s in signals)
        base_score = round(base_score, 4)

        # 2. Global Contradiction Processing (Stage 2)
        global_multiplier = 1.0
        hard_gate_triggered = False
        hard_gate_reason: Optional[str] = None

        for contra in global_contradictions:
            is_hard_gate = (
                getattr(contra, "triggers_hard_gate", False)
                or getattr(contra, "trigger_hard_gate", False)
                or getattr(contra, "level", None) == ContradictionLevel.LEVEL_2_HARD_GATE
                or (getattr(contra, "severity", "") == "CRITICAL" and "CONCURRENCY" in str(getattr(contra, "contradiction_type", "")))
            )
            detail = (
                getattr(contra, "explanation", None)
                or getattr(contra, "detail", None)
                or "Level 2 hard gate triggered"
            )
            if is_hard_gate:
                hard_gate_triggered = True
                hard_gate_reason = detail
            else:
                penalty = getattr(contra, "penalty", 0.0) or 0.0
                global_multiplier *= (1.0 - penalty)

        # Check behavioral signal findings for hard gate candidates if not already caught
        if not hard_gate_triggered:
            for f in getattr(behavioral_signal, "findings", []):
                if isinstance(f, dict) and (f.get("triggers_hard_gate_candidate") or f.get("finding") == "TEMPORAL_CONCURRENCY_CLASH"):
                    hard_gate_triggered = True
                    hard_gate_reason = f.get("observation") or "Active authenticated concurrency verified across distinct exit infrastructure."
                    break

        global_multiplier = round(global_multiplier, 4)

        # Validated negative evidence detection:
        # Cannot be triggered merely by Level 1 dampening (CoinJoin or translation).
        # Requires conflicting key fingerprints / contradictory signals.
        has_contradictory_finding = any(
            any(
                isinstance(f, dict) and (
                    f.get("evidence_strength") == "CONTRADICTORY"
                    or f.get("rule") == "INCONSISTENT_KEYPAIR_HYPOTHESIS"
                )
                for f in getattr(s, "findings", [])
            )
            for s in signals
        )
        has_crypto_conflict = (
            crypto_signal.raw_score <= 0.15
            and getattr(crypto_signal, "status", SignalStatus.VALID) == SignalStatus.VALID
            and len(getattr(crypto_signal, "evidence_ids", [])) > 0
        )
        has_non_dampening_contra = any(
            not getattr(c, "triggers_hard_gate", False)
            and not getattr(c, "trigger_hard_gate", False)
            and getattr(c, "contradiction_type", "") not in (
                "POTENTIAL_COINJOIN", "TRANSLATION_VARIATION", "POTENTIAL_COINJOIN_DETECTED", "TRANSLATION_VARIATION_DETECTED"
            )
            for c in global_contradictions
        )
        validated_negative_evidence = (has_contradictory_finding or has_crypto_conflict or has_non_dampening_contra)

        # 3. Decision Boundary Mapping & State Classification
        # Exact threshold rules:
        # - Hard gate: INCONCLUSIVE (band LOW), base_score preserved
        # - S_base >= 0.85 AND crypto_signal.adjusted_score > 0.80: CONFIRMED_LINK (band HIGH)
        # - S_base >= 0.70: LIKELY_LINK (band HIGH)
        # - S_base >= 0.50: POSSIBLE_LINK (band MEDIUM)
        # - S_base < 0.20 AND validated_negative_evidence: LIKELY_DIFFERENT (band LOW)
        # - Otherwise: INCONCLUSIVE (band LOW)
        if hard_gate_triggered:
            state = AttributionState.INCONCLUSIVE
            band = ConfidenceBand.LOW
            c_min, c_max = 0.0, 0.49
            rationale_summary = f"HARD GATE TRIGGERED: Attribution halted and capped at INCONCLUSIVE due to mutually exclusive operational clash ({hard_gate_reason})."
        elif base_score >= 0.85 and crypto_signal.adjusted_score > 0.80:
            state = AttributionState.CONFIRMED_LINK
            band = ConfidenceBand.HIGH
            c_min, c_max = 0.85, 0.96
            rationale_summary = "High-confidence multi-modal convergence backed by direct cryptographic key reuse (adjusted score > 0.80) and multi-source corroboration without contradiction."
        elif base_score >= 0.70:
            state = AttributionState.LIKELY_LINK
            band = ConfidenceBand.HIGH
            c_min, c_max = 0.70, 0.84
            rationale_summary = "Evidence substantially favors persona linkage across financial, stylometric, and behavioral migration signals."
        elif base_score >= 0.50:
            state = AttributionState.POSSIBLE_LINK
            band = ConfidenceBand.MEDIUM
            c_min, c_max = 0.50, 0.69
            rationale_summary = "Correlative indicators observed, but plausible alternative explanations remain."
        elif base_score < 0.20 and validated_negative_evidence:
            state = AttributionState.LIKELY_DIFFERENT
            band = ConfidenceBand.LOW
            c_min, c_max = 0.05, 0.25
            rationale_summary = "Low multi-modal alignment coupled with validated conflicting provenance indicates structurally separate operators."
        else:
            state = AttributionState.INCONCLUSIVE
            band = ConfidenceBand.LOW
            c_min, c_max = 0.0, 0.49
            rationale_summary = "Collected evidence is statistically insufficient or highly ambiguous."

        # Count supporting signals (adjusted score >= 0.50)
        supporting_count = sum(1 for s in signals if s.adjusted_score >= 0.50)

        # Normalize global_contradictions to list of GlobalContradiction models for schemas
        normalized_contras: List[GlobalContradiction] = []
        for c in global_contradictions:
            if isinstance(c, GlobalContradiction):
                normalized_contras.append(c)
            elif isinstance(c, dict):
                normalized_contras.append(GlobalContradiction(
                    contradiction_type=c.get("contradiction_type", "CONTRADICTION"),
                    severity=c.get("severity", "CRITICAL" if c.get("triggers_hard_gate") else "HIGH"),
                    penalty=c.get("penalty", 0.0),
                    triggers_hard_gate=c.get("triggers_hard_gate", False),
                    detail=c.get("detail", c.get("explanation", ""))
                ))
            elif hasattr(c, "contradiction_type"):
                normalized_contras.append(GlobalContradiction(
                    contradiction_type=c.contradiction_type,
                    severity="CRITICAL" if getattr(c, "trigger_hard_gate", False) else "HIGH",
                    penalty=getattr(c, "dampening_factor", 0.0) or 0.0,
                    triggers_hard_gate=getattr(c, "trigger_hard_gate", False),
                    detail=getattr(c, "explanation", "")
                ))

        return AttributionAssessment(
            assessment_id=assessment_id,
            investigation_id=investigation_id,
            target_persona_a=persona_a,
            target_persona_b=persona_b,
            attribution_state=state,
            confidence_band=band,
            confidence_range_min=c_min,
            confidence_range_max=c_max,
            base_score=base_score,
            global_penalty_multiplier=global_multiplier,
            real_world_identity="NOT ESTABLISHED",
            evidence_dimensions=EvidenceDimensionsBlock(
                cryptographic=crypto_signal,
                financial=financial_signal,
                stylometric=stylometry_signal,
                infrastructure=infra_signal,
                behavioral_temporal=behavioral_signal
            ),
            channel_dampenings=channel_dampenings,
            global_contradictions=normalized_contras,
            hard_gate_applied=hard_gate_triggered,
            hard_gate_reason=hard_gate_reason,
            assessment_rationale=AssessmentRationale(
                summary=rationale_summary,
                supporting_signal_count=supporting_count,
                contradiction_count=len(channel_dampenings) + len(normalized_contras),
                hard_gate_applied=hard_gate_triggered,
                hard_gate_reason=hard_gate_reason
            ),
            created_at=datetime.now(timezone.utc)
        )

    @classmethod
    def fuse_contract(
        cls,
        assessment_id: str,
        investigation_id: str,
        signals: Dict[DimensionType, ContractDimensionSignal],
        contradictions: Optional[List[ContradictionFinding]] = None,
        weights: Optional[Dict[DimensionType, float]] = None
    ) -> ContractAttributionAssessment:
        """
        Pure immutable contract fusion engine adhering to Phase 0 contracts.py.
        """
        canonical_weights = {
            DimensionType.CRYPTOGRAPHIC: 0.30,
            DimensionType.FINANCIAL: 0.25,
            DimensionType.STYLOMETRIC: 0.20,
            DimensionType.INFRASTRUCTURE: 0.15,
            DimensionType.BEHAVIORAL_TEMPORAL: 0.10,
        }
        active_weights = weights or canonical_weights
        contradictions = contradictions or []

        # 1. Compute Base Score
        base_score = 0.0
        for dim, w in active_weights.items():
            sig = signals.get(dim)
            if sig:
                base_score += w * sig.adjusted_score
        base_score = round(base_score, 4)

        # 2. Check Level 2 Hard Gates
        hard_gate_triggered = False
        hard_gate_reason: Optional[str] = None
        for c in contradictions:
            if c.trigger_hard_gate or c.level == ContradictionLevel.LEVEL_2_HARD_GATE:
                hard_gate_triggered = True
                hard_gate_reason = c.explanation
                break

        # Check temporal signal findings
        beh_sig = signals.get(DimensionType.BEHAVIORAL_TEMPORAL)
        if not hard_gate_triggered and beh_sig:
            for f in beh_sig.findings:
                if isinstance(f, dict) and (f.get("triggers_hard_gate_candidate") or f.get("finding") == "TEMPORAL_CONCURRENCY_CLASH"):
                    hard_gate_triggered = True
                    hard_gate_reason = f.get("observation") or "Active authenticated concurrency verified across distinct exit infrastructure."
                    break

        crypto_sig = signals.get(DimensionType.CRYPTOGRAPHIC)
        crypto_adjusted = crypto_sig.adjusted_score if crypto_sig else 0.0

        # Validated negative evidence
        has_contradictory_finding = any(
            any(
                isinstance(f, dict) and (
                    f.get("evidence_strength") == "CONTRADICTORY"
                    or f.get("rule") == "INCONSISTENT_KEYPAIR_HYPOTHESIS"
                )
                for f in sig.findings
            )
            for sig in signals.values()
        )
        has_crypto_conflict = (
            crypto_sig is not None
            and crypto_sig.raw_score <= 0.15
            and crypto_sig.status == SignalStatus.VALID
            and len(crypto_sig.evidence_ids) > 0
        )
        validated_negative_evidence = has_contradictory_finding or has_crypto_conflict

        # 3. State Mapping
        if hard_gate_triggered:
            state = ContractAttributionState.INCONCLUSIVE
            band = ContractConfidenceBand.LOW
            rationale = f"HARD GATE TRIGGERED: Attribution halted and capped at INCONCLUSIVE due to mutually exclusive operational clash ({hard_gate_reason})."
        elif base_score >= 0.85 and crypto_adjusted > 0.80:
            state = ContractAttributionState.CONFIRMED_LINK
            band = ContractConfidenceBand.HIGH
            rationale = "High-confidence multi-modal convergence backed by direct cryptographic key reuse (adjusted score > 0.80)."
        elif base_score >= 0.70:
            state = ContractAttributionState.LIKELY_LINK
            band = ContractConfidenceBand.HIGH
            rationale = "Evidence substantially favors persona linkage across multi-modal indicators."
        elif base_score >= 0.50:
            state = ContractAttributionState.POSSIBLE_LINK
            band = ContractConfidenceBand.MEDIUM
            rationale = "Correlative indicators observed, but plausible alternative explanations remain."
        elif base_score < 0.20 and validated_negative_evidence:
            state = ContractAttributionState.LIKELY_DIFFERENT
            band = ContractConfidenceBand.LOW
            rationale = "Low multi-modal alignment coupled with validated conflicting provenance indicates structurally separate operators."
        else:
            state = ContractAttributionState.INCONCLUSIVE
            band = ContractConfidenceBand.LOW
            rationale = "Collected evidence is statistically insufficient or highly ambiguous."

        return ContractAttributionAssessment(
            assessment_id=assessment_id,
            investigation_id=investigation_id,
            attribution_state=state,
            confidence_band=band,
            base_score=base_score,
            real_world_identity="NOT ESTABLISHED",
            dimension_signals=signals,
            contradictions=contradictions,
            hard_gate_applied=hard_gate_triggered,
            hard_gate_reason=hard_gate_reason,
            rationale=rationale,
            is_current=True,
            created_at=datetime.now(timezone.utc)
        )
