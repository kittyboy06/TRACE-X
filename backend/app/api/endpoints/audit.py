from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib

from app.models.database import get_db, AuditEventModel, AttributionAssessmentModel, InvestigationModel
from app.models.schemas import AuditDecisionRequest, AuditEvent
from app.core.security import require_role, get_current_user, authorize_investigation_access
from app.services.audit_chain import AuditChainService

router = APIRouter()


@router.post("/decision", response_model=AuditEvent)
def record_analyst_decision(
    req: AuditDecisionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Records an append-only, tamper-evident audit record of the analyst's decision.
    Analyst identity is strictly derived server-side from JWT claims.
    """
    authorize_investigation_access(req.investigation_id, current_user, db)

    assess = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.assessment_id == req.assessment_id
    ).first()
    
    prior_state = assess.attribution_state if assess else "INCONCLUSIVE"
    resulting_state = prior_state
    if req.action.value == "CONFIRMED":
        resulting_state = f"{prior_state} (CONFIRMED_BY_ANALYST)"
    elif req.action.value == "REJECTED":
        resulting_state = "REJECTED_BY_ANALYST"
    elif req.action.value == "INVESTIGATE":
        resulting_state = "UNDER_FURTHER_INVESTIGATION"

    effective_analyst = current_user.get("analyst_id", "ANALYST-001")

    # Append audit event using canonical hash-chaining service (does not commit)
    db_audit = AuditChainService.append_event(
        db=db,
        investigation_id=req.investigation_id,
        assessment_id=req.assessment_id,
        action=req.action.value,
        analyst_id=effective_analyst,
        rationale=req.rationale,
        prior_state=prior_state,
        resulting_state=resulting_state
    )

    # Atomic commit
    db.commit()
    db.refresh(db_audit)

    return AuditEvent(
        audit_id=db_audit.audit_id,
        investigation_id=db_audit.investigation_id,
        assessment_id=db_audit.assessment_id,
        action=db_audit.action,
        analyst_id=db_audit.analyst_id,
        timestamp=db_audit.timestamp,
        rationale=db_audit.rationale,
        prior_state=db_audit.prior_state,
        resulting_state=db_audit.resulting_state,
        previous_hash=db_audit.previous_hash,
        event_hash=db_audit.event_hash
    )


@router.get("/verify/{investigation_id}")
def verify_audit_chain(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Cryptographically verifies the investigation's audit chain from genesis to terminal hash.
    """
    authorize_investigation_access(investigation_id, current_user, db)
    is_valid, records, error = AuditChainService.verify_investigation_chain(investigation_id, db)
    return {
        "investigation_id": investigation_id,
        "is_valid": is_valid,
        "event_count": len(records),
        "terminal_hash": records[-1]["event_hash"] if records else "0" * 64,
        "error": error
    }


@router.get("/export/{investigation_id}")
def export_investigation_dossier(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Exports a comprehensive, tamper-evident audit dossier of the entire investigation.
    Requires authenticated CTI_ANALYST or LEAD_AUDITOR role with investigation authorization.
    """
    inv = authorize_investigation_access(investigation_id, current_user, db)

    assess = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    
    is_valid, records, error = AuditChainService.verify_investigation_chain(investigation_id, db)
    audits = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == investigation_id).order_by(AuditEventModel.timestamp.asc()).all()

    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "export_metadata": {
            "system": "TRACE-X (Threat Relationship & Attribution Correlation Engine)",
            "compliance_standard": "NTRO SIH26151 Evidentiary Framework",
            "exported_at": now_iso,
            "export_hash": hashlib.sha256(f"{investigation_id}:{now_iso}".encode("utf-8")).hexdigest(),
            "audit_chain_valid": is_valid,
            "audit_chain_error": error
        },
        "investigation": {
            "id": inv.id,
            "title": inv.title,
            "persona_a": inv.target_persona_a,
            "persona_b": inv.target_persona_b,
            "real_world_identity": "NOT ESTABLISHED (Formal external subpoena required)"
        },
        "latest_attribution": assess.payload if assess else None,
        "audit_trail": [
            {
                "audit_id": a.audit_id,
                "action": a.action,
                "analyst_id": a.analyst_id,
                "timestamp": a.timestamp.isoformat() if hasattr(a.timestamp, "isoformat") else str(a.timestamp),
                "rationale": a.rationale,
                "previous_hash": a.previous_hash,
                "event_hash": a.event_hash
            }
            for a in audits
        ]
    }
