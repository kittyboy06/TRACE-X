import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.models.contracts import NormalizedArtifact, ArtifactType
from app.models.database import EvidenceRecordModel


class NormalizationService:
    """
    Normalizes heterogeneous evidentiary artifacts into immutable,
    canonicalized NormalizedArtifact contracts with deterministic SHA-256
    content hashing and database-enforced deduplication.
    """

    @classmethod
    def canonicalize_value(cls, val: Any) -> Any:
        """
        Recursively standardizes values:
        - Dictionaries: sorted keys, stripped string values
        - Lists: preserved order with canonicalized elements
        - Strings: whitespace trimmed
        - Datetime strings: normalized to standard UTC ISO-8601
        """
        if isinstance(val, dict):
            return {k: cls.canonicalize_value(v) for k, v in sorted(val.items())}
        elif isinstance(val, list):
            return [cls.canonicalize_value(item) for item in val]
        elif isinstance(val, str):
            trimmed = val.strip()
            # If string is an ISO timestamp, attempt standard UTC normalization
            if len(trimmed) >= 19 and ("T" in trimmed or " " in trimmed):
                try:
                    iso_candidate = trimmed.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(iso_candidate)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    return dt.isoformat()
                except Exception:
                    pass
            return trimmed
        elif isinstance(val, (datetime,)):
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            else:
                val = val.astimezone(timezone.utc)
            return val.isoformat()
        else:
            return val

    @classmethod
    def compute_canonical_json(cls, normalized_payload: Dict[str, Any]) -> str:
        """Produces compact, deterministic, UTF-8 JSON representation with sorted keys."""
        return json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def compute_content_hash(cls, normalized_payload: Dict[str, Any]) -> str:
        """Computes deterministic 64-hex SHA-256 hash over the canonical JSON."""
        canonical_str = cls.compute_canonical_json(normalized_payload)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def parse_collected_at(cls, val: Any) -> datetime:
        """Parses collected_at value into a timezone-aware UTC datetime object."""
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc)
        elif isinstance(val, str) and val.strip():
            iso_str = val.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    @classmethod
    def normalize_artifact(
        cls,
        raw_artifact: Dict[str, Any],
        investigation_id: str
    ) -> NormalizedArtifact:
        """
        Transforms raw artifact dictionary into an immutable NormalizedArtifact contract.
        - Preserves pristine raw_payload.
        - Produces canonicalized normalized_payload.
        - Computes deterministic content_hash.
        - Assigns deterministic evidence_id derived strictly from content_hash (unless explicitly provided).
        """
        raw_payload = raw_artifact.get("raw_payload", {})
        if not isinstance(raw_payload, dict):
            raise ValueError("Artifact 'raw_payload' must be a valid JSON dictionary.")

        # Canonicalize payload
        normalized_payload = cls.canonicalize_value(raw_payload)

        # Compute deterministic SHA-256
        content_hash = cls.compute_content_hash(normalized_payload)

        # Stable deterministic evidence_id (avoids timestamps!)
        evidence_id = raw_artifact.get("evidence_id") or f"EV-{content_hash[:16]}"

        raw_type = raw_artifact.get("artifact_type", "FORUM_POST")
        try:
            artifact_type = ArtifactType(raw_type)
        except ValueError:
            raise ValueError(
                f"Invalid artifact_type '{raw_type}'. Allowed types: {[e.value for e in ArtifactType]}"
            )

        source_uri = raw_artifact.get("source_uri") or "unknown://source"
        collected_at = cls.parse_collected_at(raw_artifact.get("collected_at"))

        return NormalizedArtifact(
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            artifact_type=artifact_type,
            source_uri=source_uri,
            collected_at=collected_at,
            content_hash=content_hash,
            raw_payload=raw_payload,
            normalized_payload=normalized_payload
        )

    @classmethod
    def persist_normalized_artifact(
        cls,
        db: Session,
        artifact: NormalizedArtifact,
        extractor_version: str = "v2.0",
        provenance_chain: Optional[List[str]] = None
    ) -> Tuple[EvidenceRecordModel, bool]:
        """
        Stores NormalizedArtifact in the database with strict deduplication on
        (investigation_id, content_hash).
        Returns (record, is_new).
        """
        existing = (
            db.query(EvidenceRecordModel)
            .filter(
                EvidenceRecordModel.investigation_id == artifact.investigation_id,
                EvidenceRecordModel.content_hash == artifact.content_hash
            )
            .first()
        )
        if existing:
            return existing, False

        prov = provenance_chain or [
            f"INGESTED_VIA_NORMALIZATION_SERVICE_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            f"SOURCE:{artifact.source_uri}",
            f"SHA256:{artifact.content_hash}"
        ]

        record = EvidenceRecordModel(
            evidence_id=artifact.evidence_id,
            investigation_id=artifact.investigation_id,
            source_uri=artifact.source_uri,
            artifact_type=artifact.artifact_type.value,
            collected_at=artifact.collected_at,
            content_hash=artifact.content_hash,
            raw_payload=artifact.raw_payload,
            normalized_payload=artifact.normalized_payload,
            extractor_version=extractor_version,
            provenance_chain=prov
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, True
