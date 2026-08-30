import numpy as np
from typing import List, Dict, Any, Optional
from app.models.schemas import DimensionSignal, SignalStatus


class StylometryEngine:
    MIN_WORD_COUNT = 150

    @staticmethod
    def _compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @staticmethod
    def _extract_pseudo_embedding(text: str) -> np.ndarray:
        """
        Fast, deterministic feature vectorizer for offline hackathon benchmarking
        (capturing syntax, punctuation density, length distributions, and key vocab frequencies).
        Can be upgraded with sentence-transformers / DarkBERT weights.
        """
        words = text.lower().split()
        if not words:
            return np.zeros(64)
            
        vector = np.zeros(64)
        for i, word in enumerate(words):
            idx = (hash(word) % 60) + 4
            vector[idx] += 1.0
            
        # Punctuation & syntactic signals
        vector[0] = text.count(".") / max(1, len(words))
        vector[1] = text.count(",") / max(1, len(words))
        vector[2] = sum(1 for c in text if c.isupper()) / max(1, len(text))
        vector[3] = len(words) / 100.0
        
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0 else vector

    @classmethod
    def analyze_personas(
        cls,
        persona_a_posts: List[Dict[str, Any]],
        persona_b_posts: List[Dict[str, Any]],
        weight: float = 0.20
    ) -> DimensionSignal:
        """
        Extracts stylometric signals, evaluates minimum-word guardrails,
        computes cosine similarity, and sets Level 1 channel reliability.
        """
        def get_text(p: Dict[str, Any]) -> str:
            return p.get("post_text") or p.get("raw_payload", {}).get("post_text", "")

        def get_lang(p: Dict[str, Any]) -> str:
            return p.get("language") or p.get("raw_payload", {}).get("language", "en")

        text_a = " ".join([get_text(p) for p in persona_a_posts])
        text_b = " ".join([get_text(p) for p in persona_b_posts])
        
        words_a = len(text_a.split())
        words_b = len(text_b.split())
        
        # 1. Guardrail check
        if words_a < cls.MIN_WORD_COUNT or words_b < cls.MIN_WORD_COUNT:
            return DimensionSignal(
                dimension_name="stylometric",
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                raw_score=0.0,
                reliability_factor=0.0,
                adjusted_score=0.0,
                configured_weight=weight,
                contribution=0.0,
                evidence_ids=[p.get("evidence_id", "") for p in persona_a_posts + persona_b_posts if "evidence_id" in p],
                supporting_details={
                    "status": "NOT_ENOUGH_EVIDENCE",
                    "reason": f"Insufficient corpus for statistical stylometry (A: {words_a} words, B: {words_b} words; min required: {cls.MIN_WORD_COUNT})",
                    "words_persona_a": words_a,
                    "words_persona_b": words_b
                }
            )

        # 2. Compute similarity
        vec_a = cls._extract_pseudo_embedding(text_a)
        vec_b = cls._extract_pseudo_embedding(text_b)
        raw_sim = cls._compute_cosine_similarity(vec_a, vec_b)
        
        # 3. Channel reliability (e.g. check language tags)
        lang_a = get_lang(persona_a_posts[0]) if persona_a_posts else "en"
        lang_b = get_lang(persona_b_posts[0]) if persona_b_posts else "en"
        
        reliability = 1.0
        details = {
            "cosine_similarity": round(raw_sim, 4),
            "words_persona_a": words_a,
            "words_persona_b": words_b,
            "language_persona_a": lang_a,
            "language_persona_b": lang_b,
            "token_count": words_a + words_b
        }
        
        if lang_a != lang_b:
            reliability = 0.50
            details["reliability_note"] = "Cross-language translation detected; stylometric confidence dampened by 50%."

        adjusted_score = round(raw_sim * reliability, 4)
        
        return DimensionSignal(
            dimension_name="stylometric",
            status=SignalStatus.VALID,
            raw_score=round(raw_sim, 4),
            reliability_factor=reliability,
            adjusted_score=adjusted_score,
            configured_weight=weight,
            contribution=round(weight * adjusted_score, 4),
            evidence_ids=[p.get("evidence_id", "") for p in persona_a_posts + persona_b_posts if "evidence_id" in p],
            supporting_details=details
        )
