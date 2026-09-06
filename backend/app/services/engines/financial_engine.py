from typing import List, Dict, Any, Optional
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity,
    EntityType
)
from app.services.source_reliability_service import SourceReliabilityService


class FinancialEngine:
    """
    Canonical Financial / Blockchain Forensics Engine.
    Analyzes UTXO transactions, Common-Input-Ownership Heuristic (CIOH) clustering,
    centralized VASP hops, and collaborative transaction (CoinJoin) mixing.

    LOCKED INVARIANTS:
    - Pure engine interface decoupled from database sessions.
    - CIOH identifies a heuristic association among inputs that may indicate common control;
      collaborative transactions can invalidate that assumption.
    - CoinJoin triggers deterministic channel dampening (factor * 0.60) without arbitrary subtraction
      or affecting unrelated dimensions.
    """
    CANONICAL_WEIGHT = 0.25
    COINJOIN_DAMPENING_FACTOR = 0.60

    @classmethod
    def analyze(
        cls,
        artifacts: List[Dict[str, Any]],
        entities: Optional[List[ExtractedEntity]] = None,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        tx_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("BTC_TRANSACTION", "BLOCKCHAIN_TX", "FINANCIAL_TRANSACTION")
        ]
        wallet_entities = [
            e for e in (entities or [])
            if getattr(e, "entity_type", None) == EntityType.WALLET
        ]

        evidence_ids = [
            a.get("evidence_id") for a in tx_artifacts if a.get("evidence_id")
        ] + [
            getattr(e, "evidence_id", "") for e in wallet_entities if getattr(e, "evidence_id", "")
        ]
        evidence_ids = sorted(list(set(filter(None, evidence_ids))))

        clamped_r = max(0.0, min(1.0, float(reliability_context)))
        base_rel_modifier = round(0.5 + 0.5 * clamped_r, 4)

        if not tx_artifacts and not wallet_entities:
            return DimensionSignal(
                dimension=DimensionType.FINANCIAL,
                raw_score=0.0,
                reliability_factor=base_rel_modifier,
                adjusted_score=0.0,
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                evidence_ids=[],
                engine_metadata={"engine": "FinancialEngine", "version": "1.0.0"},
                findings=[{"observation": "No cryptocurrency transactions or wallet addresses found in evidence package."}]
            )

        findings = []
        has_direct_cluster = False
        clustering_method = "CIOH"
        coinjoin_detected = False
        coinjoin_protocol = "Standard CoinJoin"
        vasp_hops = []

        for a in tx_artifacts:
            payload = a.get("raw_payload", {})
            if payload.get("cluster_id"):
                has_direct_cluster = True
            if payload.get("clustering_method"):
                clustering_method = payload.get("clustering_method")
            if payload.get("coinjoin_detected"):
                coinjoin_detected = True
                coinjoin_protocol = payload.get("coinjoin_protocol", "Standard CoinJoin")
            if payload.get("hops_to_vasp"):
                vasp_hops.extend(payload.get("hops_to_vasp"))

        # Raw Score Evaluation
        if has_direct_cluster and clustering_method == "CIOH":
            raw_score = 0.90
            findings.append({
                "rule": "CIOH_CO_SPEND_CLUSTER",
                "evidence_strength": "HIGH",
                "observation": "CIOH identifies a heuristic association among inputs that may indicate common control; collaborative transactions can invalidate that assumption."
            })
        elif has_direct_cluster or len(vasp_hops) > 0:
            raw_score = 0.60
            findings.append({
                "rule": "MULTI_HOP_VASP_PATH",
                "evidence_strength": "MEDIUM",
                "observation": "Multi-hop transaction pathway traces to shared deposit cluster or intermediary VASP."
            })
        else:
            raw_score = 0.20
            findings.append({
                "rule": "UNLINKED_WALLET_OBSERVATION",
                "evidence_strength": "LOW",
                "observation": "Disparate wallet addresses observed on public ledger without confirmed co-spend or cluster."
            })

        # Deterministic CoinJoin Dampening
        if coinjoin_detected:
            # Deterministic channel dampening factor: (0.5 + 0.5 * R) * 0.60
            reliability_factor = round(base_rel_modifier * cls.COINJOIN_DAMPENING_FACTOR, 4)
            findings.append({
                "finding": "POTENTIAL_COINJOIN_DETECTED",
                "protocol": coinjoin_protocol,
                "dampening_multiplier": cls.COINJOIN_DAMPENING_FACTOR,
                "explanation": (
                    f"Collaborative transaction ({coinjoin_protocol}) detected. Applied deterministic "
                    f"{cls.COINJOIN_DAMPENING_FACTOR}x channel dampening to financial reliability modifier."
                )
            })
        else:
            reliability_factor = base_rel_modifier

        adjusted_score = round(raw_score * reliability_factor, 4)

        # Mathematical Invariant Guarantees
        assert 0.0 <= raw_score <= 1.0, f"Raw score out of bounds: {raw_score}"
        assert 0.0 <= clamped_r <= 1.0, f"Reliability out of bounds: {clamped_r}"
        assert 0.0 <= adjusted_score <= raw_score + 1e-4, f"Adjusted score exceeded raw: {adjusted_score} > {raw_score}"
        if not coinjoin_detected:
            assert (0.5 * raw_score) - 1e-4 <= adjusted_score <= raw_score + 1e-4

        return DimensionSignal(
            dimension=DimensionType.FINANCIAL,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            status=SignalStatus.VALID,
            evidence_ids=evidence_ids,
            engine_metadata={
                "engine": "FinancialEngine",
                "version": "1.0.0",
                "canonical_weight": cls.CANONICAL_WEIGHT,
                "clustering_method": clustering_method,
                "coinjoin_detected": coinjoin_detected
            },
            findings=findings
        )
