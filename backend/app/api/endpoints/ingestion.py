from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import json
import zipfile
import io
import os

from app.models.database import get_db, InvestigationModel, EvidenceRecordModel, ExtractedEntityModel
from app.models.schemas import EvidencePackageUpload, ProvenanceRecord, EvidenceType
from app.services.ingestion_service import IngestionService
from app.services.collectors.manual_upload_collector import ManualUploadCollector
from app.core.security import require_role, get_current_user, authorize_investigation_access

router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_ENTRIES = 50
MAX_UNCOMPRESSED_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_EVIDENCE_TYPES = {e.value for e in EvidenceType}


def validate_artifacts_schema(artifacts: List[Dict[str, Any]]):
    if not isinstance(artifacts, list) or len(artifacts) == 0:
        raise HTTPException(status_code=400, detail="Evidence package must contain a non-empty 'artifacts' array.")
    for idx, art in enumerate(artifacts):
        if not isinstance(art, dict):
            raise HTTPException(status_code=400, detail=f"Artifact at index {idx} must be a JSON object.")
        art_type = art.get("artifact_type")
        if not art_type or art_type not in ALLOWED_EVIDENCE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Artifact at index {idx} has invalid artifact_type '{art_type}'. Allowed types: {sorted(list(ALLOWED_EVIDENCE_TYPES))}"
            )
        if "raw_payload" not in art or not isinstance(art["raw_payload"], dict):
            raise HTTPException(status_code=400, detail=f"Artifact at index {idx} must contain a valid 'raw_payload' object.")


@router.post("/benchmark/{case_id}")
def load_benchmark(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    1-Click Benchmark Loader for SIH26151 Presentation.
    Loads Case 1 (Convergence -> LIKELY_LINK) or Case 2 (Contradiction -> INCONCLUSIVE).
    Requires authenticated analyst/auditor session.
    """
    case_name = f"case_{case_id}" if not case_id.startswith("case_") else case_id
    try:
        inv, records = IngestionService.load_benchmark_package(db, case_name)
        return {
            "status": "SUCCESS",
            "message": f"Loaded benchmark {case_name} successfully",
            "investigation_id": inv.id,
            "title": inv.title,
            "persona_a": inv.target_persona_a,
            "persona_b": inv.target_persona_b,
            "artifact_count": len(records),
            "artifacts": records
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load benchmark {case_id}: {str(e)}")


@router.get("/{investigation_id}/artifacts")
def get_investigation_artifacts(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves all ingested evidence records for a given investigation.
    Requires authentication and investigation-level authorization.
    """
    from app.core.security import authorize_investigation_access
    authorize_investigation_access(investigation_id, current_user, db)

    records = db.query(EvidenceRecordModel).filter(EvidenceRecordModel.investigation_id == investigation_id).all()
    return {
        "investigation_id": investigation_id,
        "count": len(records),
        "artifacts": [
            {
                "evidence_id": r.evidence_id,
                "investigation_id": r.investigation_id,
                "source_uri": r.source_uri,
                "artifact_type": r.artifact_type,
                "collected_at": r.collected_at.isoformat() if hasattr(r.collected_at, "isoformat") else str(r.collected_at),
                "content_hash": r.content_hash,
                "raw_payload": r.raw_payload,
                "provenance_chain": r.provenance_chain
            }
            for r in records
        ]
    }


@router.post("/upload")
async def upload_evidence_package(
    package: EvidencePackageUpload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Upload custom JSON evidence package with automated SHA-256 provenance hashing.
    Protected by RBAC.
    """
    validate_artifacts_schema(package.artifacts)

    inv = db.query(InvestigationModel).filter(InvestigationModel.id == package.investigation_id).first()
    if not inv:
        inv = InvestigationModel(
            id=package.investigation_id,
            title=f"Investigation {package.investigation_id} ({package.target_persona_a} ↔ {package.target_persona_b})",
            target_persona_a=package.target_persona_a,
            target_persona_b=package.target_persona_b,
            status="ACTIVE"
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        
    records: List[ProvenanceRecord] = []
    for art in package.artifacts:
        rec = IngestionService.process_and_store_artifact(db, package.investigation_id, art)
        records.append(rec)
        
    return {
        "status": "SUCCESS",
        "investigation_id": package.investigation_id,
        "persona_a": package.target_persona_a,
        "persona_b": package.target_persona_b,
        "ingested_count": len(records),
        "uploaded_by": current_user.get("analyst_id", "ANALYST"),
        "records": records
    }


@router.post("/upload-file")
async def upload_evidence_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Accepts multipart/form-data upload of .json or .zip evidence packages.
    Enforces file size limits (10 MB), entry count (50 entries), uncompressed size (25 MB),
    safe directory traversal prevention, and schema validation.
    """
    filename = file.filename or "evidence.json"
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum limit of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    ext = "json" if filename.endswith(".json") else ("zip" if filename.endswith(".zip") else "")
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Please upload a .json evidence package or .zip archive."
        )

    try:
        collector = ManualUploadCollector()
        package_data = collector.collect({
            "format": ext,
            "content": contents,
            "filename": filename
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process evidence package: {str(e)}")

    if not package_data or not isinstance(package_data, dict):
        raise HTTPException(status_code=400, detail="Evidence package must be a valid JSON object.")

    investigation_id = package_data.get("investigation_id", f"INV-UPLOAD-{abs(hash(filename)) % 100000:05d}")
    persona_a = package_data.get("target_persona_a", "Persona_A")
    persona_b = package_data.get("target_persona_b", "Persona_B")
    artifacts = package_data.get("artifacts", [])

    validate_artifacts_schema(artifacts)

    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        inv = InvestigationModel(
            id=investigation_id,
            title=package_data.get("title", f"Investigation {investigation_id} ({persona_a} ↔ {persona_b})"),
            target_persona_a=persona_a,
            target_persona_b=persona_b,
            status="ACTIVE"
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)

    records: List[ProvenanceRecord] = []
    for art in artifacts:
        rec = IngestionService.process_and_store_artifact(db, investigation_id, art)
        records.append(rec)

    return {
        "status": "SUCCESS",
        "investigation_id": investigation_id,
        "persona_a": persona_a,
        "persona_b": persona_b,
        "ingested_count": len(records),
        "uploaded_by": current_user.get("analyst_id", "ANALYST"),
        "records": records
    }


@router.get("/{investigation_id}/entities")
def get_investigation_entities(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves all discrete extracted entities (technical/cryptographic/network indicators)
    associated with evidence in this investigation.
    Requires authentication and investigation-level authorization.
    """
    authorize_investigation_access(investigation_id, current_user, db)

    entities = db.query(ExtractedEntityModel).filter(ExtractedEntityModel.investigation_id == investigation_id).all()
    return {
        "investigation_id": investigation_id,
        "count": len(entities),
        "entities": [
            {
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "value": e.value,
                "evidence_id": e.evidence_id,
                "confidence": e.confidence
            }
            for e in entities
        ]
    }
