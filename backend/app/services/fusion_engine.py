from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    AttributionAssessment,
    AttributionState,
    ConfidenceBand,
    EvidenceDimensionsBlock,
    DimensionSignal,
    ChannelDampening,
    GlobalContradiction,
    AssessmentRationale
)


class EvidenceFusionEngine:
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
        global_contradictions: List[GlobalContradiction]
    ) -> AttributionAssessment:
        """
        Executes the Two-Level Contradiction Evidence Fusion Model.
        """
        # Collect any Level 1 channel dampening explanations
        channel_dampenings: List[ChannelDampening] = []
        if financial_signal.reliability_factor < 1.0:
            channel_dampenings.append(
                ChannelDampening(
                    dimension="financial",
                    factor_applied=financial_signal.reliability_factor,
                    reason=financial_signal.supporting_details.get("coinjoin_protocol") or "Collaborative transaction / CoinJoin pattern detected"
                )
            )
        if stylometry_signal.reliability_factor < 1.0:
            channel_dampenings.append(
                ChannelDampening(
                    dimension="stylometric",
                    factor_applied=stylometry_signal.reliability_factor,
                    reason="Cross-language syntax / translation variation"
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
            if contra.triggers_hard_gate:
                hard_gate_triggered = True
                hard_gate_reason = contra.detail
            else:
                global_multiplier *= (1.0 - contra.penalty)

        global_multiplier = round(global_multiplier, 4)
        evidence_score = round(base_score * global_multiplier, 4)

        # 3. Decision Boundary Mapping & State Classification
        if hard_gate_triggered:
            state = AttributionState.INCONCLUSIVE
            band = ConfidenceBand.INCONCLUSIVE
            c_min, c_max = 0.0, 0.49
            rationale_summary = f"HARD GATE TRIGGERED: Attribution halted and capped at INCONCLUSIVE due to mutually exclusive operational clash ({hard_gate_reason})."
        elif evidence_score >= 0.85 and crypto_signal.adjusted_score > 0.80:
            state = AttributionState.CONFIRMED_LINK
            band = ConfidenceBand.VERY_HIGH
            c_min, c_max = 0.85, 0.96
            rationale_summary = "High-confidence multi-modal convergence backed by direct cryptographic key reuse and multi-source corroboration without contradiction."
        elif evidence_score >= 0.70:
            state = AttributionState.LIKELY_LINK
            band = ConfidenceBand.HIGH
            c_min, c_max = 0.75, 0.84
            rationale_summary = "Evidence substantially favors persona linkage across financial, stylometric, and behavioral migration signals."
        elif evidence_score >= 0.50:
            state = AttributionState.POSSIBLE_LINK
            band = ConfidenceBand.MODERATE
            c_min, c_max = 0.50, 0.69
            rationale_summary = "Correlative indicators observed, but plausible alternative explanations remain."
        elif evidence_score < 0.20 and len(global_contradictions) > 0:
            state = AttributionState.LIKELY_DIFFERENT
            band = ConfidenceBand.LOW
            c_min, c_max = 0.05, 0.25
            rationale_summary = "Low multi-modal alignment coupled with conflicting provenance indicates structurally separate operators."
        else:
            state = AttributionState.INCONCLUSIVE
            band = ConfidenceBand.INCONCLUSIVE
            c_min, c_max = 0.0, 0.49
            rationale_summary = "Collected evidence is statistically insufficient or highly ambiguous."

        # Count supporting signals (adjusted score >= 0.50)
        supporting_count = sum(1 for s in signals if s.adjusted_score >= 0.50)

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
            evidence_score=evidence_score,
            real_world_identity="NOT ESTABLISHED",
            evidence_dimensions=EvidenceDimensionsBlock(
                cryptographic=crypto_signal,
                financial=financial_signal,
                stylometric=stylometry_signal,
                infrastructure=infra_signal,
                behavioral_temporal=behavioral_signal
            ),
            channel_dampenings=channel_dampenings,
            global_contradictions=global_contradictions,
            assessment_rationale=AssessmentRationale(
                summary=rationale_summary,
                supporting_signal_count=supporting_count,
                contradiction_count=len(channel_dampenings) + len(global_contradictions),
                hard_cap_applied=hard_gate_triggered,
                hard_cap_reason=hard_gate_reason
            ),
            created_at=datetime.utcnow()
        )
