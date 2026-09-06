from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import re

HEX64_REGEX = r"^[a-fA-F0-9]{64}$"


class ImmutableContract(BaseModel):
    """
    Base contract enforcing strict immutability and forbidding undeclared extra fields.
    All inter-stage analytical contracts derive from this base.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")


# =====================================================================
# Canonical Enums
# =====================================================================

class ArtifactType(str, Enum):
    PGP_KEY = "PGP_KEY"
    FORUM_POST = "FORUM_POST"
    BTC_TRANSACTION = "BTC_TRANSACTION"
    INFRASTRUCTURE_HEADER = "INFRASTRUCTURE_HEADER"
    TEMPORAL_BURST = "TEMPORAL_BURST"


class EntityType(str, Enum):
    PERSONA = "PERSONA"
    PGP_FINGERPRINT = "PGP_FINGERPRINT"
    WALLET = "WALLET"
    ONION_SERVICE = "ONION_SERVICE"
    DOMAIN = "DOMAIN"
    CERTIFICATE = "CERTIFICATE"
    IP_ENDPOINT = "IP_ENDPOINT"


class DimensionType(str, Enum):
    CRYPTOGRAPHIC = "CRYPTOGRAPHIC"
    FINANCIAL = "FINANCIAL"
    STYLOMETRIC = "STYLOMETRIC"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    BEHAVIORAL_TEMPORAL = "BEHAVIORAL_TEMPORAL"


class ReliabilityClass(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ScanStatus(str, Enum):
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    FAILED = "FAILED"
    NEVER_SCANNED = "NEVER_SCANNED"


class SignalStatus(str, Enum):
    VALID = "VALID"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class ContradictionLevel(str, Enum):
    LEVEL_1_CHANNEL_DAMPENING = "LEVEL_1_CHANNEL_DAMPENING"
    LEVEL_2_HARD_GATE = "LEVEL_2_HARD_GATE"


class AttributionState(str, Enum):
    CONFIRMED_LINK = "CONFIRMED_LINK"
    LIKELY_LINK = "LIKELY_LINK"
    POSSIBLE_LINK = "POSSIBLE_LINK"
    INCONCLUSIVE = "INCONCLUSIVE"
    LIKELY_DIFFERENT = "LIKELY_DIFFERENT"


class ConfidenceBand(str, Enum):
    """
    Interpretive confidence bands representing analyst assessment certainty.
    Must never be labeled or interpreted as mathematical identity probabilities.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditEventType(str, Enum):
    EVIDENCE_INGESTED = "EVIDENCE_INGESTED"
    WEIGHTS_COMMITTED = "WEIGHTS_COMMITTED"
    ASSESSMENT_GENERATED = "ASSESSMENT_GENERATED"
    ANALYST_DECISION = "ANALYST_DECISION"


# =====================================================================
# Canonical Data Contracts
# =====================================================================

class NormalizedArtifact(ImmutableContract):
    """
    Standardized evidentiary artifact produced by normalization.py.
    """
    evidence_id: str = Field(..., min_length=1, description="Unique immutable artifact identifier")
    investigation_id: str = Field(..., min_length=1, description="Parent investigation ID")
    artifact_type: ArtifactType
    source_uri: str = Field(..., min_length=1)
    collected_at: datetime
    content_hash: str = Field(..., pattern=HEX64_REGEX, description="Deterministic SHA-256 hash of canonical normalized payload")
    raw_payload: Dict[str, Any]
    normalized_payload: Dict[str, Any]


class ExtractedEntity(ImmutableContract):
    """
    Discrete technical, cryptographic, or financial indicator extracted from an artifact.
    """
    entity_id: str = Field(..., min_length=1)
    entity_type: EntityType
    value: str = Field(..., min_length=1)
    evidence_id: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score in [0.0, 1.0]")


class SourceReliabilityAssessment(ImmutableContract):
    """
    Trustworthiness and freshness evaluation for an evidence feed.
    Modifies evidence reliability entering dimensions; is never a 6th scoring dimension.
    """
    source_uri: str = Field(..., min_length=1)
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Overall reliability score in [0.0, 1.0]")
    reliability_class: ReliabilityClass
    factors: Dict[str, float] = Field(..., description="Transparent factor breakdown (reputation, freshness, corroboration, consistency)")
    last_scan: datetime
    scan_status: ScanStatus


class DimensionSignal(ImmutableContract):
    """
    Output produced by one of the five independent analytical engines.
    """
    dimension: DimensionType
    raw_score: float = Field(..., ge=0.0, le=1.0, description="Unweighted engine score in [0.0, 1.0]")
    reliability_factor: float = Field(..., ge=0.0, le=1.0, description="Source reliability and Level 1 channel dampening modifier")
    adjusted_score: float = Field(..., ge=0.0, le=1.0, description="raw_score * reliability_factor")
    status: SignalStatus = Field(default=SignalStatus.VALID, description="Distinguishes valid scores from insufficient evidence or unavailability")
    evidence_ids: List[str] = Field(default_factory=list)
    engine_metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution engine details (e.g. model name, fallback status)")
    findings: List[Dict[str, Any]] = Field(default_factory=list)


class ContradictionFinding(ImmutableContract):
    """
    Recorded contradiction or inconsistency across evidence channels.
    """
    level: ContradictionLevel
    contradiction_type: str = Field(..., min_length=1, description="Classification identifier (e.g. TEMPORAL_CONCURRENCY_CLASH, POTENTIAL_COINJOIN)")
    target_dimension: Optional[DimensionType] = None
    dampening_factor: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Channel reliability multiplier if Level 1")
    trigger_hard_gate: bool = Field(default=False, description="True if Level 2 hard gate forcing INCONCLUSIVE")
    explanation: str = Field(..., min_length=1)
    evidence_ids: List[str] = Field(default_factory=list)


class AttributionAssessment(ImmutableContract):
    """
    Final explainable attribution assessment produced by EvidenceFusionEngine.
    """
    assessment_id: str = Field(..., min_length=1)
    investigation_id: str = Field(..., min_length=1)
    attribution_state: AttributionState
    confidence_band: ConfidenceBand
    base_score: float = Field(..., ge=0.0, le=1.0, description="Fused weighted sum: sum(w_i * adjusted_score_i)")
    real_world_identity: str = Field(default="NOT ESTABLISHED")
    dimension_signals: Dict[DimensionType, DimensionSignal]
    contradictions: List[ContradictionFinding] = Field(default_factory=list)
    hard_gate_applied: bool = False
    hard_gate_reason: Optional[str] = None
    rationale: str = Field(..., min_length=1)
    is_current: bool = True
    created_at: datetime


class AuditEvent(ImmutableContract):
    """
    Append-only tamper-evident audit record within an investigation's hash chain.
    First event uses previous_event_hash = '0'*64; subsequent events link to the preceding event's event_hash.
    """
    event_id: str = Field(..., min_length=1)
    investigation_id: str = Field(..., min_length=1)
    event_type: AuditEventType
    actor_id: str = Field(..., min_length=1, description="Authenticated analyst ID derived server-side from JWT")
    timestamp: datetime
    canonical_event_data: str = Field(..., min_length=1, description="Deterministic canonical JSON string")
    previous_event_hash: str = Field(..., pattern=HEX64_REGEX, description="Preceding event hash (or '0'*64 for first event)")
    event_hash: str = Field(..., pattern=HEX64_REGEX, description="SHA256(canonical_event_data + previous_event_hash)")


class PipelineResult(ImmutableContract):
    """
    Composite result returned by services/pipeline.py containing all stage artifacts.
    """
    investigation_id: str = Field(..., min_length=1)
    normalized_artifacts: List[NormalizedArtifact]
    extracted_entities: List[ExtractedEntity]
    source_reliability: List[SourceReliabilityAssessment]
    dimension_signals: Dict[DimensionType, DimensionSignal]
    contradictions: List[ContradictionFinding]
    assessment: AttributionAssessment
    audit_event: AuditEvent
