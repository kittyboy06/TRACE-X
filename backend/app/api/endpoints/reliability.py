from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.database import get_db, SourceReliabilityModel, EvidenceRecordModel
from app.services.source_reliability_service import SourceReliabilityService, SourceTrustTier
from app.core.security import get_current_user, authorize_investigation_access

router = APIRouter()


class SourceReliabilityEvaluationRequest(BaseModel):
    investigation_id: str = Field(..., min_length=1, description="Investigation scope")
    source_uri: str = Field(..., min_length=1, description="URI of the evidence feed or source")
    reference_time: Optional[datetime] = Field(None, description="Optional reference time for deterministic freshness evaluation")


@router.post("/evaluate")
def evaluate_source_reliability(
    req: SourceReliabilityEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Evaluates evidence source reliability using Decision #10 4-factor scoring model.
    Guarded by investigation authorization to prevent cross-case data leakage.
    """
    authorize_investigation_access(req.investigation_id, current_user, db)

    assessment, trust_tier, diag = SourceReliabilityService.evaluate_source(
        db=db,
        investigation_id=req.investigation_id,
        source_uri=req.source_uri,
        reference_time=req.reference_time
    )

    persisted = SourceReliabilityService.persist_assessment(
        db=db,
        assessment=assessment,
        investigation_id=req.investigation_id,
        trust_tier=trust_tier,
        diagnostic_status=diag
    )

    return {
        "investigation_id": req.investigation_id,
        "source_uri": assessment.source_uri,
        "assessment": assessment.model_dump(mode="json"),
        "trust_tier": trust_tier.value,
        "diagnostic_status": diag,
        "record_id": persisted.id
    }


@router.get("/{investigation_id}/sources")
def get_investigation_sources_reliability(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves reliability evaluations for all sources within an investigation.
    Requires authentication and investigation-level authorization.
    """
    authorize_investigation_access(investigation_id, current_user, db)

    # Check existing evaluations
    records = (
        db.query(SourceReliabilityModel)
        .filter(SourceReliabilityModel.investigation_id == investigation_id)
        .all()
    )

    # If no cached evaluations exist, dynamically evaluate all unique sources from evidence
    if not records:
        unique_sources = (
            db.query(EvidenceRecordModel.source_uri)
            .filter(EvidenceRecordModel.investigation_id == investigation_id)
            .distinct()
            .all()
        )
        for (s_uri,) in unique_sources:
            assessment, trust_tier, diag = SourceReliabilityService.evaluate_source(
                db=db,
                investigation_id=investigation_id,
                source_uri=s_uri
            )
            persisted = SourceReliabilityService.persist_assessment(
                db=db,
                assessment=assessment,
                investigation_id=investigation_id,
                trust_tier=trust_tier,
                diagnostic_status=diag
            )
            records.append(persisted)

    return {
        "investigation_id": investigation_id,
        "count": len(records),
        "sources": [
            {
                "id": r.id,
                "source_uri": r.source_uri,
                "trust_tier": r.trust_tier,
                "reliability_score": r.reliability_score,
                "reliability_class": r.reliability_class,
                "factors": {
                    "reputation": r.reputation,
                    "freshness": r.freshness,
                    "corroboration": r.corroboration,
                    "consistency": r.consistency
                },
                "last_scan": r.last_scan.isoformat() if hasattr(r.last_scan, "isoformat") else str(r.last_scan),
                "scan_status": r.scan_status,
                "diagnostic_status": r.diagnostic_status
            }
            for r in records
        ]
    }
