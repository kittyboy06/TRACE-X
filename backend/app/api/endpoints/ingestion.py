from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import json
import zipfile
import io
import os

from app.models.database import get_db, InvestigationModel, EvidenceRecordModel
from app.models.schemas import EvidencePackageUpload, ProvenanceRecord, EvidenceType
from app.services.ingestion_service import IngestionService
from app.core.security import require_role, get_current_user

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
def load_benchmark(case_id: str, db: Session = Depends(get_db)):
    """
    1-Click Benchmark Loader for SIH26151 Presentation.
    Loads Case 1 (Convergence -> LIKELY_LINK) or Case 2 (Contradiction -> INCONCLUSIVE).
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
def get_investigation_artifacts(investigation_id: str, db: Session = Depends(get_db)):
    """
    Retrieves all ingested evidence records for a given investigation.
    """
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
    Enforces file size limits, safe archive extraction, and schema validation.
    """
    filename = file.filename or "evidence.json"
    contents = await file.read()
    
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum limit of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    package_data = None
    if filename.endswith(".json"):
        try:
            package_data = json.loads(contents.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(e)}")
    elif filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                entries = z.namelist()
                if len(entries) > MAX_ZIP_ENTRIES:
                    raise HTTPException(status_code=400, detail=f"ZIP archive contains too many files (max {MAX_ZIP_ENTRIES}).")
                
                total_uncompressed = sum(info.file_size for info in z.infolist())
                if total_uncompressed > MAX_UNCOMPRESSED_SIZE:
                    raise HTTPException(status_code=400, detail="ZIP archive exceeds uncompressed memory limit.")

                json_files = [f for f in entries if f.endswith(".json") and ".." not in f and not f.startswith("/")]
                if not json_files:
                    raise HTTPException(status_code=400, detail="No safe .json evidence package found in ZIP archive.")
                with z.open(json_files[0]) as jf:
                    package_data = json.loads(jf.read().decode("utf-8"))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract ZIP archive: {str(e)}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Please upload a .json evidence package or .zip archive."
        )

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
