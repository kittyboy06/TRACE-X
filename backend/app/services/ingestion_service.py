import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.models.schemas import (
    ProvenanceRecord,
    EvidenceType,
    SignalStatus
)
from app.models.database import EvidenceRecordModel, InvestigationModel
from app.services.normalization_service import NormalizationService
from app.services.entity_extraction_service import EntityExtractionService
from app.services.collectors.benchmark_collector import BenchmarkCollector


def compute_sha256(data: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of JSON serializable dictionary."""
    normalized_json = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


class IngestionService:
    @staticmethod
    def process_and_store_artifact(
        db: Session,
        investigation_id: str,
        artifact: Dict[str, Any]
    ) -> ProvenanceRecord:
        """
        Normalizes raw artifact into immutable NormalizedArtifact contract,
        computes deterministic content_hash and evidence_id, enforces
        database deduplication on (investigation_id, content_hash), and extracts
        discrete technical indicators into ExtractedEntity models.
        """
        normalized_art = NormalizationService.normalize_artifact(artifact, investigation_id)
        db_model, is_new = NormalizationService.persist_normalized_artifact(
            db=db,
            artifact=normalized_art,
            extractor_version=artifact.get("extractor_version", "v2.0"),
            provenance_chain=artifact.get("provenance_chain") or ["RAW_INGEST", "NORMALIZED"]
        )

        # Extract and persist discrete technical indicators
        entities = EntityExtractionService.extract_entities(normalized_art)
        EntityExtractionService.persist_entities(db, entities, investigation_id)

        return ProvenanceRecord(
            evidence_id=normalized_art.evidence_id,
            investigation_id=normalized_art.investigation_id,
            source_uri=normalized_art.source_uri,
            collected_at=normalized_art.collected_at,
            content_hash=normalized_art.content_hash,
            artifact_type=EvidenceType(normalized_art.artifact_type.value),
            raw_payload=normalized_art.raw_payload,
            extractor_version=db_model.extractor_version,
            model_version=db_model.model_version,
            provenance_chain=db_model.provenance_chain
        )

    @staticmethod
    def load_benchmark_package(db: Session, case_id: str) -> Tuple[InvestigationModel, List[ProvenanceRecord]]:
        """
        Loads pre-configured benchmark scenario from disk via BenchmarkCollector,
        validates frozen Phase 0 SHA-256 ground truth anchors, and ingests all artifacts.
        """
        collector = BenchmarkCollector()
        benchmark_data = collector.collect({"case_id": case_id})

        inv_id = benchmark_data["investigation_id"]
        inv = db.query(InvestigationModel).filter(InvestigationModel.id == inv_id).first()
        if not inv:
            inv = InvestigationModel(
                id=inv_id,
                title=benchmark_data["title"],
                target_persona_a=benchmark_data["target_persona_a"],
                target_persona_b=benchmark_data["target_persona_b"],
                status="ACTIVE",
                created_at=datetime.now(timezone.utc)
            )
            db.add(inv)
            db.commit()
            db.refresh(inv)

        records = []
        for art in benchmark_data.get("artifacts", []):
            rec = IngestionService.process_and_store_artifact(db, inv_id, art)
            records.append(rec)

        return inv, records
