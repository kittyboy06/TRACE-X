import numpy as np
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import DimensionSignal, SignalStatus, StylometryEngineType
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global model cache to avoid re-loading on each request
_TRANSFORMER_MODEL = None
_MODEL_LOAD_FAILED = False


class StylometryEngine:
    MIN_WORD_COUNT = 150
    DEFAULT_MODEL_NAME = settings.STYLOMETRY_MODEL

    @classmethod
    def _get_transformer_model(cls):
        global _TRANSFORMER_MODEL, _MODEL_LOAD_FAILED
        if _TRANSFORMER_MODEL is not None:
            return _TRANSFORMER_MODEL
        if _MODEL_LOAD_FAILED:
            return None

        if not settings.ENABLE_REAL_TRANSFORMER:
            _MODEL_LOAD_FAILED = True
            return None

        try:
            from sentence_transformers import SentenceTransformer
            # Try loading cached local weights first
            try:
                _TRANSFORMER_MODEL = SentenceTransformer(cls.DEFAULT_MODEL_NAME, local_files_only=True)
            except Exception:
                _TRANSFORMER_MODEL = SentenceTransformer(cls.DEFAULT_MODEL_NAME)
            logger.info(f"Loaded SentenceTransformer: {cls.DEFAULT_MODEL_NAME}")
            return _TRANSFORMER_MODEL
        except Exception as e:
            logger.info(f"SentenceTransformer not cached locally ({str(e)}). Using deterministic statistical feature engine.")
            _MODEL_LOAD_FAILED = True
            return None

    @staticmethod
    def _compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @classmethod
    def _extract_pseudo_embedding(cls, text: str) -> np.ndarray:
        """
        Deterministic, offline statistical feature vectorizer (64 dimensions)
        capturing syntax, punctuation density, casing, and word-length distributions.
        Used as a truthful fallback when transformer weights are unavailable offline.
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
    def extract_embedding_and_similarity(cls, text_a: str, text_b: str) -> Tuple[float, str, Optional[str], int]:
        """
        Extracts author embedding using SentenceTransformer (if available)
        or deterministic statistical fallback. Returns (similarity, engine_name, model_name, embedding_dim).
        """
        model = cls._get_transformer_model()
        if model is not None:
            try:
                embeddings = model.encode([text_a, text_b], convert_to_numpy=True)
                sim = cls._compute_cosine_similarity(embeddings[0], embeddings[1])
                return round(sim, 4), StylometryEngineType.TRANSFORMER.value, cls.DEFAULT_MODEL_NAME, int(embeddings.shape[1])
            except Exception as e:
                logger.warning(f"Transformer inference error ({str(e)}). Using fallback.")

        # Deterministic Statistical Feature Engine Fallback
        vec_a = cls._extract_pseudo_embedding(text_a)
        vec_b = cls._extract_pseudo_embedding(text_b)
        sim = cls._compute_cosine_similarity(vec_a, vec_b)
        return round(sim, 4), StylometryEngineType.DETERMINISTIC_FALLBACK.value, None, 64

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
        
        # 1. Guardrail check (Minimum 150 words)
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
                    "words_persona_b": words_b,
                    "engine": StylometryEngineType.DETERMINISTIC_FALLBACK.value,
                    "model": None
                }
            )

        # 2. Compute similarity with explicit engine and model metadata
        raw_sim, engine_name, model_name, emb_dim = cls.extract_embedding_and_similarity(text_a, text_b)
        
        # 3. Channel reliability (e.g. check language consistency)
        lang_a = get_lang(persona_a_posts[0]) if persona_a_posts else "en"
        lang_b = get_lang(persona_b_posts[0]) if persona_b_posts else "en"
        
        reliability = 1.0
        details = {
            "cosine_similarity": raw_sim,
            "engine": engine_name,
            "model": model_name,
            "embedding_dimension": emb_dim,
            "words_persona_a": words_a,
            "words_persona_b": words_b,
            "language_persona_a": lang_a,
            "language_persona_b": lang_b,
            "token_count": words_a + words_b
        }

        if lang_a != lang_b:
            reliability = 0.50
            details["cross_language_penalty"] = "-50% (Cross-language syntax / translation variation)"

        adjusted_score = round(raw_sim * reliability, 4)
        contribution = round(weight * adjusted_score, 4)

        return DimensionSignal(
            dimension_name="stylometric",
            status=SignalStatus.VALID,
            raw_score=raw_sim,
            reliability_factor=reliability,
            adjusted_score=adjusted_score,
            configured_weight=weight,
            contribution=contribution,
            evidence_ids=[p.get("evidence_id", "") for p in persona_a_posts + persona_b_posts if "evidence_id" in p],
            supporting_details=details
        )
