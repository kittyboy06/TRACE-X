from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db, AttributionAssessmentModel, InvestigationModel
from app.models.schemas import SensitivityAdjustmentRequest, AttributionAssessment
from app.services.fusion_engine import EvidenceFusionEngine

router = APIRouter()


@router.get("/{investigation_id}")
def get_attribution_assessment(investigation_id: str, db: Session = Depends(get_db)):
    """
    Returns the latest fused attribution assessment for the investigation.
    """
    record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Attribution assessment not found for this investigation")
        
    return record.payload


@router.post("/recalculate")
def recalculate_sensitivity(req: SensitivityAdjustmentRequest, db: Session = Depends(get_db)):
    """
    Dynamic live recalculation for the Sensitivity & Contradiction Tuner in the UI.
    Normalizes new weights and re-runs the Two-Level Fusion Engine instantly.
    """
    record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == req.investigation_id
    ).first()
    
    if not record or not record.payload:
        raise HTTPException(status_code=404, detail="Original assessment not found to tune")
        
    old_payload = record.payload
    dims = old_payload.get("evidence_dimensions", {})

    # Re-normalize weights so sum = 1.0
    raw_sum = (
        req.weight_cryptographic +
        req.weight_financial +
        req.weight_stylometric +
        req.weight_infrastructure +
        req.weight_behavioral
    )
    if raw_sum <= 0:
        raw_sum = 1.0

    w_crypto = req.weight_cryptographic / raw_sum
    w_fin = req.weight_financial / raw_sum
    w_style = req.weight_stylometric / raw_sum
    w_infra = req.weight_infrastructure / raw_sum
    w_beh = req.weight_behavioral / raw_sum

    # Rebuild signals with new weights
    from app.models.schemas import DimensionSignal, GlobalContradiction
    
    crypto_sig = DimensionSignal(**dims["cryptographic"])
    crypto_sig.configured_weight = round(w_crypto, 4)
    crypto_sig.contribution = round(crypto_sig.configured_weight * crypto_sig.adjusted_score, 4)

    fin_sig = DimensionSignal(**dims["financial"])
    fin_sig.configured_weight = round(w_fin, 4)
    fin_sig.contribution = round(fin_sig.configured_weight * fin_sig.adjusted_score, 4)

    style_sig = DimensionSignal(**dims["stylometric"])
    style_sig.configured_weight = round(w_style, 4)
    style_sig.contribution = round(style_sig.configured_weight * style_sig.adjusted_score, 4)

    infra_sig = DimensionSignal(**dims["infrastructure"])
    infra_sig.configured_weight = round(w_infra, 4)
    infra_sig.contribution = round(infra_sig.configured_weight * infra_sig.adjusted_score, 4)

    beh_sig = DimensionSignal(**dims["behavioral_temporal"])
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

    return updated_assessment.model_dump()
