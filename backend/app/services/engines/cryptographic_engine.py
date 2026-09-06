from typing import List, Dict, Any, Optional
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity,
    EntityType
)
from app.services.source_reliability_service import SourceReliabilityService


class CryptographicEngine:
    """
    Canonical Cryptographic / PGP Correlation Engine.
    Analyzes subkey cross-certification, primary key bindings, and PGP keypair reuse.
    
    LOCKED INVARIANTS:
    - Pure engine interface decoupled from database sessions.
    - Decision #10 channel modifier: adjusted_score = raw_score * (0.5 + 0.5 * R).
    - Guaranteed mathematical invariant: 0.5 * raw_score <= adjusted_score <= raw_score.
    """
    CANONICAL_WEIGHT = 0.30

    @classmethod
    def analyze(
        cls,
        artifacts: List[Dict[str, Any]],
        entities: Optional[List[ExtractedEntity]] = None,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        # Filter PGP artifacts
        pgp_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("PGP_KEY", "CRYPTOGRAPHIC_KEY")
        ]
        
        # Also check PGP fingerprint entities if passed
        pgp_entities = [
            e for e in (entities or [])
            if getattr(e, "entity_type", None) == EntityType.PGP_FINGERPRINT
        ]

        evidence_ids = [
            a.get("evidence_id") for a in pgp_artifacts if a.get("evidence_id")
        ] + [
            getattr(e, "evidence_id", "") for e in pgp_entities if getattr(e, "evidence_id", "")
        ]
        evidence_ids = sorted(list(set(filter(None, evidence_ids))))

        # Clamped reliability context
        clamped_r = max(0.0, min(1.0, float(reliability_context)))
        reliability_factor = round(0.5 + 0.5 * clamped_r, 4)

        if not pgp_artifacts and not pgp_entities:
            return DimensionSignal(
                dimension=DimensionType.CRYPTOGRAPHIC,
                raw_score=0.0,
                reliability_factor=reliability_factor,
                adjusted_score=0.0,
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                evidence_ids=[],
                engine_metadata={"engine": "CryptographicEngine", "version": "1.0.0"},
                findings=[{"observation": "No cryptographic keys or PGP fingerprints located in evidence package."}]
            )

        findings = []
        
        # Inspect payloads
        shared_fingerprint = False
        subkey_cross_cert = False
        conflicting_keys = False
        observed_fingerprints = set()

        for a in pgp_artifacts:
            payload = a.get("raw_payload", {})
            if payload.get("shared_key") or payload.get("identical_primary_fingerprint"):
                shared_fingerprint = True
            if payload.get("subkey_cross_certification"):
                subkey_cross_cert = True
            if payload.get("conflicting_keys") or payload.get("distinct_algorithms"):
                conflicting_keys = True
            
            fp = payload.get("fingerprint") or payload.get("key_id")
            if fp:
                observed_fingerprints.add(fp)

        for e in pgp_entities:
            observed_fingerprints.add(e.value)

        # Evaluate scoring rules
        if shared_fingerprint or (len(observed_fingerprints) == 1 and len(pgp_artifacts) >= 2):
            raw_score = 0.95
            findings.append({
                "rule": "PRIMARY_KEY_REUSE",
                "evidence_strength": "VERY_HIGH",
                "observation": "Identical primary PGP keypair / fingerprint deployed across distinct persona profiles."
            })
        elif subkey_cross_cert:
            raw_score = 0.85
            findings.append({
                "rule": "SUBKEY_CROSS_CERTIFICATION",
                "evidence_strength": "HIGH",
                "observation": "Valid subkey cross-certification signature links secondary key to common primary keypair."
            })
        elif conflicting_keys or (len(observed_fingerprints) > 1 and not shared_fingerprint):
            raw_score = 0.15
            findings.append({
                "rule": "INCONSISTENT_KEYPAIR_HYPOTHESIS",
                "evidence_strength": "CONTRADICTORY",
                "observation": "raw_score = 0.15 indicating evidence inconsistent with the tested key-reuse hypothesis."
            })
        elif len(pgp_artifacts) == 1 or len(observed_fingerprints) == 1:
            raw_score = 0.50
            findings.append({
                "rule": "SINGLE_KEY_OBSERVED",
                "evidence_strength": "MEDIUM",
                "observation": "Single PGP key identified; awaiting counter-profile verification."
            })
        else:
            raw_score = 0.20
            findings.append({
                "rule": "GENERIC_KEY_OBSERVATION",
                "evidence_strength": "LOW",
                "observation": "Cryptographic material parsed without direct linkage."
            })

        # Apply Decision #10 channel modifier
        adjusted_score = SourceReliabilityService.apply_channel_modifier(raw_score, clamped_r)
        
        # Enforce mathematical invariants
        assert 0.0 <= raw_score <= 1.0, f"Raw score out of bounds: {raw_score}"
        assert 0.0 <= clamped_r <= 1.0, f"Reliability out of bounds: {clamped_r}"
        assert (0.5 * raw_score) - 1e-4 <= adjusted_score <= raw_score + 1e-4, (
            f"Channel modifier invariant violated: {adjusted_score} not in [{0.5 * raw_score}, {raw_score}]"
        )

        return DimensionSignal(
            dimension=DimensionType.CRYPTOGRAPHIC,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            status=SignalStatus.VALID,
            evidence_ids=evidence_ids,
            engine_metadata={
                "engine": "CryptographicEngine",
                "version": "1.0.0",
                "canonical_weight": cls.CANONICAL_WEIGHT,
                "observed_fingerprints_count": len(observed_fingerprints)
            },
            findings=findings
        )
