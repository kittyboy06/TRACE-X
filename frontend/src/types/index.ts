export type AttributionState = 
  | 'CONFIRMED_LINK'
  | 'LIKELY_LINK'
  | 'POSSIBLE_LINK'
  | 'INCONCLUSIVE'
  | 'LIKELY_DIFFERENT';

export type ConfidenceBand = 'HIGH' | 'MEDIUM' | 'LOW';

export type SignalStatus = 'VALID' | 'NOT_ENOUGH_EVIDENCE' | 'UNAVAILABLE' | 'ERROR';

export type AnalystAction = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'INVESTIGATE' | 'WEIGHTS_COMMITTED';

export interface DimensionSignal {
  dimension_name: 'cryptographic' | 'financial' | 'stylometric' | 'infrastructure' | 'behavioral_temporal';
  status: SignalStatus;
  raw_score: number;
  reliability_factor: number;
  adjusted_score: number;
  configured_weight: number;
  contribution: number;
  evidence_ids: string[];
  supporting_details: Record<string, any>;
  findings?: Array<Record<string, any>>;
}

export interface ChannelDampening {
  dimension: string;
  factor_applied: number;
  reason: string;
}

export interface GlobalContradiction {
  contradiction_type: string;
  severity: 'HIGH' | 'CRITICAL';
  penalty: number;
  triggers_hard_gate: boolean;
  detail: string;
}

export interface EvidenceDimensionsBlock {
  cryptographic: DimensionSignal;
  financial: DimensionSignal;
  stylometric: DimensionSignal;
  infrastructure: DimensionSignal;
  behavioral_temporal: DimensionSignal;
}

export interface AssessmentRationale {
  summary: string;
  supporting_signal_count: number;
  contradiction_count: number;
  hard_gate_applied: boolean;
  hard_gate_reason?: string | null;
}

export interface AttributionAssessment {
  assessment_id: string;
  investigation_id: string;
  target_persona_a: string;
  target_persona_b: string;
  attribution_state: AttributionState;
  confidence_band: ConfidenceBand;
  confidence_range_min?: number;
  confidence_range_max?: number;
  base_score: number;
  global_penalty_multiplier?: number;
  evidence_score?: number;
  real_world_identity: string;
  hard_gate_applied: boolean;
  hard_gate_reason?: string | null;
  evidence_dimensions: EvidenceDimensionsBlock;
  channel_dampenings: ChannelDampening[];
  global_contradictions: GlobalContradiction[];
  assessment_rationale: AssessmentRationale;
  created_at: string;
}

export interface ProvenanceRecord {
  evidence_id: string;
  investigation_id: string;
  source_uri: string;
  collected_at: string;
  content_hash: string;
  artifact_type: string;
  raw_payload: Record<string, any>;
  extractor_version?: string;
  model_version?: string;
  provenance_chain?: string[];
}

export interface SourceFactors {
  reputation: number;
  freshness: number;
  corroboration: number;
  consistency: number;
}

export interface SourceReliabilityRecord {
  id: number;
  source_uri: string;
  trust_tier: string;
  reliability_score: number;
  reliability_class: 'HIGH' | 'MEDIUM' | 'LOW';
  factors: SourceFactors;
  last_scan: string;
  scan_status: string;
  diagnostic_status: string;
}

export interface ExtractedEntityRecord {
  entity_id: string;
  entity_type: string;
  value: string;
  evidence_id: string;
  confidence: number;
}

export interface CytoscapeElement {
  data: {
    id: string;
    label?: string;
    type?: string;
    source?: string;
    target?: string;
    evidence_strength?: string;
    risk?: string;
    centrality?: number;
    evidence_id?: string;
    amount_btc?: number;
    reason?: string;
    state?: string;
    words?: number;
    [key: string]: any;
  };
}

export interface CytoscapeGraphData {
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
}

export interface AuditEvent {
  audit_id: string;
  investigation_id: string;
  assessment_id: string;
  action: AnalystAction;
  analyst_id: string;
  timestamp: string;
  rationale: string;
  prior_state: string;
  resulting_state: string;
  previous_hash?: string;
  event_hash: string;
}

export interface PipelineProgressEvent {
  investigation_id: string;
  stage: string;
  progress_percentage: number;
  message: string;
  timestamp?: string;
}

export interface PresentationModeState {
  enabled: boolean;
  activeScenario?: 'CASE_1' | 'CASE_2';
  tourStep?: number;
  timerSeconds?: number;
}
