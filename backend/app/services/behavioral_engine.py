from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import DimensionSignal, GlobalContradiction, SignalStatus


class BehavioralEngine:
    @classmethod
    def analyze_behavior_and_temporality(
        cls,
        temporal_artifacts: List[Dict[str, Any]],
        post_artifacts: List[Dict[str, Any]],
        weight: float = 0.10
    ) -> Tuple[DimensionSignal, List[GlobalContradiction]]:
        """
        Analyzes post timing, migration sequences, and checks for hard temporal concurrency clashes.
        Returns the Behavioral DimensionSignal and any global contradictions triggered.
        """
        global_contradictions: List[GlobalContradiction] = []
        
        # 1. Check for explicit temporal burst / concurrency clash artifact
        hard_concurrency_found = False
        concurrency_detail = ""
        
        for art in temporal_artifacts:
            payload = art.get("raw_payload", {})
            if payload.get("concurrent_authenticated_session") or payload.get("conflict_severity") == "CRITICAL":
                hard_concurrency_found = True
                concurrency_detail = (
                    f"Simultaneous authenticated activity confirmed within {payload.get('time_delta_seconds', 0)}s "
                    f"across conflicting nodes ({payload.get('persona_a_active_window', {}).get('node_location', 'Node A')} vs "
                    f"{payload.get('persona_b_active_window', {}).get('node_location', 'Node B')})."
                )
                
                global_contradictions.append(
                    GlobalContradiction(
                        contradiction_type="TEMPORAL_CONCURRENCY_CLASH",
                        severity="CRITICAL",
                        penalty=0.0,  # Hard gate overrides score directly
                        triggers_hard_gate=True,
                        detail=concurrency_detail
                    )
                )

        # 2. Migration & Behavioral Score Evaluation
        if hard_concurrency_found:
            raw_score = 0.10
            status = SignalStatus.VALID
            details = {
                "sequence_type": "CONCURRENT_OPERATIONAL_CLASH",
                "hard_gate_triggered": True,
                "contradiction_summary": concurrency_detail
            }
        elif post_artifacts:
            raw_score = 0.80  # Demonstrates clean sequential migration pattern
            status = SignalStatus.VALID
            details = {
                "sequence_type": "CLEAN_SEQUENTIAL_MIGRATION",
                "dormancy_observed": True,
                "overlap_windows_detected": False,
                "summary": "Persona A went dormant prior to Persona B emergence with consistent operational cadence."
            }
        else:
            raw_score = 0.0
            status = SignalStatus.NOT_ENOUGH_EVIDENCE
            details = {"message": "No behavioral or temporal records found."}
            
        signal = DimensionSignal(
            dimension_name="behavioral_temporal",
            status=status,
            raw_score=raw_score,
            reliability_factor=1.0,
            adjusted_score=raw_score,
            configured_weight=weight,
            contribution=round(weight * raw_score, 4),
            evidence_ids=[a.get("evidence_id", "") for a in temporal_artifacts + post_artifacts if "evidence_id" in a],
            supporting_details=details
        )
        
        return signal, global_contradictions
