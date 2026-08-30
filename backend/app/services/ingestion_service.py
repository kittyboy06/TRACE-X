import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.models.schemas import (
    ProvenanceRecord,
    EvidenceType,
    SignalStatus
)
from app.models.database import EvidenceRecordModel, InvestigationModel


def compute_sha256(data: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of JSON serializable dictionary."""
    normalized_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


class IngestionService:
    @staticmethod
    def process_and_store_artifact(
        db: Session,
        investigation_id: str,
        artifact: Dict[str, Any]
    ) -> ProvenanceRecord:
        """
        Validates artifact, computes SHA-256, assigns provenance metadata,
        and saves it immutably to the database.
        """
        raw_payload = artifact.get("raw_payload", {})
        content_hash = compute_sha256(raw_payload)
        
        evidence_id = artifact.get("evidence_id") or f"EV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{content_hash[:6]}"
        collected_at_str = artifact.get("collected_at")
        collected_at = datetime.fromisoformat(collected_at_str.replace("Z", "+00:00")) if collected_at_str else datetime.utcnow()
        
        record = ProvenanceRecord(
            evidence_id=evidence_id,
            investigation_id=investigation_id,
            source_uri=artifact.get("source_uri", "unknown/source"),
            collected_at=collected_at,
            content_hash=content_hash,
            artifact_type=EvidenceType(artifact.get("artifact_type", "FORUM_POST")),
            raw_payload=raw_payload,
            extractor_version=artifact.get("extractor_version", "v1.4.0"),
            model_version=artifact.get("model_version", "sentence-transformers/all-mpnet-base-v2"),
            provenance_chain=["RAW_INGEST", "NORMALIZED"]
        )
        
        # Check if already exists in this investigation
        existing = db.query(EvidenceRecordModel).filter(
            EvidenceRecordModel.investigation_id == investigation_id,
            EvidenceRecordModel.content_hash == content_hash
        ).first()
        if not existing:
            db_model = EvidenceRecordModel(
                evidence_id=record.evidence_id,
                investigation_id=record.investigation_id,
                source_uri=record.source_uri,
                artifact_type=record.artifact_type.value,
                collected_at=record.collected_at,
                content_hash=record.content_hash,
                raw_payload=record.raw_payload,
                extractor_version=record.extractor_version,
                model_version=record.model_version,
                provenance_chain=record.provenance_chain
            )
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            
        return record

    @staticmethod
    def load_benchmark_package(db: Session, case_id: str) -> Tuple[InvestigationModel, List[ProvenanceRecord]]:
        """Loads pre-configured benchmark scenario from disk and ingests all artifacts."""
        file_path = f"app/data/benchmark_{case_id}.json"
        if not file_path.endswith(".json"):
            file_path += ".json"
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        inv_id = data["investigation_id"]
        inv = db.query(InvestigationModel).filter(InvestigationModel.id == inv_id).first()
        if not inv:
            inv = InvestigationModel(
                id=inv_id,
                title=data["title"],
                target_persona_a=data["target_persona_a"],
                target_persona_b=data["target_persona_b"],
                status="ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(inv)
            db.commit()
            db.refresh(inv)
            
        records = []
        for art in data.get("artifacts", []):
            rec = IngestionService.process_and_store_artifact(db, inv_id, art)
            records.append(rec)
            
        return inv, records
