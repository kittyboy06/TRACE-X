from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from enum import Enum


class EvidenceType(str, Enum):
    FORUM_POST = "FORUM_POST"
    PGP_KEY = "PGP_KEY"
    BTC_TRANSACTION = "BTC_TRANSACTION"
    INFRASTRUCTURE_HEADER = "INFRASTRUCTURE_HEADER"
    TEMPORAL_BURST = "TEMPORAL_BURST"


class EvidenceStrength(str, Enum):
    VERY_HIGH = "VERY_HIGH"        # E.g. Direct cryptographic key reuse
    HIGH = "HIGH"                  # E.g. Corroborated multi-input wallet cluster
    MEDIUM = "MEDIUM"              # E.g. High stylometric similarity (>0.80) / rare infra
    LOW = "LOW"                    # E.g. Topic overlap, single-input heuristic
    CONTRADICTORY = "CONTRADICTORY" # Explicit negative signal


class ConfidenceBand(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INCONCLUSIVE = "INCONCLUSIVE"


class SignalStatus(str, Enum):
    VALID = "VALID"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class AttributionState(str, Enum):
    CONFIRMED_LINK = "CONFIRMED_LINK"
    LIKELY_LINK = "LIKELY_LINK"
    POSSIBLE_LINK = "POSSIBLE_LINK"
    INCONCLUSIVE = "INCONCLUSIVE"
    LIKELY_DIFFERENT = "LIKELY_DIFFERENT"


class AnalystDecision(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    INVESTIGATE = "INVESTIGATE"


# Alias for backward compatibility
AnalystAction = AnalystDecision


class StylometryEngineType(str, Enum):
    TRANSFORMER = "TRANSFORMER"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"


# --- Evidence Ingestion & Provenance Models ---

class ProvenanceRecord(BaseModel):
    evidence_id: str = Field(..., description="Unique immutable artifact identifier")
    investigation_id: str = Field(..., description="Parent investigation ID")
    source_uri: str = Field(..., description="Raw source location or thread URL")
    collected_at: datetime
    content_hash: str = Field(..., description="SHA-256 integrity hash of raw payload")
    artifact_type: EvidenceType
    raw_payload: Dict[str, Any]
    extractor_version: str = Field(default="v1.4.0")
    model_version: Optional[str] = Field(default="sentence-transformers/all-mpnet-base-v2")
    provenance_chain: List[str] = Field(default_factory=lambda: ["RAW_INGEST", "NORMALIZED"])


class EvidencePackageUpload(BaseModel):
    investigation_id: str
    target_persona_a: str
    target_persona_b: str
    artifacts: List[Dict[str, Any]]


# --- 5-Dimension Engine Output Models ---

class DimensionSignal(BaseModel):
    dimension_name: Literal["cryptographic", "financial", "stylometric", "infrastructure", "behavioral_temporal"]
    status: SignalStatus = Field(default=SignalStatus.VALID, description="Distinguishes zero-score from not enough evidence")
    raw_score: float = Field(..., ge=0.0, le=1.0, description="Raw model or heuristic similarity scalar")
    reliability_factor: float = Field(default=1.0, ge=0.0, le=1.0, description="Level 1 channel reliability modifier")
    adjusted_score: float = Field(..., ge=0.0, le=1.0, description="raw_score * reliability_factor")
    configured_weight: float = Field(..., ge=0.0, le=1.0, description="Weight proportion in fusion")
    contribution: float = Field(..., description="configured_weight * adjusted_score")
    evidence_ids: List[str] = []
    supporting_details: Dict[str, Any] = {}


class ChannelDampening(BaseModel):
    dimension: str
    factor_applied: float
    reason: str


class GlobalContradiction(BaseModel):
    contradiction_type: str
    severity: Literal["HIGH", "CRITICAL"]
    penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    triggers_hard_gate: bool = Field(default=False)
    detail: str


# --- Fused Attribution Assessment Models ---

class EvidenceDimensionsBlock(BaseModel):
    cryptographic: DimensionSignal
    financial: DimensionSignal
    stylometric: DimensionSignal
    infrastructure: DimensionSignal
    behavioral_temporal: DimensionSignal


class AssessmentRationale(BaseModel):
    summary: str
    supporting_signal_count: int
    contradiction_count: int
    hard_cap_applied: bool
    hard_cap_reason: Optional[str] = None


class AttributionAssessment(BaseModel):
    assessment_id: str
    investigation_id: str
    target_persona_a: str
    target_persona_b: str
    attribution_state: AttributionState
    confidence_band: ConfidenceBand
    confidence_range_min: float = Field(..., ge=0.0, le=1.0)
    confidence_range_max: float = Field(..., ge=0.0, le=1.0)
    base_score: float = Field(..., description="Weighted sum before global penalties")
    global_penalty_multiplier: float = Field(default=1.0, description="Product of (1 - p_j) for soft contradictions")
    evidence_score: float = Field(..., description="Final fused numerical score")
    real_world_identity: str = Field(default="NOT ESTABLISHED")
    evidence_dimensions: EvidenceDimensionsBlock
    channel_dampenings: List[ChannelDampening] = []
    global_contradictions: List[GlobalContradiction] = []
    assessment_rationale: AssessmentRationale
    created_at: datetime


class SensitivityAdjustmentRequest(BaseModel):
    investigation_id: str
    weight_cryptographic: float = Field(..., ge=0.0, le=1.0)
    weight_financial: float = Field(..., ge=0.0, le=1.0)
    weight_stylometric: float = Field(..., ge=0.0, le=1.0)
    weight_infrastructure: float = Field(..., ge=0.0, le=1.0)
    weight_behavioral: float = Field(..., ge=0.0, le=1.0)


# --- Append-Only Audit & Decision Models ---

class AuditDecisionRequest(BaseModel):
    investigation_id: str
    assessment_id: str
    action: AnalystDecision
    analyst_id: str
    rationale: str


class AuditEvent(BaseModel):
    audit_id: str
    investigation_id: str
    assessment_id: str
    action: AnalystDecision
    analyst_id: str
    timestamp: datetime
    rationale: str
    prior_state: str = Field(..., description="Prior algorithmic attribution state (e.g. LIKELY_LINK)")
    resulting_state: str = Field(..., description="Resulting operational state (e.g. CONFIRMED, REJECTED)")
    event_hash: str = Field(..., description="Cryptographic SHA-256 fingerprint of the audit record")


# --- Pipeline Streaming Event ---

class PipelineProgressEvent(BaseModel):
    investigation_id: str
    stage: str
    progress_percentage: int
    message: str
    timestamp: datetime
