from typing import List, Dict, Any, Optional
from app.models.schemas import DimensionSignal, SignalStatus


class BlockchainEngine:
    @classmethod
    def analyze_transactions(
        cls,
        tx_artifacts: List[Dict[str, Any]],
        weight: float = 0.25
    ) -> DimensionSignal:
        """
        Analyzes UTXO transactions, clusters addresses using CIOH,
        checks for CoinJoin mixing anomalies, and extracts VASP hops.
        """
        if not tx_artifacts:
            return DimensionSignal(
                dimension_name="financial",
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                raw_score=0.0,
                reliability_factor=1.0,
                adjusted_score=0.0,
                configured_weight=weight,
                contribution=0.0,
                evidence_ids=[],
                supporting_details={"message": "No cryptocurrency transactions found in evidence package"}
            )
            
        primary_tx = tx_artifacts[0]
        raw_payload = primary_tx.get("raw_payload", {})
        
        # Check clustering link
        has_direct_cluster = bool(raw_payload.get("cluster_id"))
        clustering_method = raw_payload.get("clustering_method", "CIOH")
        
        # Base financial score
        if has_direct_cluster and clustering_method == "CIOH":
            raw_score = 0.90
        elif has_direct_cluster:
            raw_score = 0.60
        else:
            raw_score = 0.20
            
        # Check CoinJoin mixing pattern (Level 1 reliability adjustment)
        coinjoin_detected = raw_payload.get("coinjoin_detected", False)
        coinjoin_penalty = raw_payload.get("coinjoin_penalty", 0.0)
        protocol = raw_payload.get("coinjoin_protocol", "Standard CoinJoin")
        
        reliability_factor = 1.0
        if coinjoin_detected:
            # Dampen financial reliability due to collaborative transaction ambiguity
            penalty = coinjoin_penalty if coinjoin_penalty > 0 else 0.40
            reliability_factor = round(1.0 - penalty, 2)
            
        adjusted_score = round(raw_score * reliability_factor, 4)
        
        vasp_hops = raw_payload.get("hops_to_vasp", [])
        vasp_targets = [h.get("vasp_entity") for h in vasp_hops if h.get("vasp_entity")]
        
        return DimensionSignal(
            dimension_name="financial",
            status=SignalStatus.VALID,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            configured_weight=weight,
            contribution=round(weight * adjusted_score, 4),
            evidence_ids=[tx.get("evidence_id", "") for tx in tx_artifacts if "evidence_id" in tx],
            supporting_details={
                "cluster_id": raw_payload.get("cluster_id", "UNCLUSTERED"),
                "clustering_method": clustering_method,
                "coinjoin_detected": coinjoin_detected,
                "coinjoin_protocol": protocol if coinjoin_detected else None,
                "reliability_adjustment": f"-{int((1-reliability_factor)*100)}%" if coinjoin_detected else "None",
                "hops_to_vasp": vasp_hops,
                "identified_vasps": vasp_targets,
                "nearest_vasp": vasp_targets[0] if vasp_targets else "None Detected"
            }
        )
