from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import DimensionSignal, SignalStatus, StylometryEngineType
from app.services.engines.stylometric_engine import StylometricEngine


class StylometryEngine:
    """
    Compatibility facade re-exporting canonical StylometricEngine.
    """
    MIN_WORD_COUNT = StylometricEngine.MIN_WORD_COUNT
    MIN_TOKEN_COUNT = StylometricEngine.MIN_TOKEN_COUNT
    DEFAULT_MODEL_NAME = StylometricEngine.PREFERRED_MODEL_NAME

    @classmethod
    def extract_embedding_and_similarity(
        cls,
        text_a: str,
        text_b: str
    ) -> Tuple[float, str, Optional[str], int]:
        sim, eng, model, dim = StylometricEngine.extract_embedding_and_similarity(text_a, text_b)
        eng_type = StylometryEngineType.TRANSFORMER.value if eng == "TRANSFORMER" else StylometryEngineType.DETERMINISTIC_FALLBACK.value
        return sim, eng_type, model, dim

    @classmethod
    def analyze_personas(
        cls,
        persona_a_posts: List[Dict[str, Any]],
        persona_b_posts: List[Dict[str, Any]],
        weight: float = 0.20,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        contract_sig = StylometricEngine.analyze(
            artifacts=persona_a_posts + persona_b_posts,
            reliability_context=reliability_context,
            persona_a_posts=persona_a_posts,
            persona_b_posts=persona_b_posts
        )

        status_val = SignalStatus(contract_sig.status.value)
        meta = contract_sig.engine_metadata

        if contract_sig.status == SignalStatus.NOT_ENOUGH_EVIDENCE:
            return DimensionSignal(
                dimension_name="stylometric",
                status=status_val,
                raw_score=0.0,
                reliability_factor=0.0,
                adjusted_score=0.0,
                configured_weight=weight,
                contribution=0.0,
                evidence_ids=contract_sig.evidence_ids,
                supporting_details={
                    "status": "NOT_ENOUGH_EVIDENCE",
                    "reason": meta.get("reason", "Corpus volume below mandatory 150-word and 500-token threshold."),
                    "sample_metrics": meta.get("sample_metrics", {}),
                    "action_required": "Provide additional communication samples to satisfy the evidentiary threshold."
                }
            )

        translation_detected = meta.get("translation_dampening_applied", False)
        eng_name = meta.get("engine", "DETERMINISTIC_FALLBACK")
        eng_type = StylometryEngineType.TRANSFORMER.value if eng_name == "TRANSFORMER" else StylometryEngineType.DETERMINISTIC_FALLBACK.value

        return DimensionSignal(
            dimension_name="stylometric",
            status=status_val,
            raw_score=contract_sig.raw_score,
            reliability_factor=contract_sig.reliability_factor,
            adjusted_score=contract_sig.adjusted_score,
            configured_weight=weight,
            contribution=round(weight * contract_sig.adjusted_score, 4),
            evidence_ids=contract_sig.evidence_ids,
            supporting_details={
                "similarity_score": contract_sig.raw_score,
                "engine_type": eng_type,
                "model_name": meta.get("model_name"),
                "embedding_dimension": meta.get("embedding_dimension"),
                "persona_a_words": meta.get("words_persona_a"),
                "persona_a_tokens": meta.get("tokens_persona_a"),
                "persona_b_words": meta.get("words_persona_b"),
                "persona_b_tokens": meta.get("tokens_persona_b"),
                "translation_variation_detected": translation_detected,
                "reliability_modifier": contract_sig.reliability_factor,
                "interpretation": f"High lexical alignment ({contract_sig.raw_score}) across syntactic style vectors" if contract_sig.raw_score >= 0.75 else "Moderate to low stylometric similarity"
            }
        )
