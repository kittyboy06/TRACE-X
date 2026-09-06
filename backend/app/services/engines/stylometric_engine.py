import re
import zlib
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity
)
from app.core.config import settings
from app.services.source_reliability_service import SourceReliabilityService

logger = logging.getLogger(__name__)

# Global model cache to avoid re-loading on each request
_TRANSFORMER_MODEL = None
_MODEL_LOAD_FAILED = False


class StylometricEngine:
    """
    Canonical Stylometric Correlation Engine.
    Performs quantitative stylometry and author similarity analysis.

    LOCKED INVARIANTS:
    - Stylometric Guardrail: Both comparison corpora must contain at least 150 whitespace-delimited
      words and at least 500 tokens according to the configured tokenizer. Failure of either threshold
      returns NOT_ENOUGH_EVIDENCE; no similarity score is inferred.
    - Preferred Real Transformer: sentence-transformers/all-mpnet-base-v2 (768-dim).
    - Truthful Provenance: engine_metadata strictly records the actual engine utilized
      ('TRANSFORMER' or 'DETERMINISTIC_FALLBACK') and exact embedding dimension.
    """
    CANONICAL_WEIGHT = 0.20
    MIN_WORD_COUNT = 150
    MIN_TOKEN_COUNT = 500
    PREFERRED_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

    TOKENIZER_NAME = "char_3gram"

    @classmethod
    def _count_words(cls, text: str) -> int:
        """Counts whitespace-delimited words."""
        return len(text.strip().split())

    @classmethod
    def count_tokens(cls, text: str) -> int:
        """
        Counts tokens according to the configured stylometry tokenizer.
        In computational stylometry and authorship attribution, character tri-grams
        (char 3-grams) represent the canonical tokenization unit for capturing syntax,
        morphological sub-word patterns, and punctuation distributions.
        """
        clean = text.strip()
        if not clean:
            return 0
        return max(0, len(clean) - 2)

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
            import os
            model_name = settings.STYLOMETRY_MODEL or cls.PREFERRED_MODEL_NAME
            try:
                _TRANSFORMER_MODEL = SentenceTransformer(model_name, local_files_only=True)
                logger.info(f"Loaded SentenceTransformer from local cache: {model_name}")
                return _TRANSFORMER_MODEL
            except Exception:
                pass

            if os.getenv("ALLOW_ONLINE_MODEL_DOWNLOAD", "false").lower() in ("true", "1", "yes"):
                _TRANSFORMER_MODEL = SentenceTransformer(model_name)
                logger.info(f"Downloaded and loaded SentenceTransformer: {model_name}")
                return _TRANSFORMER_MODEL

            logger.info(f"Local weights for {model_name} not cached locally. Using truthful deterministic statistical fallback.")
            _MODEL_LOAD_FAILED = True
            return None
        except Exception as e:
            logger.info(f"Transformer model unavailable offline ({str(e)}). Using deterministic statistical fallback.")
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
            idx = (zlib.crc32(word.encode("utf-8")) % 60) + 4
            vector[idx] += 1.0

        # Punctuation & syntactic signals
        vector[0] = text.count(".") / max(1, len(words))
        vector[1] = text.count(",") / max(1, len(words))
        vector[2] = sum(1 for c in text if c.isupper()) / max(1, len(text))
        vector[3] = len(words) / 100.0

        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0 else vector

    @classmethod
    def extract_embedding_and_similarity(
        cls,
        text_a: str,
        text_b: str
    ) -> Tuple[float, str, Optional[str], int]:
        """
        Extracts author embedding and computes cosine similarity.
        Returns: (similarity, engine_name, model_name, embedding_dim).
        Truthfully reports fallback if transformer was not executed.
        """
        model = cls._get_transformer_model()
        if model is not None:
            try:
                embeddings = model.encode([text_a, text_b], convert_to_numpy=True)
                sim = cls._compute_cosine_similarity(embeddings[0], embeddings[1])
                return round(sim, 4), "TRANSFORMER", cls.PREFERRED_MODEL_NAME, int(embeddings.shape[1])
            except Exception as e:
                logger.warning(f"Transformer inference error ({str(e)}). Utilizing deterministic fallback.")

        # Deterministic Statistical Feature Engine Fallback
        vec_a = cls._extract_pseudo_embedding(text_a)
        vec_b = cls._extract_pseudo_embedding(text_b)
        sim = cls._compute_cosine_similarity(vec_a, vec_b)
        return round(sim, 4), "DETERMINISTIC_FALLBACK", None, 64

    @classmethod
    def analyze(
        cls,
        artifacts: List[Dict[str, Any]],
        entities: Optional[List[ExtractedEntity]] = None,
        reliability_context: float = 1.0,
        persona_a_posts: Optional[List[Dict[str, Any]]] = None,
        persona_b_posts: Optional[List[Dict[str, Any]]] = None
    ) -> DimensionSignal:
        post_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("FORUM_POST", "TEXT_SAMPLE", "COMMUNICATION")
        ]

        def get_text(p: Dict[str, Any]) -> str:
            return p.get("post_text") or p.get("raw_payload", {}).get("post_text", "")

        def get_lang(p: Dict[str, Any]) -> str:
            return p.get("language") or p.get("raw_payload", {}).get("language", "en")

        if persona_a_posts is None and persona_b_posts is None:
            # Auto-partition by persona if available
            personas = set()
            for p in post_artifacts:
                pers = p.get("raw_payload", {}).get("persona") or p.get("persona")
                if pers:
                    personas.add(pers)
            persona_list = sorted(list(personas))
            if len(persona_list) >= 2:
                persona_a_posts = [p for p in post_artifacts if (p.get("raw_payload", {}).get("persona") or p.get("persona")) == persona_list[0]]
                persona_b_posts = [p for p in post_artifacts if (p.get("raw_payload", {}).get("persona") or p.get("persona")) == persona_list[1]]
            else:
                persona_a_posts = post_artifacts[:len(post_artifacts)//2]
                persona_b_posts = post_artifacts[len(post_artifacts)//2:]

        persona_a_posts = persona_a_posts or []
        persona_b_posts = persona_b_posts or []

        evidence_ids = sorted(list(set([
            p.get("evidence_id") for p in (persona_a_posts + persona_b_posts) if p.get("evidence_id")
        ])))

        clamped_r = max(0.0, min(1.0, float(reliability_context)))
        base_rel_modifier = round(0.5 + 0.5 * clamped_r, 4)

        text_a = " ".join([get_text(p) for p in persona_a_posts]).strip()
        text_b = " ".join([get_text(p) for p in persona_b_posts]).strip()

        words_a = cls._count_words(text_a)
        words_b = cls._count_words(text_b)
        tokens_a = cls.count_tokens(text_a)
        tokens_b = cls.count_tokens(text_b)

        # -------------------------------------------------------------
        # LOCKED STYLOMETRIC GUARDRAIL:
        # Both comparison corpora must contain at least 150 whitespace-delimited
        # words AND at least 500 tokens according to the configured tokenizer.
        # Failure of either threshold returns NOT_ENOUGH_EVIDENCE;
        # no similarity score is inferred.
        # -------------------------------------------------------------
        eligible_a = (words_a >= cls.MIN_WORD_COUNT) and (tokens_a >= cls.MIN_TOKEN_COUNT)
        eligible_b = (words_b >= cls.MIN_WORD_COUNT) and (tokens_b >= cls.MIN_TOKEN_COUNT)

        if not (eligible_a and eligible_b):
            return DimensionSignal(
                dimension=DimensionType.STYLOMETRIC,
                raw_score=0.0,
                reliability_factor=base_rel_modifier,
                adjusted_score=0.0,
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                evidence_ids=evidence_ids,
                engine_metadata={
                    "engine": "StylometricEngine",
                    "version": "1.0.0",
                    "guardrail": "FAILED",
                    "reason": "Both comparison corpora must contain at least 150 whitespace-delimited words and at least 500 tokens according to the configured tokenizer. Failure of either threshold returns NOT_ENOUGH_EVIDENCE; no similarity score is inferred.",
                    "sample_metrics": {
                        "persona_a": {"words": words_a, "tokens": tokens_a, "min_words": cls.MIN_WORD_COUNT, "min_tokens": cls.MIN_TOKEN_COUNT},
                        "persona_b": {"words": words_b, "tokens": tokens_b, "min_words": cls.MIN_WORD_COUNT, "min_tokens": cls.MIN_TOKEN_COUNT}
                    }
                },
                findings=[{
                    "observation": "Corpus volume below mandatory 150-word and 500-token threshold; stylometric similarity inference suppressed."
                }]
            )

        # Corpus is eligible for inference
        similarity, engine_name, model_name, embedding_dim = cls.extract_embedding_and_similarity(text_a, text_b)
        raw_score = max(0.0, min(1.0, similarity))

        # Check for language translation variations
        lang_a = set(get_lang(p) for p in persona_a_posts)
        lang_b = set(get_lang(p) for p in persona_b_posts)
        translation_detected = False
        translation_dampening = 1.0

        if (lang_a and lang_b and lang_a != lang_b) or any(p.get("raw_payload", {}).get("translation_detected") for p in persona_a_posts + persona_b_posts):
            translation_detected = True
            translation_dampening = 0.80

        reliability_factor = round(base_rel_modifier * translation_dampening, 4)
        adjusted_score = round(raw_score * reliability_factor, 4)

        # Mathematical Invariants
        assert 0.0 <= raw_score <= 1.0, f"Raw score out of bounds: {raw_score}"
        assert 0.0 <= clamped_r <= 1.0, f"Reliability out of bounds: {clamped_r}"
        assert 0.0 <= adjusted_score <= raw_score + 1e-4, f"Adjusted score exceeded raw: {adjusted_score} > {raw_score}"
        if not translation_detected:
            assert (0.5 * raw_score) - 1e-4 <= adjusted_score <= raw_score + 1e-4

        findings = [{
            "rule": "STYLOMETRIC_SIMILARITY",
            "cosine_similarity": raw_score,
            "engine": engine_name,
            "corpus_metrics": {
                "persona_a": {"words": words_a, "tokens": tokens_a},
                "persona_b": {"words": words_b, "tokens": tokens_b}
            },
            "observation": f"Evaluated stylometric similarity across {words_a + words_b} words ({tokens_a + tokens_b} tokens) using {engine_name}."
        }]

        if translation_detected:
            findings.append({
                "finding": "TRANSLATION_VARIATION_DETECTED",
                "dampening_factor": translation_dampening,
                "observation": "Detected cross-lingual translation variations; applied 0.80x channel reliability dampening."
            })

        return DimensionSignal(
            dimension=DimensionType.STYLOMETRIC,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            status=SignalStatus.VALID,
            evidence_ids=evidence_ids,
            engine_metadata={
                "engine": engine_name,
                "model_name": model_name,
                "embedding_dimension": embedding_dim,
                "canonical_weight": cls.CANONICAL_WEIGHT,
                "words_persona_a": words_a,
                "tokens_persona_a": tokens_a,
                "words_persona_b": words_b,
                "tokens_persona_b": tokens_b,
                "translation_dampening_applied": translation_detected
            },
            findings=findings
        )
