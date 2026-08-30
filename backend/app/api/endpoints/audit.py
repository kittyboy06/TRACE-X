from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import json

from app.models.database import get_db, AuditEventModel, AttributionAssessmentModel, InvestigationModel
from app.models.schemas import AuditDecisionRequest, AuditEvent, AttributionState

router = APIRouter()


@router.post("/decision", response_model=AuditEvent)
def record_analyst_decision(req: AuditDecisionRequest, db: Session = Depends(get_db)):
    """
    Records an append-only, tamper-evident audit record of the analyst's decision.
    """
    assess = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.assessment_id == req.assessment_id
    ).first()
    
    prior_state = assess.attribution_state if assess else "INCONCLUSIVE"
    resulting_state = prior_state
    if req.action.value == "CONFIRMED":
        resulting_state = prior_state
    elif req.action.value == "REJECTED":
        resulting_state = "REJECTED_BY_ANALYST"
    elif req.action.value == "INVESTIGATE":
        resulting_state = "UNDER_FURTHER_INVESTIGATION"

    audit_id = f"AUDIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{req.analyst_id[-4:]}"
    now = datetime.utcnow()
    
    # Compute immutable event hash
    hash_payload = {
        "audit_id": audit_id,
        "investigation_id": req.investigation_id,
        "assessment_id": req.assessment_id,
        "action": req.action.value,
        "analyst_id": req.analyst_id,
        "timestamp": now.isoformat(),
        "rationale": req.rationale,
        "prior_state": prior_state,
        "resulting_state": resulting_state
    }
    event_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

    db_audit = AuditEventModel(
        audit_id=audit_id,
        investigation_id=req.investigation_id,
        assessment_id=req.assessment_id,
        action=req.action.value,
        analyst_id=req.analyst_id,
        timestamp=now,
        rationale=req.rationale,
        prior_state=prior_state,
        resulting_state=resulting_state,
        event_hash=event_hash
    )
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)

    return AuditEvent(
        audit_id=audit_id,
        investigation_id=req.investigation_id,
        assessment_id=req.assessment_id,
        action=req.action,
        analyst_id=req.analyst_id,
        timestamp=now,
        rationale=req.rationale,
        prior_state=AttributionState(prior_state) if prior_state in AttributionState.__members__.values() else AttributionState.INCONCLUSIVE,
        resulting_state=AttributionState(resulting_state) if resulting_state in AttributionState.__members__.values() else AttributionState.INCONCLUSIVE,
        event_hash=event_hash
    )


@router.get("/export/{investigation_id}")
def export_investigation_dossier(investigation_id: str, db: Session = Depends(get_db)):
    """
    Exports a comprehensive, tamper-evident audit dossier of the entire investigation.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    assess = db.query(AttributionAssessmentModel).filter(AttributionAssessmentModel.investigation_id == investigation_id).first()
    audits = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == investigation_id).all()

    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return {
        "export_metadata": {
            "system": "TRACE-X (Threat Relationship & Attribution Correlation Engine)",
            "compliance_standard": "NTRO SIH26151 Evidentiary Framework",
            "exported_at": datetime.utcnow().isoformat(),
            "export_hash": hashlib.sha256(f"{investigation_id}:{datetime.utcnow().isoformat()}".encode("utf-8")).hexdigest()
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
                "timestamp": a.timestamp.isoformat(),
                "rationale": a.rationale,
                "event_hash": a.event_hash
            }
            for a in audits
        ]
    }
