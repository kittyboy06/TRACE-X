from typing import List, Dict, Any, Optional
from app.models.schemas import DimensionSignal, SignalStatus
from app.services.engines.financial_engine import FinancialEngine


class BlockchainEngine:
    """
    Compatibility facade re-exporting canonical FinancialEngine.
    """
    @classmethod
    def analyze_transactions(
        cls,
        tx_artifacts: List[Dict[str, Any]],
        weight: float = 0.25,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        contract_sig = FinancialEngine.analyze(
            artifacts=tx_artifacts,
            reliability_context=reliability_context
        )

        primary_tx = tx_artifacts[0] if tx_artifacts else {}
        raw_payload = primary_tx.get("raw_payload", {})
        vasp_hops = raw_payload.get("hops_to_vasp", [])
        vasp_targets = [h.get("vasp_entity") for h in vasp_hops if h.get("vasp_entity")]
        coinjoin_detected = raw_payload.get("coinjoin_detected", False)
        protocol = raw_payload.get("coinjoin_protocol", "Standard CoinJoin")

        status_val = SignalStatus(contract_sig.status.value)

        return DimensionSignal(
            dimension_name="financial",
            status=status_val,
            raw_score=contract_sig.raw_score,
            reliability_factor=contract_sig.reliability_factor,
            adjusted_score=contract_sig.adjusted_score,
            configured_weight=weight,
            contribution=round(weight * contract_sig.adjusted_score, 4),
            evidence_ids=contract_sig.evidence_ids,
            supporting_details={
                "cluster_id": raw_payload.get("cluster_id", "UNCLUSTERED"),
                "clustering_method": contract_sig.engine_metadata.get("clustering_method", "CIOH"),
                "coinjoin_detected": coinjoin_detected,
                "coinjoin_protocol": protocol if coinjoin_detected else None,
                "reliability_adjustment": f"-{int(round((1.0 - contract_sig.reliability_factor) * 100))}%" if coinjoin_detected else "None",
                "hops_to_vasp": vasp_hops,
                "identified_vasps": vasp_targets,
                "nearest_vasp": vasp_targets[0] if vasp_targets else "None Detected",
                "findings": contract_sig.findings
            }
        )
