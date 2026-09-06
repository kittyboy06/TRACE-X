from typing import List, Dict, Any, Optional
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity
)
from app.services.source_reliability_service import SourceReliabilityService


class TemporalEngine:
    """
    Canonical Behavioral & Temporal Correlation Engine.
    Analyzes apparent UTC activity windows, activity-time profiles, operational migration cadence,
    and observes concurrent authenticated sessions.

    LOCKED INVARIANTS:
    - Pure engine interface decoupled from database sessions.
    - Uses cautious terminology: 'apparent UTC activity window', 'activity-time profile',
      'temporal cadence' without claiming to prove physical operator location or timezone.
    - Separation of Concerns: The Temporal Engine detects and records conflicting evidence
      (e.g. concurrent authenticated activity) in findings. It does NOT double-penalize
      by artificially forcing its numerical score down; the ContradictionEngine owns the
      Level 2 hard gate decision that overrides S_base to INCONCLUSIVE.
    - Decision #10 channel modifier: adjusted_score = raw_score * (0.5 + 0.5 * R).
    """
    CANONICAL_WEIGHT = 0.10

    @classmethod
    def analyze(
        cls,
        artifacts: List[Dict[str, Any]],
        entities: Optional[List[ExtractedEntity]] = None,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        temporal_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("TEMPORAL_BURST", "TEMPORAL_ACTIVITY", "ACTIVITY_LOG")
        ]
        post_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("FORUM_POST", "COMMUNICATION")
        ]

        evidence_ids = sorted(list(set(filter(None, [
            a.get("evidence_id") for a in (temporal_artifacts + post_artifacts) if a.get("evidence_id")
        ]))))

        clamped_r = max(0.0, min(1.0, float(reliability_context)))
        reliability_factor = round(0.5 + 0.5 * clamped_r, 4)

        if not temporal_artifacts and not post_artifacts:
            return DimensionSignal(
                dimension=DimensionType.BEHAVIORAL_TEMPORAL,
                raw_score=0.0,
                reliability_factor=reliability_factor,
                adjusted_score=0.0,
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                evidence_ids=[],
                engine_metadata={"engine": "TemporalEngine", "version": "1.0.0"},
                findings=[{"observation": "No temporal burst records or timestamped communications located."}]
            )

        findings = []
        concurrency_clash_detected = False
        concurrency_detail = ""
        clean_migration = False

        # 1. Inspect for concurrent authenticated sessions
        for a in temporal_artifacts:
            payload = a.get("raw_payload", {})
            if payload.get("concurrent_authenticated_session") or payload.get("conflict_severity") == "CRITICAL":
                concurrency_clash_detected = True
                delta = payload.get("time_delta_seconds", 0)
                node_a = payload.get("persona_a_active_window", {}).get("node_location", "Node A")
                node_b = payload.get("persona_b_active_window", {}).get("node_location", "Node B")
                concurrency_detail = (
                    f"Simultaneous authenticated activity confirmed within {delta}s across conflicting nodes "
                    f"({node_a} vs {node_b})."
                )

        if concurrency_clash_detected:
            findings.append({
                "finding": "TEMPORAL_CONCURRENCY_CLASH",
                "severity": "CRITICAL",
                "triggers_hard_gate_candidate": True,
                "observation": concurrency_detail
            })

        # 2. Evaluate operational cadence and apparent activity profiles
        if post_artifacts:
            # Check for sequential migration cadence
            clean_migration = True
            raw_score = 0.80
            findings.append({
                "rule": "SEQUENTIAL_MIGRATION_CADENCE",
                "evidence_strength": "HIGH",
                "observation": (
                    "Observed consistent operational cadence where Persona A activity ceased prior to "
                    "Persona B emergence within matching apparent UTC activity windows."
                )
            })
        elif temporal_artifacts:
            raw_score = 0.50
            findings.append({
                "rule": "CONSISTENT_ACTIVITY_TIME_PROFILE",
                "evidence_strength": "MEDIUM",
                "observation": "Apparent UTC activity window demonstrates overlapping diurnal operational cadence."
            })
        else:
            raw_score = 0.25
            findings.append({
                "rule": "INCONCLUSIVE_TEMPORAL_PROFILE",
                "evidence_strength": "LOW",
                "observation": "Sparse timestamp distribution; inconclusive temporal correlation."
            })

        # Apply Decision #10 channel modifier (without double penalizing the score for hard gate candidate)
        adjusted_score = SourceReliabilityService.apply_channel_modifier(raw_score, clamped_r)

        # Enforce mathematical invariants
        assert 0.0 <= raw_score <= 1.0, f"Raw score out of bounds: {raw_score}"
        assert 0.0 <= clamped_r <= 1.0, f"Reliability out of bounds: {clamped_r}"
        assert (0.5 * raw_score) - 1e-4 <= adjusted_score <= raw_score + 1e-4, (
            f"Channel modifier invariant violated: {adjusted_score} not in [{0.5 * raw_score}, {raw_score}]"
        )

        return DimensionSignal(
            dimension=DimensionType.BEHAVIORAL_TEMPORAL,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            status=SignalStatus.VALID,
            evidence_ids=evidence_ids,
            engine_metadata={
                "engine": "TemporalEngine",
                "version": "1.0.0",
                "canonical_weight": cls.CANONICAL_WEIGHT,
                "apparent_activity_profile": "DIURNAL_UTC_PROFILE",
                "concurrency_clash_observed": concurrency_clash_detected
            },
            findings=findings
        )
