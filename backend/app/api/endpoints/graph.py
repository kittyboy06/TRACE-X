from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models.database import get_db, InvestigationModel, EvidenceRecordModel, AttributionAssessmentModel
from app.services.graph_engine import GraphEngine
from app.core.security import get_current_user, authorize_investigation_access

router = APIRouter()


@router.get("/{investigation_id}")
def get_cytoscape_graph(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns the Cytoscape.js compatible graph payload for the given investigation.
    Requires authentication and investigation-level authorization.
    In production mode, fails closed with HTTP 503 if Neo4j is unavailable.
    """
    inv = authorize_investigation_access(investigation_id, current_user, db)

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

    assess_record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    state = assess_record.attribution_state if assess_record else "INCONCLUSIVE"

    # Check if hard gate triggered
    hard_gate = False
    actual_assessment_id = f"ASSESS-{investigation_id}"
    if assess_record and assess_record.payload:
        actual_assessment_id = assess_record.assessment_id
        hard_gate = (
            assess_record.payload.get("hard_gate_applied")
            or assess_record.payload.get("assessment_rationale", {}).get("hard_gate_applied", False)
            or assess_record.payload.get("assessment_rationale", {}).get("hard_cap_applied", False)
        )

    graph_data = GraphEngine.generate_cytoscape_graph(
        investigation_id=investigation_id,
        persona_a=inv.target_persona_a,
        persona_b=inv.target_persona_b,
        artifacts=artifacts,
        attribution_state=state,
        hard_gate_triggered=hard_gate,
        assessment_id=actual_assessment_id,
        evidence_ids=[r.evidence_id for r in records]
    )

    return {
        "investigation_id": investigation_id,
        "persona_a": inv.target_persona_a,
        "persona_b": inv.target_persona_b,
        "attribution_state": state,
        "assessment_id": actual_assessment_id,
        "graph": graph_data,
        "metrics": graph_data.get("metrics", {})
    }


@router.get("/{investigation_id}/metrics")
def get_graph_metrics(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns purely topological metrics (degree centrality, density, hop distance)
    for the given investigation graph.
    Requires authentication and investigation-level authorization.
    """
    inv = authorize_investigation_access(investigation_id, current_user, db)

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

    assess_record = db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id,
        AttributionAssessmentModel.is_current == True
    ).order_by(AttributionAssessmentModel.created_at.desc()).first()
    state = assess_record.attribution_state if assess_record else "INCONCLUSIVE"

    hard_gate = False
    actual_assessment_id = f"ASSESS-{investigation_id}"
    if assess_record and assess_record.payload:
        actual_assessment_id = assess_record.assessment_id
        hard_gate = (
            assess_record.payload.get("hard_gate_applied")
            or assess_record.payload.get("assessment_rationale", {}).get("hard_gate_applied", False)
            or assess_record.payload.get("assessment_rationale", {}).get("hard_cap_applied", False)
        )

    graph_data = GraphEngine.generate_cytoscape_graph(
        investigation_id=investigation_id,
        persona_a=inv.target_persona_a,
        persona_b=inv.target_persona_b,
        artifacts=artifacts,
        attribution_state=state,
        hard_gate_triggered=hard_gate,
        assessment_id=actual_assessment_id,
        evidence_ids=[r.evidence_id for r in records]
    )

    return {
        "investigation_id": investigation_id,
        "persona_a": inv.target_persona_a,
        "persona_b": inv.target_persona_b,
        "graph_source": graph_data.get("graph_source"),
        "metrics": graph_data.get("metrics", {})
    }
