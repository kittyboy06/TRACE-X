from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import json
import math
import hashlib

from app.models.database import get_db, AttributionAssessmentModel, AuditEventModel
from app.models.schemas import (
    AttributionAssessment,
    SensitivityAdjustmentRequest,
    DimensionSignal,
    GlobalContradiction
)
from app.services.fusion_engine import EvidenceFusionEngine
from app.core.security import require_role

router = APIRouter()


@router.get("/{investigation_id}")
def get_attribution_assessment(investigation_id: str, db: Session = Depends(get_db)):
    """
    Returns the latest official fused attribution assessment for the investigation (is_current=True).
    """
    record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Attribution assessment not found for this investigation")
        
    return record.payload


def calculate_sensitivity_preview(req: SensitivityAdjustmentRequest, db: Session) -> Dict[str, Any]:
    """
    Pure service calculation for sensitivity and contradiction weight adjustments.
    """
    weights = [
        req.weight_cryptographic,
        req.weight_financial,
        req.weight_stylometric,
        req.weight_infrastructure,
        req.weight_behavioral
    ]
    
    if any(math.isnan(w) or math.isinf(w) or w < 0 for w in weights):
        raise HTTPException(status_code=400, detail="Evidence weights must be non-negative, finite numbers.")
        
    raw_sum = sum(weights)
    if raw_sum <= 0.0:
        raise HTTPException(status_code=400, detail="At least one evidence dimension weight must be greater than zero.")

    record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == req.investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    
    if not record or not record.payload:
        raise HTTPException(status_code=404, detail="Original baseline assessment not found to tune")
        
    old_payload = record.payload
    dims = old_payload.get("evidence_dimensions", {})

    w_crypto = req.weight_cryptographic / raw_sum
    w_fin = req.weight_financial / raw_sum
    w_style = req.weight_stylometric / raw_sum
    w_infra = req.weight_infrastructure / raw_sum
    w_beh = req.weight_behavioral / raw_sum
    
    crypto_payload = dims.get("cryptographic")
    fin_payload = dims.get("financial")
    style_payload = dims.get("stylometric") or dims.get("stylometry")
    infra_payload = dims.get("infrastructure")
    beh_payload = dims.get("behavioral_temporal") or dims.get("behavioral")

    crypto_sig = DimensionSignal(**crypto_payload)
    crypto_sig.configured_weight = round(w_crypto, 4)
    crypto_sig.contribution = round(crypto_sig.configured_weight * crypto_sig.adjusted_score, 4)

    fin_sig = DimensionSignal(**fin_payload)
    fin_sig.configured_weight = round(w_fin, 4)
    fin_sig.contribution = round(fin_sig.configured_weight * fin_sig.adjusted_score, 4)

    style_sig = DimensionSignal(**style_payload)
    style_sig.configured_weight = round(w_style, 4)
    style_sig.contribution = round(style_sig.configured_weight * style_sig.adjusted_score, 4)

    infra_sig = DimensionSignal(**infra_payload)
    infra_sig.configured_weight = round(w_infra, 4)
    infra_sig.contribution = round(infra_sig.configured_weight * infra_sig.adjusted_score, 4)

    beh_sig = DimensionSignal(**beh_payload)
    beh_sig.configured_weight = round(w_beh, 4)
    beh_sig.contribution = round(beh_sig.configured_weight * beh_sig.adjusted_score, 4)

    global_contras = [GlobalContradiction(**c) for c in old_payload.get("global_contradictions", [])]

    # Re-run fusion
    updated_assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id=old_payload["assessment_id"],
        investigation_id=req.investigation_id,
        persona_a=old_payload["target_persona_a"],
        persona_b=old_payload["target_persona_b"],
        crypto_signal=crypto_sig,
        financial_signal=fin_sig,
        stylometry_signal=style_sig,
        infra_signal=infra_sig,
        behavioral_signal=beh_sig,
        global_contradictions=global_contras
    )

    return updated_assessment.model_dump(mode="json")


@router.post("/recalculate")
def recalculate_sensitivity(
    req: SensitivityAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Dynamic live recalculation for the Sensitivity & Contradiction Tuner in the UI.
    Returns an ephemeral preview without overwriting the official baseline assessment.
    Requires authenticated analyst session.
    """
    resp = calculate_sensitivity_preview(req, db)
    resp["is_preview"] = True
    resp["preview_notice"] = "Ephemeral sensitivity preview. Use /commit-weights to establish as official assessment."
    return resp


@router.post("/commit-weights")
def commit_tuned_weights(
    req: SensitivityAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Persists tuned weights as the official baseline assessment for an investigation with audit provenance.
    """
    record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == req.investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    
    if not record or not record.payload:
        raise HTTPException(status_code=404, detail="Original assessment not found to commit")

    preview = calculate_sensitivity_preview(req, db)

    # Deactivate older assessments
    db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == req.investigation_id
    ).update({"is_current": False})

    new_assessment_id = f"ASSESS-{req.investigation_id}-{datetime.utcnow().strftime('%H%M%S%f')}"
    preview["assessment_id"] = new_assessment_id
    analyst_id = current_user.get("analyst_id", "ANALYST-001")
    now = datetime.utcnow()

    db_assess = AttributionAssessmentModel(
        assessment_id=new_assessment_id,
        investigation_id=req.investigation_id,
        attribution_state=preview["attribution_state"],
        confidence_band=preview["confidence_band"],
        base_score=preview["base_score"],
        evidence_score=preview["evidence_score"],
        real_world_identity="NOT ESTABLISHED",
        is_current=True,
        payload=preview,
        created_at=now
    )
    db.add(db_assess)

    # Retrieve previous event hash for cryptographic hash chaining
    last_event = db.query(AuditEventModel).filter(
        AuditEventModel.investigation_id == req.investigation_id
    ).order_by(AuditEventModel.timestamp.desc()).first()
    previous_hash = last_event.event_hash if last_event else "GENESIS_ROOT_HASH_0000000000000000"

    audit_id = f"AUDIT-{now.strftime('%Y%m%d%H%M%S%f')}-{analyst_id[-4:]}"
    rationale = (
        f"Analyst calibrated dimension weights (Crypto: {req.weight_cryptographic}, "
        f"Fin: {req.weight_financial}, Style: {req.weight_stylometric}, "
        f"Infra: {req.weight_infrastructure}, Beh: {req.weight_behavioral})"
    )
    hash_payload = {
        "audit_id": audit_id,
        "investigation_id": req.investigation_id,
        "assessment_id": new_assessment_id,
        "action": "WEIGHTS_COMMITTED",
        "analyst_id": analyst_id,
        "timestamp": now.isoformat(),
        "rationale": rationale,
        "prior_state": record.attribution_state,
        "resulting_state": preview["attribution_state"],
        "previous_hash": previous_hash
    }
    event_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode("utf-8")).hexdigest()

    db_audit = AuditEventModel(
        audit_id=audit_id,
        investigation_id=req.investigation_id,
        assessment_id=new_assessment_id,
        action="WEIGHTS_COMMITTED",
        analyst_id=analyst_id,
        timestamp=now,
        rationale=rationale,
        prior_state=record.attribution_state,
        resulting_state=preview["attribution_state"],
        previous_hash=previous_hash,
        event_hash=event_hash
    )
    db.add(db_audit)
    db.commit()

    return {
        "status": "COMMITTED",
        "message": f"Tuned weights committed by {analyst_id}",
        "assessment": preview,
        "audit_event": {
            "audit_id": audit_id,
            "action": "WEIGHTS_COMMITTED",
            "previous_hash": previous_hash,
            "event_hash": event_hash
        }
    }
