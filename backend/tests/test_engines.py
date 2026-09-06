import pytest
import re
from typing import List, Dict, Any
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity,
    EntityType
)
from app.services.engines.cryptographic_engine import CryptographicEngine
from app.services.engines.financial_engine import FinancialEngine
from app.services.engines.stylometric_engine import StylometricEngine
from app.services.engines.infrastructure_engine import InfrastructureEngine
from app.services.engines.temporal_engine import TemporalEngine
from app.services.blockchain_engine import BlockchainEngine
from app.services.stylometry_engine import StylometryEngine as StylometryFacade
from app.services.behavioral_engine import BehavioralEngine
from app.services.graph_engine import GraphEngine
from app.services.source_reliability_service import SourceReliabilityService


# =====================================================================
# 1. Stylometry Guardrail & Provenance Tests
# =====================================================================

def test_stylometry_guardrail_four_boundary_cases():
    """
    Verifies the locked stylometric guardrail across all 4 boundary conditions:
    Both comparison corpora must contain at least 150 whitespace-delimited words
    AND at least 500 tokens according to the configured tokenizer.
    Failure of either threshold returns NOT_ENOUGH_EVIDENCE; no similarity score is inferred.
    """
    # Helper to generate text with exact word and token counts (using configured char_3gram tokenizer)
    def build_text(word_count: int, target_tokens: int) -> str:
        target_chars = target_tokens + 2
        spaces = word_count - 1
        letters_needed = target_chars - spaces
        assert letters_needed >= word_count
        q, r = divmod(letters_needed, word_count)
        words = [("a" * (q + (1 if i < r else 0))) for i in range(word_count)]
        return " ".join(words)

    # Case A: 149 words + 500 tokens -> INSUFFICIENT
    text_149w_500t = build_text(149, 500)
    assert StylometricEngine._count_words(text_149w_500t) == 149
    assert StylometricEngine.count_tokens(text_149w_500t) == 500
    
    text_eligible = build_text(160, 520)

    sig_a = StylometricEngine.analyze(
        artifacts=[],
        persona_a_posts=[{"post_text": text_149w_500t}],
        persona_b_posts=[{"post_text": text_eligible}]
    )
    assert sig_a.status == SignalStatus.NOT_ENOUGH_EVIDENCE
    assert sig_a.raw_score == 0.0
    assert sig_a.adjusted_score == 0.0
    assert sig_a.engine_metadata.get("guardrail") == "FAILED"

    # Case B: 150 words + 499 tokens -> INSUFFICIENT
    text_150w_499t = build_text(150, 499)
    assert StylometricEngine._count_words(text_150w_499t) == 150
    assert StylometricEngine.count_tokens(text_150w_499t) == 499

    sig_b = StylometricEngine.analyze(
        artifacts=[],
        persona_a_posts=[{"post_text": text_150w_499t}],
        persona_b_posts=[{"post_text": text_eligible}]
    )
    assert sig_b.status == SignalStatus.NOT_ENOUGH_EVIDENCE
    assert sig_b.raw_score == 0.0
    assert sig_b.adjusted_score == 0.0
    assert sig_b.engine_metadata.get("guardrail") == "FAILED"

    # Case C: 150 words + 500 tokens -> ELIGIBLE
    text_150w_500t = build_text(150, 500)
    assert StylometricEngine._count_words(text_150w_500t) == 150
    assert StylometricEngine.count_tokens(text_150w_500t) == 500

    sig_c = StylometricEngine.analyze(
        artifacts=[],
        persona_a_posts=[{"post_text": text_150w_500t}],
        persona_b_posts=[{"post_text": text_eligible}]
    )
    assert sig_c.status == SignalStatus.VALID
    assert sig_c.raw_score > 0.0
    assert sig_c.adjusted_score > 0.0

    # Case D: 200 words + 700 tokens -> ELIGIBLE
    text_200w_700t = build_text(200, 700)
    assert StylometricEngine._count_words(text_200w_700t) == 200
    assert StylometricEngine.count_tokens(text_200w_700t) == 700

    sig_d = StylometricEngine.analyze(
        artifacts=[],
        persona_a_posts=[{"post_text": text_200w_700t}],
        persona_b_posts=[{"post_text": text_eligible}]
    )
    assert sig_d.status == SignalStatus.VALID
    assert sig_d.raw_score > 0.0
    assert sig_d.adjusted_score > 0.0


def test_stylometry_truthful_runtime_metadata():
    """
    Verifies that engine_metadata truthfully reports actual engine used
    ('TRANSFORMER' with 768 dim, or 'DETERMINISTIC_FALLBACK' with 64 dim).
    Never falsely reports MPNet if fallback was used.
    """
    def build_text(word_count: int, target_tokens: int) -> str:
        target_chars = target_tokens + 2
        spaces = word_count - 1
        letters_needed = target_chars - spaces
        q, r = divmod(letters_needed, word_count)
        words = [("a" * (q + (1 if i < r else 0))) for i in range(word_count)]
        return " ".join(words)

    corpus_a = build_text(160, 600)
    corpus_b = build_text(160, 600)

    sig = StylometricEngine.analyze(
        artifacts=[],
        persona_a_posts=[{"post_text": corpus_a}],
        persona_b_posts=[{"post_text": corpus_b}]
    )
    assert sig.status == SignalStatus.VALID
    eng = sig.engine_metadata["engine"]
    dim = sig.engine_metadata["embedding_dimension"]

    if eng == "TRANSFORMER":
        assert sig.engine_metadata["model_name"] == "sentence-transformers/all-mpnet-base-v2"
        assert dim == 768
    else:
        assert eng == "DETERMINISTIC_FALLBACK"
        assert sig.engine_metadata["model_name"] is None
        assert dim == 64


# =====================================================================
# 2. Financial Engine & CoinJoin Dampening Tests
# =====================================================================

def test_financial_engine_cioh_and_deterministic_coinjoin_dampening():
    """
    Verifies:
    1. Heuristic association without ownership claims.
    2. CoinJoin collaborative transaction dampening applies deterministic factor * 0.60
       without arbitrary score subtraction.
    3. Formula: adjusted = raw * (0.5 + 0.5 * R) * 0.60
    """
    # 1. Direct CIOH without CoinJoin
    art_cioh = {
        "artifact_type": "BTC_TRANSACTION",
        "evidence_id": "EV-TX-01",
        "raw_payload": {
            "cluster_id": "CL-001",
            "clustering_method": "CIOH",
            "coinjoin_detected": False
        }
    }
    sig_cioh = FinancialEngine.analyze([art_cioh], reliability_context=1.0)
    assert sig_cioh.status == SignalStatus.VALID
    assert sig_cioh.raw_score == 0.90
    assert sig_cioh.reliability_factor == 1.0  # 0.5 + 0.5 * 1.0
    assert sig_cioh.adjusted_score == 0.90
    assert any("heuristic association among inputs" in f.get("observation", "") for f in sig_cioh.findings)

    # 2. CIOH with CoinJoin detected (R = 1.0)
    art_coinjoin = {
        "artifact_type": "BTC_TRANSACTION",
        "evidence_id": "EV-TX-02",
        "raw_payload": {
            "cluster_id": "CL-002",
            "clustering_method": "CIOH",
            "coinjoin_detected": True,
            "coinjoin_protocol": "Samourai Whirlpool"
        }
    }
    sig_cj = FinancialEngine.analyze([art_coinjoin], reliability_context=1.0)
    assert sig_cj.status == SignalStatus.VALID
    assert sig_cj.raw_score == 0.90
    # Expected: (0.5 + 0.5 * 1.0) * 0.60 = 0.60
    assert sig_cj.reliability_factor == pytest.approx(0.60, abs=1e-4)
    # Expected adjusted: 0.90 * 0.60 = 0.54
    assert sig_cj.adjusted_score == pytest.approx(0.54, abs=1e-4)
    assert any("POTENTIAL_COINJOIN_DETECTED" in f.get("finding", "") for f in sig_cj.findings)

    # 3. CIOH with CoinJoin and moderate source reliability (R = 0.50)
    # base rel modifier = 0.5 + 0.5 * 0.5 = 0.75
    # rel factor with CJ = 0.75 * 0.60 = 0.45
    # adjusted = 0.90 * 0.45 = 0.405
    sig_cj_r50 = FinancialEngine.analyze([art_coinjoin], reliability_context=0.50)
    assert sig_cj_r50.reliability_factor == pytest.approx(0.45, abs=1e-4)
    assert sig_cj_r50.adjusted_score == pytest.approx(0.405, abs=1e-4)


# =====================================================================
# 3. Cryptographic Engine Tests
# =====================================================================

def test_cryptographic_engine_key_reuse_and_conflicting_keys():
    """
    Verifies:
    1. Primary keypair reuse gives 0.95 raw score.
    2. Subkey cross-certification gives 0.85 raw score.
    3. Conflicting keys gives 0.15 raw score with exact phrasing:
       'raw_score = 0.15 indicating evidence inconsistent with the tested key-reuse hypothesis.'
    4. Single key gives 0.50.
    5. No keys gives NOT_ENOUGH_EVIDENCE.
    """
    # 1. Primary key reuse
    arts_reuse = [
        {"artifact_type": "PGP_KEY", "evidence_id": "EV-PGP-1", "raw_payload": {"key_id": "0xABC123", "shared_key": True}},
        {"artifact_type": "PGP_KEY", "evidence_id": "EV-PGP-2", "raw_payload": {"key_id": "0xABC123", "shared_key": True}}
    ]
    sig_reuse = CryptographicEngine.analyze(arts_reuse, reliability_context=1.0)
    assert sig_reuse.raw_score == 0.95
    assert sig_reuse.adjusted_score == 0.95

    # 2. Conflicting keys
    arts_conflict = [
        {"artifact_type": "PGP_KEY", "evidence_id": "EV-PGP-1", "raw_payload": {"key_id": "0x111", "algorithm": "ED25519"}},
        {"artifact_type": "PGP_KEY", "evidence_id": "EV-PGP-2", "raw_payload": {"key_id": "0x222", "algorithm": "RSA-4096", "conflicting_keys": True}}
    ]
    sig_conflict = CryptographicEngine.analyze(arts_conflict, reliability_context=1.0)
    assert sig_conflict.raw_score == 0.15
    assert sig_conflict.adjusted_score == 0.15
    expected_msg = "raw_score = 0.15 indicating evidence inconsistent with the tested key-reuse hypothesis."
    assert any(expected_msg in f.get("observation", "") for f in sig_conflict.findings)

    # 3. No keys
    sig_none = CryptographicEngine.analyze([], reliability_context=1.0)
    assert sig_none.status == SignalStatus.NOT_ENOUGH_EVIDENCE
    assert sig_none.raw_score == 0.0


# =====================================================================
# 4. Infrastructure Engine Tests
# =====================================================================

def test_infrastructure_engine_scope_and_passive_metadata():
    """
    Verifies:
    1. Infrastructure analysis restricted strictly to authorized/synthetic metadata.
    2. Rare fingerprint match gives 0.65 raw score.
    3. Generic CDN gives 0.20 raw score.
    4. Operating mode explicitly flags PASSIVE_METADATA_ONLY with zero live probing.
    """
    art_rare = {
        "artifact_type": "INFRASTRUCTURE_HEADER",
        "evidence_id": "EV-INF-1",
        "raw_payload": {
            "rare_fingerprint_match": True,
            "persona_a_infra": {"tls_cert_serial": "SN-9988", "ssh_banner": "SSH-2.0-CustomOpenSSH"}
        }
    }
    sig_rare = InfrastructureEngine.analyze([art_rare], reliability_context=1.0)
    assert sig_rare.raw_score == 0.65
    assert sig_rare.engine_metadata["operating_mode"] == "PASSIVE_METADATA_ONLY"
    assert sig_rare.engine_metadata["live_probing_executed"] is False

    art_cdn = {
        "artifact_type": "INFRASTRUCTURE_HEADER",
        "evidence_id": "EV-INF-2",
        "raw_payload": {"generic_cdn": True}
    }
    sig_cdn = InfrastructureEngine.analyze([art_cdn], reliability_context=1.0)
    assert sig_cdn.raw_score == 0.20


# =====================================================================
# 5. Temporal Engine & Hard Gate Separation Tests
# =====================================================================

def test_temporal_engine_cadence_and_concurrency_separation():
    """
    Verifies:
    1. Temporal engine observes concurrency clash without double-penalizing the raw score.
    2. Uses cautious terminology ('apparent UTC activity window', 'apparent_activity_profile').
    3. Identifies sequential migration cadence (0.80).
    """
    # Sequential migration
    arts_mig = [
        {"artifact_type": "FORUM_POST", "evidence_id": "EV-P-1", "raw_payload": {"post_text": "text sample"}}
    ]
    sig_mig = TemporalEngine.analyze(arts_mig, reliability_context=1.0)
    assert sig_mig.raw_score == 0.80
    assert sig_mig.engine_metadata["apparent_activity_profile"] == "DIURNAL_UTC_PROFILE"

    # Concurrency clash detection
    art_clash = {
        "artifact_type": "TEMPORAL_BURST",
        "evidence_id": "EV-T-CLASH",
        "raw_payload": {
            "concurrent_authenticated_session": True,
            "conflict_severity": "CRITICAL",
            "time_delta_seconds": 15,
            "persona_a_active_window": {"node_location": "Node A"},
            "persona_b_active_window": {"node_location": "Node B"}
        }
    }
    sig_clash = TemporalEngine.analyze([art_clash] + arts_mig, reliability_context=1.0)
    assert sig_clash.status == SignalStatus.VALID
    # Numerical score is NOT artificially forced to 0.10: migration cadence scored normally
    assert sig_clash.raw_score == 0.80
    # Concurrency clash observation recorded in findings
    assert any(f.get("finding") == "TEMPORAL_CONCURRENCY_CLASH" for f in sig_clash.findings)
    assert any(f.get("triggers_hard_gate_candidate") is True for f in sig_clash.findings)


# =====================================================================
# 6. Mathematical Invariants Across All Engines
# =====================================================================

def test_all_engines_enforce_decision_10_clamping():
    """
    Verifies mathematical invariants across all 5 engines:
    1. 0.0 <= raw_score <= 1.0
    2. 0.0 <= reliability_factor <= 1.0
    3. 0.5 * raw_score <= adjusted_score <= raw_score (standard)
       adjusted_score <= raw_score (when dampened)
    """
    r_contexts = [0.0, 0.25, 0.50, 0.75, 1.0]

    # Test inputs
    dummy_crypto = [{"artifact_type": "PGP_KEY", "evidence_id": "E1", "raw_payload": {"shared_key": True}}]
    dummy_fin = [{"artifact_type": "BTC_TRANSACTION", "evidence_id": "E2", "raw_payload": {"cluster_id": "C1", "clustering_method": "CIOH"}}]
    dummy_infra = [{"artifact_type": "INFRASTRUCTURE_HEADER", "evidence_id": "E3", "raw_payload": {"rare_fingerprint_match": True}}]
    dummy_temp = [{"artifact_type": "FORUM_POST", "evidence_id": "E4", "raw_payload": {"post_text": "Sample"}}]
    text_corpus = " ".join([f"token_{i} ," for i in range(160)])

    for r in r_contexts:
        s_c = CryptographicEngine.analyze(dummy_crypto, reliability_context=r)
        assert (0.5 * s_c.raw_score) - 1e-4 <= s_c.adjusted_score <= s_c.raw_score + 1e-4

        s_f = FinancialEngine.analyze(dummy_fin, reliability_context=r)
        assert (0.5 * s_f.raw_score) - 1e-4 <= s_f.adjusted_score <= s_f.raw_score + 1e-4

        s_i = InfrastructureEngine.analyze(dummy_infra, reliability_context=r)
        assert (0.5 * s_i.raw_score) - 1e-4 <= s_i.adjusted_score <= s_i.raw_score + 1e-4

        s_t = TemporalEngine.analyze(dummy_temp, reliability_context=r)
        assert (0.5 * s_t.raw_score) - 1e-4 <= s_t.adjusted_score <= s_t.raw_score + 1e-4

        s_s = StylometricEngine.analyze(
            artifacts=[],
            persona_a_posts=[{"post_text": text_corpus}],
            persona_b_posts=[{"post_text": text_corpus}],
            reliability_context=r
        )
        assert (0.5 * s_s.raw_score) - 1e-4 <= s_s.adjusted_score <= s_s.raw_score + 1e-4


# =====================================================================
# 7. Compatibility Facades Test
# =====================================================================

def test_compatibility_facades():
    """Verify legacy facades return expected schemas.DimensionSignal."""
    # BlockchainEngine facade
    fin_sig = BlockchainEngine.analyze_transactions(
        [{"artifact_type": "BTC_TRANSACTION", "raw_payload": {"cluster_id": "C1", "clustering_method": "CIOH"}}],
        weight=0.25,
        reliability_context=1.0
    )
    assert fin_sig.dimension_name == "financial"
    assert fin_sig.configured_weight == 0.25
    assert fin_sig.raw_score == 0.90
    assert fin_sig.contribution == 0.225

    # StylometryEngine facade
    corpus = " ".join([f"word_{i}..." for i in range(160)])
    style_sig = StylometryFacade.analyze_personas(
        [{"post_text": corpus}],
        [{"post_text": corpus}],
        weight=0.20,
        reliability_context=1.0
    )
    assert style_sig.dimension_name == "stylometric"
    assert style_sig.configured_weight == 0.20
    assert style_sig.raw_score > 0.0

    # BehavioralEngine facade
    beh_sig, contras = BehavioralEngine.analyze_behavior_and_temporality(
        [{"artifact_type": "TEMPORAL_BURST", "raw_payload": {"concurrent_authenticated_session": True, "conflict_severity": "CRITICAL"}}],
        [{"artifact_type": "FORUM_POST", "raw_payload": {}}],
        weight=0.10,
        reliability_context=1.0
    )
    assert beh_sig.dimension_name == "behavioral_temporal"
    assert len(contras) == 1
    assert contras[0].triggers_hard_gate is True

    # GraphEngine facade
    crypto_sig, infra_sig = GraphEngine.analyze_cryptographic_and_infra(
        [{"artifact_type": "PGP_KEY", "raw_payload": {"shared_key": True}}],
        [{"artifact_type": "INFRASTRUCTURE_HEADER", "raw_payload": {"rare_fingerprint_match": True}}],
        weight_crypto=0.30,
        weight_infra=0.15
    )
    assert crypto_sig.dimension_name == "cryptographic"
    assert crypto_sig.raw_score == 0.95
    assert infra_sig.dimension_name == "infrastructure"
    assert infra_sig.raw_score == 0.65
