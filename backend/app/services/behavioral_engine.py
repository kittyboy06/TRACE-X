from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import DimensionSignal, GlobalContradiction, SignalStatus
from app.services.engines.temporal_engine import TemporalEngine


class BehavioralEngine:
    """
    Compatibility facade re-exporting canonical TemporalEngine.
    """
    @classmethod
    def analyze_behavior_and_temporality(
        cls,
        temporal_artifacts: List[Dict[str, Any]],
        post_artifacts: List[Dict[str, Any]],
        weight: float = 0.10,
        reliability_context: float = 1.0
    ) -> Tuple[DimensionSignal, List[GlobalContradiction]]:
        contract_sig = TemporalEngine.analyze(
            artifacts=temporal_artifacts + post_artifacts,
            reliability_context=reliability_context
        )

        global_contradictions: List[GlobalContradiction] = []
        for finding in contract_sig.findings:
            if finding.get("finding") == "TEMPORAL_CONCURRENCY_CLASH":
                global_contradictions.append(
                    GlobalContradiction(
                        contradiction_type="TEMPORAL_CONCURRENCY_CLASH",
                        severity="CRITICAL",
                        penalty=0.0,  # Level 2 hard gate overrides score directly
                        triggers_hard_gate=True,
                        detail=finding.get("observation", "Concurrent authenticated sessions detected across conflicting nodes.")
                    )
                )

        status_val = SignalStatus(contract_sig.status.value)
        meta = contract_sig.engine_metadata

        signal = DimensionSignal(
            dimension_name="behavioral_temporal",
            status=status_val,
            raw_score=contract_sig.raw_score,
            reliability_factor=contract_sig.reliability_factor,
            adjusted_score=contract_sig.adjusted_score,
            configured_weight=weight,
            contribution=round(weight * contract_sig.adjusted_score, 4),
            evidence_ids=contract_sig.evidence_ids,
            supporting_details={
                "apparent_activity_profile": meta.get("apparent_activity_profile", "DIURNAL_UTC_PROFILE"),
                "concurrency_clash_observed": meta.get("concurrency_clash_observed", False),
                "findings": contract_sig.findings
            }
        )

        return signal, global_contradictions
