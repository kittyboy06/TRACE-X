import { AttributionAssessment } from '../types';

/**
 * TRACE-X Emergency Presentation Fallbacks (Decision #13)
 * STRICT INVARIANT: Must be clearly labeled as DEMO FALLBACK DATA.
 * Used exclusively if the network or backend is unreachable during live evaluation.
 */

export const DEMO_FALLBACK_NOTICE = "DEMO FALLBACK DATA | SOURCE: FROZEN SIH BENCHMARK";

export const DEMO_FALLBACK_CASE_1: AttributionAssessment = {
  assessment_id: "ASSESS-INV-SIH-001-FALLBACK",
  investigation_id: "INV-SIH-001",
  target_persona_a: "GhostOperator",
  target_persona_b: "SpecterBroker",
  attribution_state: "LIKELY_LINK",
  confidence_band: "HIGH",
  confidence_range_min: 0.70,
  confidence_range_max: 0.85,
  base_score: 0.7639,
  real_world_identity: "NOT ESTABLISHED",
  hard_gate_applied: false,
  hard_gate_reason: null,
  evidence_dimensions: {
    cryptographic: {
      dimension_name: "cryptographic",
      status: "VALID",
      raw_score: 0.95,
      reliability_factor: 1.0,
      adjusted_score: 0.95,
      configured_weight: 0.30,
      contribution: 0.285,
      evidence_ids: ["EV-001-PGP", "EV-002-PGP-USE"],
      supporting_details: {
        match_type: "EXACT_PRIMARY_KEY_REUSE",
        key_id: "0x9B8A7C6D5E4F3A2B",
        fingerprint: "7A8B 9C0D 1E2F 3A4B 5C6D 7E8F 9A0B 1C2D 3E4F 5A6B"
      }
    },
    financial: {
      dimension_name: "financial",
      status: "VALID",
      raw_score: 0.90,
      reliability_factor: 0.60,
      adjusted_score: 0.54,
      configured_weight: 0.25,
      contribution: 0.135,
      evidence_ids: ["EV-005-BTC-TX"],
      supporting_details: {
        coinjoin_detected: true,
        coinjoin_dampening_factor: 0.60,
        nearest_vasp: "Kraken Exchange Deposit",
        hops_to_vasp: 4
      }
    },
    stylometric: {
      dimension_name: "stylometric",
      status: "VALID",
      raw_score: 0.8322,
      reliability_factor: 1.0,
      adjusted_score: 0.8322,
      configured_weight: 0.20,
      contribution: 0.1664,
      evidence_ids: ["EV-003-POSTS-A", "EV-004-POSTS-B"],
      supporting_details: {
        engine_type: "SENTENCE_TRANSFORMER_OR_STATISTICAL",
        word_count_a: 180,
        word_count_b: 180,
        token_count_a: 540,
        token_count_b: 535,
        guardrails_satisfied: true
      }
    },
    infrastructure: {
      dimension_name: "infrastructure",
      status: "VALID",
      raw_score: 0.65,
      reliability_factor: 1.0,
      adjusted_score: 0.65,
      configured_weight: 0.15,
      contribution: 0.0975,
      evidence_ids: ["EV-006-INFRA"],
      supporting_details: {
        shared_tls_cert: "sha256:4f8a12...",
        shared_ssh_fingerprint: "ssh-ed25519 SHA256:k9x..."
      }
    },
    behavioral_temporal: {
      dimension_name: "behavioral_temporal",
      status: "VALID",
      raw_score: 0.80,
      reliability_factor: 1.0,
      adjusted_score: 0.80,
      configured_weight: 0.10,
      contribution: 0.080,
      evidence_ids: ["EV-007-TEMPORAL"],
      supporting_details: {
        cadence_pattern: "SEQUENTIAL_HANDOFF",
        dormancy_observed: true,
        contradiction_detected: false
      }
    }
  },
  channel_dampenings: [
    {
      dimension: "financial",
      factor_applied: 0.60,
      reason: "CoinJoin collaborative mixing detected; dampening applied strictly to financial dimension."
    }
  ],
  global_contradictions: [],
  assessment_rationale: {
    summary: "Multi-modal evidentiary convergence observed across cryptographic, financial, stylometric, and infrastructure dimensions. S_base = 0.7639 indicates high-confidence correlation under SIH26151 criteria.",
    supporting_signal_count: 5,
    contradiction_count: 0,
    hard_gate_applied: false,
    hard_gate_reason: null
  },
  created_at: new Date().toISOString()
};

export const DEMO_FALLBACK_CASE_2: AttributionAssessment = {
  assessment_id: "ASSESS-INV-SIH-002-FALLBACK",
  investigation_id: "INV-SIH-002",
  target_persona_a: "ShadowActor",
  target_persona_b: "PhantomVendor",
  attribution_state: "INCONCLUSIVE",
  confidence_band: "LOW",
  confidence_range_min: 0.10,
  confidence_range_max: 0.35,
  base_score: 0.2150,
  real_world_identity: "NOT ESTABLISHED",
  hard_gate_applied: true,
  hard_gate_reason: "Level 2 Hard Gate enforced: Temporal Concurrency Clash (concurrent admin sessions across conflicting geos within 30s) and expired key reuse.",
  evidence_dimensions: {
    cryptographic: {
      dimension_name: "cryptographic",
      status: "VALID",
      raw_score: 0.15,
      reliability_factor: 1.0,
      adjusted_score: 0.15,
      configured_weight: 0.30,
      contribution: 0.045,
      evidence_ids: ["EV-101-PGP-SHADOW", "EV-102-PGP-PHANTOM"],
      supporting_details: {
        match_type: "DISPARATE_KEYS_EXPIRED_SIGNATURE",
        is_contradiction: true
      }
    },
    financial: {
      dimension_name: "financial",
      status: "VALID",
      raw_score: 0.60,
      reliability_factor: 0.60,
      adjusted_score: 0.36,
      configured_weight: 0.25,
      contribution: 0.090,
      evidence_ids: ["EV-105-BTC-MIXING"],
      supporting_details: {
        coinjoin_detected: true,
        coinjoin_dampening_factor: 0.60
      }
    },
    stylometric: {
      dimension_name: "stylometric",
      status: "NOT_ENOUGH_EVIDENCE",
      raw_score: 0.0,
      reliability_factor: 1.0,
      adjusted_score: 0.0,
      configured_weight: 0.20,
      contribution: 0.0,
      evidence_ids: ["EV-103-POSTS-SHADOW", "EV-104-POSTS-PHANTOM"],
      supporting_details: {
        reason: "Corpus fails the minimum 150-word AND 500-token evidentiary threshold (Persona A: 118w/390t, Persona B: 114w/380t). Stylometric signal withheld to prevent hallucinated similarity.",
        word_count_a: 118,
        word_count_b: 114,
        guardrails_satisfied: false
      }
    },
    infrastructure: {
      dimension_name: "infrastructure",
      status: "UNAVAILABLE",
      raw_score: 0.0,
      reliability_factor: 1.0,
      adjusted_score: 0.0,
      configured_weight: 0.15,
      contribution: 0.0,
      evidence_ids: [],
      supporting_details: {
        reason: "Mutually exclusive infrastructure architectures (conflicting SSH server daemons and SSL fingerprints)."
      }
    },
    behavioral_temporal: {
      dimension_name: "behavioral_temporal",
      status: "VALID",
      raw_score: 0.80,
      reliability_factor: 1.0,
      adjusted_score: 0.80,
      configured_weight: 0.10,
      contribution: 0.080,
      evidence_ids: ["EV-106-TEMPORAL-CLASH"],
      supporting_details: {
        contradiction_detected: true,
        contradiction_type: "TEMPORAL_CONCURRENCY_CLASH",
        delta_seconds: 14.2
      }
    }
  },
  channel_dampenings: [
    {
      dimension: "financial",
      factor_applied: 0.60,
      reason: "Samourai Whirlpool mixing detected; dampening applied strictly to financial dimension."
    }
  ],
  global_contradictions: [
    {
      contradiction_type: "TEMPORAL_CONCURRENCY_CLASH",
      severity: "CRITICAL",
      penalty: 1.0,
      triggers_hard_gate: true,
      detail: "Authenticated admin actions occurred simultaneously in Frankfurt and Singapore networks within 14.2s. Physically incompatible with single operational actor."
    },
    {
      contradiction_type: "EXPIRED_KEY_REUSE",
      severity: "HIGH",
      penalty: 0.5,
      triggers_hard_gate: false,
      detail: "PGP key expired in 2021 was asserted for authentication in 2024."
    }
  ],
  assessment_rationale: {
    summary: "Level 2 Hard Gate enforced. Despite partial behavioral coincidence, verified operational contradictions (temporal concurrency clash) mandate refusal to link. Assessment is strictly INCONCLUSIVE with LOW confidence to eliminate false attribution.",
    supporting_signal_count: 2,
    contradiction_count: 2,
    hard_gate_applied: true,
    hard_gate_reason: "Level 2 Hard Gate enforced: Temporal Concurrency Clash (concurrent admin sessions across conflicting geos within 30s) and expired key reuse."
  },
  created_at: new Date().toISOString()
};
