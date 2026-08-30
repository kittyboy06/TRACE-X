from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import json
import os

from app.models.database import get_db, InvestigationModel
from app.models.schemas import EvidencePackageUpload, ProvenanceRecord
from app.services.ingestion_service import IngestionService

router = APIRouter()


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


@router.post("/upload")
async def upload_evidence_package(package: EvidencePackageUpload, db: Session = Depends(get_db)):
    """
    Upload custom JSON evidence package with automated SHA-256 provenance hashing.
    """
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
        "ingested_count": len(records),
        "records": records
    }
