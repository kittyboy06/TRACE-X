from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models.database import get_db, InvestigationModel, EvidenceRecordModel, AttributionAssessmentModel
from app.services.graph_engine import GraphEngine

router = APIRouter()


@router.get("/{investigation_id}")
def get_cytoscape_graph(investigation_id: str, db: Session = Depends(get_db)):
    """
    Returns the Cytoscape.js compatible graph payload for the given investigation.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    records = db.query(EvidenceRecordModel).filter(EvidenceRecordModel.investigation_id == investigation_id).all()
    artifacts = [
        {
            "evidence_id": r.evidence_id,
            "artifact_type": r.artifact_type,
            "source_uri": r.source_uri,
            "raw_payload": r.raw_payload
        }
        for r in records
    ]

    assess_record = db.query(AttributionAssessmentModel).filter(AttributionAssessmentModel.investigation_id == investigation_id).first()
    state = assess_record.attribution_state if assess_record else "INCONCLUSIVE"
    
    # Check if hard gate triggered
    hard_gate = False
    if assess_record and assess_record.payload:
        hard_gate = assess_record.payload.get("assessment_rationale", {}).get("hard_cap_applied", False)

    graph_data = GraphEngine.generate_cytoscape_graph(
        investigation_id=investigation_id,
        persona_a=inv.target_persona_a,
        persona_b=inv.target_persona_b,
        artifacts=artifacts,
        attribution_state=state,
        hard_gate_triggered=hard_gate
    )

    return {
        "investigation_id": investigation_id,
        "persona_a": inv.target_persona_a,
        "persona_b": inv.target_persona_b,
        "attribution_state": state,
        "graph": graph_data
    }
