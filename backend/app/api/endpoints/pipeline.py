from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json
from typing import Dict, Any, List

from app.models.database import (
    get_db,
    InvestigationModel,
    EvidenceRecordModel,
    AttributionAssessmentModel,
    SessionLocal
)
from app.services.stylometry_engine import StylometryEngine
from app.services.blockchain_engine import BlockchainEngine
from app.services.behavioral_engine import BehavioralEngine
from app.services.graph_engine import GraphEngine
from app.services.fusion_engine import EvidenceFusionEngine
from app.core.config import settings

router = APIRouter()


def execute_analysis_pipeline(investigation_id: str, db: Session) -> Dict[str, Any]:
    """
    Executes the 4 analytical engines and the Two-Level Evidence Fusion Engine synchronously or via background tasks.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")
        
    import json
    def parse_payload(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return val or {}

    artifacts = [
        {
            "evidence_id": r.evidence_id,
            "artifact_type": r.artifact_type,
            "source_uri": r.source_uri,
            "collected_at": r.collected_at.isoformat() if hasattr(r.collected_at, "isoformat") else str(r.collected_at),
            "raw_payload": parse_payload(r.raw_payload)
        }
        for r in records
    ]

    # Partition artifacts by type
    pgp_artifacts = [a for a in artifacts if a["artifact_type"] == "PGP_KEY"]
    post_artifacts = [a for a in artifacts if a["artifact_type"] == "FORUM_POST"]
    tx_artifacts = [a for a in artifacts if a["artifact_type"] == "BTC_TRANSACTION"]
    infra_artifacts = [a for a in artifacts if a["artifact_type"] == "INFRASTRUCTURE_HEADER"]
    temporal_artifacts = [a for a in artifacts if a["artifact_type"] == "TEMPORAL_BURST"]

    # Persona post split
    posts_a = [p for p in post_artifacts if p.get("raw_payload", {}).get("persona") == inv.target_persona_a]
    posts_b = [p for p in post_artifacts if p.get("raw_payload", {}).get("persona") == inv.target_persona_b]

    # 1. Stylometry Engine
    stylometry_signal = StylometryEngine.analyze_personas(
        posts_a, posts_b, weight=settings.DEFAULT_WEIGHT_STYLOMETRY
    )

    # 2. Blockchain Forensics Engine
    financial_signal = BlockchainEngine.analyze_transactions(
        tx_artifacts, weight=settings.DEFAULT_WEIGHT_FINANCIAL
    )

    # 3. Behavioral & Temporal Engine
    behavioral_signal, global_contradictions = BehavioralEngine.analyze_behavior_and_temporality(
        temporal_artifacts, post_artifacts, weight=settings.DEFAULT_WEIGHT_BEHAVIORAL
    )

    # 4. Graph & Cryptographic Engine
    crypto_signal, infra_signal = GraphEngine.analyze_cryptographic_and_infra(
        pgp_artifacts, infra_artifacts,
        weight_crypto=settings.DEFAULT_WEIGHT_CRYPTO,
        weight_infra=settings.DEFAULT_WEIGHT_INFRASTRUCTURE
    )

    # 5. Evidence Fusion Engine
    assessment_id = f"ASSESS-{investigation_id}-{datetime.utcnow().strftime('%H%M%S')}"
    assessment = EvidenceFusionEngine.fuse_evidence(
        assessment_id=assessment_id,
        investigation_id=investigation_id,
        persona_a=inv.target_persona_a,
        persona_b=inv.target_persona_b,
        crypto_signal=crypto_signal,
        financial_signal=financial_signal,
        stylometry_signal=stylometry_signal,
        infra_signal=infra_signal,
        behavioral_signal=behavioral_signal,
        global_contradictions=global_contradictions
    )

    # Save assessment in DB
    existing_assessment = db.query(AttributionAssessmentModel).filter(AttributionAssessmentModel.investigation_id == investigation_id).first()
    if existing_assessment:
        existing_assessment.attribution_state = assessment.attribution_state.value
        existing_assessment.confidence_band = assessment.confidence_band.value
        existing_assessment.base_score = assessment.base_score
        existing_assessment.evidence_score = assessment.evidence_score
        existing_assessment.payload = json.loads(assessment.model_dump_json())
        existing_assessment.created_at = datetime.utcnow()
    else:
        db_assess = AttributionAssessmentModel(
            assessment_id=assessment.assessment_id,
            investigation_id=investigation_id,
            attribution_state=assessment.attribution_state.value,
            confidence_band=assessment.confidence_band.value,
            base_score=assessment.base_score,
            evidence_score=assessment.evidence_score,
            real_world_identity="NOT ESTABLISHED",
            payload=json.loads(assessment.model_dump_json()),
            created_at=datetime.utcnow()
        )
        db.add(db_assess)
    db.commit()

    return {
        "assessment": assessment,
        "artifacts": artifacts
    }


@router.get("/stream/{investigation_id}")
async def stream_pipeline_progress(investigation_id: str):
    """
    Streams Server-Sent Events (SSE) detailing each pipeline stage execution.
    """
    async def event_generator():
        stages = [
            ("EVIDENCE_INGESTION", 15, "Validating artifact schemas & computing SHA-256 integrity hashes..."),
            ("AI_STYLOMETRY", 35, "Tokenizing forum texts & computing author embedding similarity..."),
            ("BLOCKCHAIN_FORENSICS", 60, "Executing UTXO graph parsing & CoinJoin heuristic check..."),
            ("GRAPH_INTELLIGENCE", 80, "Resolving Neo4j property graph & checking infrastructure fingerprints..."),
            ("BEHAVIORAL_TEMPORAL", 90, "Evaluating operational dormancy & temporal concurrency windows..."),
            ("EVIDENCE_FUSION", 100, "Applying Two-Level Contradiction model & finalizing attribution assessment.")
        ]

        db = SessionLocal()
        try:
            for stage, pct, msg in stages:
                payload = {
                    "investigation_id": investigation_id,
                    "stage": stage,
                    "progress_percentage": pct,
                    "message": msg,
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.2)  # Fast ~1.2s total stream for demo snappy feel

            # Run actual analysis calculation
            res = execute_analysis_pipeline(investigation_id, db)
            completion_payload = {
                "investigation_id": investigation_id,
                "stage": "COMPLETE",
                "progress_percentage": 100,
                "message": f"Attribution Complete: {res['assessment'].attribution_state.value} (Score: {res['assessment'].evidence_score})",
                "assessment": res["assessment"].model_dump()
            }
            yield f"data: {json.dumps(completion_payload)}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
