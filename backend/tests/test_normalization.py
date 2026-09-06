import pytest
from datetime import datetime, timezone
from app.models.contracts import NormalizedArtifact, ArtifactType
from app.services.normalization_service import NormalizationService
from app.models.database import SessionLocal, EvidenceRecordModel


def test_canonical_json_key_permutation_invariance():
    """Verify that differently ordered dictionaries produce identical canonical JSON and SHA-256 hashes."""
    dict_a = {
        "zeta": 1,
        "alpha": "value",
        "nested": {
            "c": True,
            "b": None,
            "a": [3, 2, 1]
        }
    }
    dict_b = {
        "nested": {
            "a": [3, 2, 1],
            "c": True,
            "b": None
        },
        "alpha": "value",
        "zeta": 1
    }

    norm_a = NormalizationService.canonicalize_value(dict_a)
    norm_b = NormalizationService.canonicalize_value(dict_b)

    canon_a = NormalizationService.compute_canonical_json(norm_a)
    canon_b = NormalizationService.compute_canonical_json(norm_b)

    assert canon_a == canon_b
    assert " " not in canon_a.split(":")[0]  # Compact separators (no extra spaces)

    hash_a = NormalizationService.compute_content_hash(norm_a)
    hash_b = NormalizationService.compute_content_hash(norm_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64


def test_utc_timestamp_normalization_and_equivalence():
    """Verify that equivalent ISO timestamps across different timezone offsets normalize to identical UTC strings."""
    # 14:00 UTC == 19:30 IST (+05:30) == 09:00 EST (-05:00)
    iso_utc = "2026-03-01T14:00:00Z"
    iso_ist = "2026-03-01T19:30:00+05:30"
    iso_est = "2026-03-01T09:00:00-05:00"

    canon_utc = NormalizationService.canonicalize_value(iso_utc)
    canon_ist = NormalizationService.canonicalize_value(iso_ist)
    canon_est = NormalizationService.canonicalize_value(iso_est)

    assert canon_utc == canon_ist == canon_est == "2026-03-01T14:00:00+00:00"


def test_unicode_utf8_handling():
    """Verify deterministic normalization with Unicode characters, cyrillic, and symbols."""
    payload_unicode = {
        "forum": "Exploit.in (Форум)",
        "author": "Призрак",
        "symbol": "₿",
        "description": "Кибер-разведка threat intel"
    }
    norm = NormalizationService.canonicalize_value(payload_unicode)
    canon_json = NormalizationService.compute_canonical_json(norm)
    content_hash = NormalizationService.compute_content_hash(norm)

    assert "Призрак" in canon_json
    assert "₿" in canon_json
    assert len(content_hash) == 64


def test_deterministic_evidence_id_generation():
    """Verify evidence_id is derived deterministically from content_hash without timestamps."""
    artifact_payload_1 = {
        "raw_payload": {
            "user": "krypton",
            "score": 42
        },
        "artifact_type": "FORUM_POST"
    }
    artifact_payload_2 = {
        "raw_payload": {
            "score": 42,
            "user": "krypton"
        },
        "artifact_type": "FORUM_POST"
    }

    norm_1 = NormalizationService.normalize_artifact(artifact_payload_1, "INV-DETERMINISM-01")
    norm_2 = NormalizationService.normalize_artifact(artifact_payload_2, "INV-DETERMINISM-01")

    assert norm_1.content_hash == norm_2.content_hash
    assert norm_1.evidence_id == norm_2.evidence_id
    assert norm_1.evidence_id == f"EV-{norm_1.content_hash[:16]}"
    assert "-" not in norm_1.evidence_id[3:]  # No timestamp delimiters


def test_database_idempotent_deduplication():
    """Verify that repeated persistence of an identical payload is an idempotent no-op."""
    db = SessionLocal()
    inv_id = "INV-DEDUP-TEST-001"

    # Ensure clean state
    db.query(EvidenceRecordModel).filter(EvidenceRecordModel.investigation_id == inv_id).delete()
    db.commit()

    artifact_dict = {
        "artifact_type": "FORUM_POST",
        "source_uri": "darknet.onion/thread/1",
        "raw_payload": {"text": "Escrow payment verification.", "vendor": "Specter"}
    }

    norm_art = NormalizationService.normalize_artifact(artifact_dict, inv_id)

    # First ingestion
    rec1, is_new_1 = NormalizationService.persist_normalized_artifact(db, norm_art)
    assert is_new_1 is True
    assert rec1.content_hash == norm_art.content_hash

    # Second ingestion with identical content
    rec2, is_new_2 = NormalizationService.persist_normalized_artifact(db, norm_art)
    assert is_new_2 is False
    assert rec2.evidence_id == rec1.evidence_id
    assert rec2.content_hash == rec1.content_hash

    # Verify single database row
    count = db.query(EvidenceRecordModel).filter(
        EvidenceRecordModel.investigation_id == inv_id,
        EvidenceRecordModel.content_hash == norm_art.content_hash
    ).count()
    assert count == 1

    db.close()
