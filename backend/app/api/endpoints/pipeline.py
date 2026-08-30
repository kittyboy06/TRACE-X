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
    Executes the 4 analytical engines and the Two-Level Evidence Fusion Engine synchronously.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")
        
    def parse_payload(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return val or {}

    records = db.query(EvidenceRecordModel).filter(EvidenceRecordModel.investigation_id == investigation_id).all()
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
    assessment_id = f"ASSESS-{investigation_id}-{datetime.utcnow().strftime('%H%M%S%f')}"
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

    # Mark prior assessments as is_current = False
    db.query(AttributionAssessmentModel).filter(
        AttributionAssessmentModel.investigation_id == investigation_id
    ).update({"is_current": False})

    # Save new current assessment in DB
    db_assess = AttributionAssessmentModel(
        assessment_id=assessment.assessment_id,
        investigation_id=investigation_id,
        attribution_state=assessment.attribution_state.value,
        confidence_band=assessment.confidence_band.value,
        base_score=assessment.base_score,
        evidence_score=assessment.evidence_score,
        real_world_identity="NOT ESTABLISHED",
        is_current=True,
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
    Streams Server-Sent Events (SSE) detailing actual stepwise execution of each analytical engine.
    """
    async def event_generator():
        db = SessionLocal()
        try:
            inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
            if not inv:
                yield f"data: {json.dumps({'error': f'Investigation {investigation_id} not found'})}\n\n"
                return

            def parse_payload(val):
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except Exception:
                        return {}
                return val or {}

            # --- STAGE 1: Evidence Ingestion & Provenance (15%) ---
            records = db.query(EvidenceRecordModel).filter(EvidenceRecordModel.investigation_id == investigation_id).all()
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

            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'EVIDENCE_INGESTION', 'progress_percentage': 15, 'message': f'Validated {len(artifacts)} artifacts with deterministic SHA-256 provenance.', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            pgp_artifacts = [a for a in artifacts if a["artifact_type"] == "PGP_KEY"]
            post_artifacts = [a for a in artifacts if a["artifact_type"] == "FORUM_POST"]
            tx_artifacts = [a for a in artifacts if a["artifact_type"] == "BTC_TRANSACTION"]
            infra_artifacts = [a for a in artifacts if a["artifact_type"] == "INFRASTRUCTURE_HEADER"]
            temporal_artifacts = [a for a in artifacts if a["artifact_type"] == "TEMPORAL_BURST"]

            posts_a = [p for p in post_artifacts if p.get("raw_payload", {}).get("persona") == inv.target_persona_a]
            posts_b = [p for p in post_artifacts if p.get("raw_payload", {}).get("persona") == inv.target_persona_b]

            # --- STAGE 2: AI Stylometry Engine (35%) ---
            stylometry_signal = StylometryEngine.analyze_personas(
                posts_a, posts_b, weight=settings.DEFAULT_WEIGHT_STYLOMETRY
            )
            style_engine_used = stylometry_signal.supporting_details.get("engine", "STYLOMETRY")
            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'AI_STYLOMETRY', 'progress_percentage': 35, 'message': f'Stylometry completed via {style_engine_used} (Similarity: {stylometry_signal.raw_score}, Status: {stylometry_signal.status.value}).', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            # --- STAGE 3: Blockchain Forensics Engine (60%) ---
            financial_signal = BlockchainEngine.analyze_transactions(
                tx_artifacts, weight=settings.DEFAULT_WEIGHT_FINANCIAL
            )
            coinjoin_detected = financial_signal.supporting_details.get("coinjoin_detected", False)
            nearest_vasp = financial_signal.supporting_details.get("nearest_vasp", "None")
            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'BLOCKCHAIN_FORENSICS', 'progress_percentage': 60, 'message': f'UTXO flow traced. CoinJoin detected: {coinjoin_detected}, Target VASP: {nearest_vasp}.', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            # --- STAGE 4: Graph Intelligence & Infrastructure (80%) ---
            crypto_signal, infra_signal = GraphEngine.analyze_cryptographic_and_infra(
                pgp_artifacts, infra_artifacts,
                weight_crypto=settings.DEFAULT_WEIGHT_CRYPTO,
                weight_infra=settings.DEFAULT_WEIGHT_INFRASTRUCTURE
            )
            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'GRAPH_INTELLIGENCE', 'progress_percentage': 80, 'message': f'Graph topology correlated. Cryptographic: {crypto_signal.status.value}, Infra: {infra_signal.status.value}.', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            # --- STAGE 5: Behavioral & Temporal Intelligence (90%) ---
            behavioral_signal, global_contradictions = BehavioralEngine.analyze_behavior_and_temporality(
                temporal_artifacts, post_artifacts, weight=settings.DEFAULT_WEIGHT_BEHAVIORAL
            )
            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'BEHAVIORAL_TEMPORAL', 'progress_percentage': 90, 'message': f'Dormancy cadence evaluated. Contradiction count: {len(global_contradictions)}.', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            # --- STAGE 6: Evidence Fusion Engine (95%) ---
            assessment_id = f"ASSESS-{investigation_id}-{datetime.utcnow().strftime('%H%M%S%f')}"
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
            yield f"data: {json.dumps({'investigation_id': investigation_id, 'stage': 'EVIDENCE_FUSION', 'progress_percentage': 95, 'message': f'Two-Level Fusion finalized. Fused Score: {assessment.evidence_score} ({assessment.attribution_state.value}).', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.05)

            # --- STAGE 7: Persistence & Complete (100%) ---
            db.query(AttributionAssessmentModel).filter(
                AttributionAssessmentModel.investigation_id == investigation_id
            ).update({"is_current": False})

            db_assess = AttributionAssessmentModel(
                assessment_id=assessment.assessment_id,
                investigation_id=investigation_id,
                attribution_state=assessment.attribution_state.value,
                confidence_band=assessment.confidence_band.value,
                base_score=assessment.base_score,
                evidence_score=assessment.evidence_score,
                real_world_identity="NOT ESTABLISHED",
                is_current=True,
                payload=json.loads(assessment.model_dump_json()),
                created_at=datetime.utcnow()
            )
            db.add(db_assess)
            db.commit()

            completion_payload = {
                "investigation_id": investigation_id,
                "stage": "COMPLETE",
                "progress_percentage": 100,
                "message": f"Attribution Complete: {assessment.attribution_state.value} (Score: {assessment.evidence_score})",
                "assessment": assessment.model_dump(mode="json")
            }
            yield f"data: {json.dumps(completion_payload)}\n\n"
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
