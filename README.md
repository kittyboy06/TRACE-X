# 🛡️ TRACE-X: Threat Relationship & Attribution Correlation Engine

> **Next-Generation Explainable Cyber Threat Intelligence (CTI) & Multi-Modal Attribution Platform**  
> **Problem Statement SIH26151 | National Technical Research Organisation (NTRO) | Smart India Hackathon 2026**

---

[![CI Test Suite](https://img.shields.io/badge/Tests-95%2F95%20Passed-emerald?style=flat-square&logo=pytest)](https://pytest.org)
[![SIH Checkpoints](https://img.shields.io/badge/SIH%20Checkpoints-10%2F10%20Verified-blue?style=flat-square&logo=checkmarx)](scripts/verify_sih_submission.py)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-3776AB?style=flat-square&logo=python)](https://www.python.org)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com)
[![Cytoscape.js](https://img.shields.io/badge/Cytoscape.js-3.28-orange?style=flat-square)](https://js.cytoscape.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.18-008CC1?style=flat-square&logo=neo4j)](https://neo4j.com)
[![ReportLab](https://img.shields.io/badge/ReportLab-4.0%2B-red?style=flat-square)](https://www.reportlab.com)
[![Docker](https://img.shields.io/badge/Docker-Compose%20v2-2496ED?style=flat-square&logo=docker)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 📑 Table of Contents
1. [Executive Overview](#-executive-overview)
2. [Key Differentiators & Innovations](#-key-differentiators--innovations)
3. [Tech Stack](#-tech-stack)
4. [Prerequisites](#-prerequisites)
5. [Getting Started (Quick Start)](#-getting-started)
   - [Option 1: Production Multi-Container Stack (Docker Compose)](#option-1-production-multi-container-stack-docker-compose)
   - [Option 2: Standalone Local Development](#option-2-standalone-local-development)
6. [System Architecture](#-system-architecture)
   - [Directory Structure](#directory-structure)
   - [Request & Ingestion Lifecycle](#request--ingestion-lifecycle)
   - [Data Flow Architecture](#data-flow-architecture)
   - [Relational & Graph Database Schemas](#relational--graph-database-schemas)
7. [Mathematical Attribution & Fusion Framework](#-mathematical-attribution--fusion-framework)
   - [Normalized Weighting Constraint](#1-normalized-weighting-constraint)
   - [Level 1: Channel-Specific Reliability Dampening](#2-level-1-channel-specific-reliability-dampening)
   - [Decision #10: 4-Factor Source Reliability Engine](#3-decision-10-4-factor-source-reliability-engine)
   - [Base Fused Score Formulation](#4-base-fused-score-formulation)
   - [Level 2: Global Contradiction Hard Gate](#5-level-2-global-contradiction-hard-gate)
   - [Confidence Band Calibration & State Mapping](#6-confidence-band-calibration--state-mapping)
8. [Analytical Engines Breakdown](#-analytical-engines-breakdown)
9. [Benchmark Evaluation Scenarios (Case 1 & Case 2)](#-benchmark-evaluation-scenarios)
10. [Publication-Grade Forensic Reporting Dossier (Decision #11)](#-publication-grade-forensic-reporting-dossier-decision-11)
11. [Interactive Command Center & UI Workspace](#-interactive-command-center--ui-workspace)
12. [REST API Reference & SSE Streaming Contracts](#-rest-api-reference--sse-streaming-contracts)
13. [Environment Variables Reference](#-environment-variables-reference)
14. [Available Scripts & Quality Verification Commands](#-available-scripts--quality-verification-commands)
15. [Automated Testing & SIH Verification Checkpoints](#-automated-testing--sih-verification-checkpoints)
16. [Security, Defense-in-Depth & Legal Boundary Disclaimers](#-security-defense-in-depth--legal-boundary-disclaimers)
17. [Team & Acknowledgments](#-team--acknowledgments)

---

## 🎯 Executive Overview

**TRACE-X** is an explainable, multi-modal Cyber Threat Intelligence (CTI) platform engineered to correlate dark-web operational personas, cryptocurrency UTXO flows, infrastructure fingerprints, linguistic stylometry, and behavioral dormancy patterns. It transforms disparate darknet artifacts into mathematically transparent, evidence-backed attribution assessments for analyst decision support while systematically preventing AI hallucinations and false-positive attributions.

Traditional threat attribution tools typically rely on naive similarity heuristics or opaque black-box neural networks that conflate financial obfuscation with innocence or mistake coincidental linguistic patterns for definitive operational overlap. **TRACE-X introduces a Two-Level Contradiction Fusion Model** with channel-specific dampening and global hard gates, accompanied by an append-only SHA-256 cryptographic audit chain and pure database-reconstructed forensic dossiers.

---

## 💡 Key Differentiators & Innovations

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 6 CORE DIFFERENTIATORS                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Two-Level Contradiction Fusion Model                                                │
│    • Level 1: Channel-Specific Dampening (CoinJoin affects only Financial: 0.60x).     │
│    • Level 2: Global Hard Gate (Temporal Concurrency overrides to INCONCLUSIVE).       │
│                                                                                        │
│ 2. Cross-Phase Numerical Reproducibility (Decision #12)                                │
│    • Preserves calculated S_base identically across Pipeline, DB, REST, and Dossiers.  │
│    • Benchmark Case 1 converges to LIKELY_LINK (HIGH); Case 2 overrides to INCONCLUSIVE│
│                                                                                        │
│ 3. 4-Factor Source Reliability Engine (Decision #10)                                   │
│    • R = 0.40*Reputation + 0.30*Freshness + 0.20*Corroboration + 0.10*Consistency.     │
│    • Modulates evidence into [0.50, 1.00] channel factor: 0.50 + 0.50*R.               │
│                                                                                        │
│ 4. Strict Stylometric Statistical Guardrail                                            │
│    • Enforces minimum 150 words AND 500 tokenizer tokens per comparison corpus.        │
│    • Yields NOT_ENOUGH_EVIDENCE to strictly separate missing data from true divergence.│
│                                                                                        │
│ 5. Cryptographically Hash-Chained Audit Trail (Genesis to Terminal)                   │
│    • Immutable SHA-256 event chaining (E_1 -> E_2 -> ... -> E_n) with JWT identities. │
│    • Sensitivity Tuner enforces Preview (audit-neutral) vs. Commit (immutable event).  │
│                                                                                        │
│ 6. Publication-Grade Forensic Dossiers (Decision #11)                                  │
│    • 100% reconstructed from persisted SQLite state; zero live re-runs during export. │
│    • Formatted in publication PDF (numbered canvas), structured CSV, and signed JSON.  │
│    • Prominently displays: "REAL-WORLD IDENTITY: NOT ESTABLISHED".                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Backend Framework**: Python 3.11+ / FastAPI 0.110 / Uvicorn (ASGI)
- **Data Modeling & Validation**: Pydantic v2 / Pydantic Settings
- **Relational Storage**: SQLite 3 (WAL Mode, synchronous=NORMAL, 10s busy timeout) via SQLAlchemy 2.0
- **Graph Database**: Neo4j 5.18 Community (Cypher queries, APOC, Graph Data Science) + NetworkX local fallback
- **Analytical & ML Libraries**: `sentence-transformers` (`all-mpnet-base-v2`, 768-dim), NumPy, scikit-learn
- **Reporting & Dossiers**: ReportLab 4.0+ (Custom `NumberedCanvas`), `pypdf` 4.0+ (text extraction verification)
- **Frontend UI**: React 18.2, TypeScript 5.2, Vite 5.4, Tailwind CSS 3.4, Lucide React
- **Visualizers**: Cytoscape.js 3.28 (Hardware-accelerated graph with force-directed physics), Recharts 2.12
- **Reverse Proxy & Gateway**: Nginx Alpine (`client_max_body_size 10M;`, unbuffered SSE streaming)
- **Containerization**: Docker Compose v2 with named persistent volumes and healthchecks

---

## 📋 Prerequisites

Before running TRACE-X locally, ensure the following software is installed:

- **Docker & Docker Compose** (Recommended): Docker Desktop 4.28+ (Docker Engine 25+)
- **Python** (for standalone backend): Python 3.11 or Python 3.12+ (tested on Python 3.14)
- **Node.js** (for standalone frontend): Node.js 20 LTS or higher (`npm` 10+)
- **C Compiler / Build Tools** (optional, for native wheels): `gcc` / Visual Studio Build Tools

---

## ⚡ Getting Started

### Option 1: Production Multi-Container Stack (Docker Compose)

The fastest and most robust way to run TRACE-X is via the multi-container Docker Compose configuration:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/TRACE-X.git
cd TRACE-X

# 2. Start the stack (Backend, Frontend, Neo4j, Persistent Volumes)
docker compose up --build -d

# 3. Verify that all services pass healthchecks
docker compose ps
```

#### Access Points:
- 🖥️ **Analyst Command Center**: [http://localhost:5173](http://localhost:5173) (Proxied via Nginx)
- 📚 **FastAPI OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🗄️ **Neo4j Cypher Browser**: [http://localhost:7474](http://localhost:7474) (`neo4j` / `DEV_NEO4J_PASSWORD_SIH26151`)
- 🩺 **Container Healthchecks**:
  - Backend: `http://localhost:8000/health`
  - Frontend: `http://localhost:5173/healthz`

#### Pre-Configured Analyst Credentials:
| Username | Password | Assigned Role | Permissions |
| :--- | :--- | :--- | :--- |
| `analyst` | `tracex2026` | `CTI_ANALYST` | Ingestion, analysis, sensitivity preview/commit, dossier export |
| `lead_auditor` | `auditor2026` | `LEAD_AUDITOR` | Global case access, restricted case evaluation, audit export |

---

### Option 2: Standalone Local Development

If you prefer running services directly on the host machine:

#### 1. Backend Service
```bash
# Navigate to backend directory
cd backend

# Install dependencies
python -m pip install -r requirements.txt

# Start Uvicorn API server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Application
```bash
# Navigate to frontend directory in a separate terminal
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🏗️ System Architecture

### Directory Structure

```text
TRACE-X/
├── docker-compose.yml              # Multi-container orchestration (Backend, Frontend, Neo4j)
├── README.md                       # Comprehensive system documentation
├── scripts/
│   └── verify_sih_submission.py    # 10-checkpoint automated SIH acceptance runner
├── backend/
│   ├── Dockerfile                  # Python 3.11-slim container with healthcheck
│   ├── requirements.txt            # Locked Python runtime dependencies
│   ├── pytest.ini                  # Pytest configuration & warning filters
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory & middleware
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic BaseSettings & production secret validation
│   │   │   └── security.py         # JWT generation, bcrypt verification & RBAC decorators
│   │   ├── models/
│   │   │   ├── database.py         # SQLAlchemy models (SQLite WAL pragmas & indexes)
│   │   │   ├── contracts.py        # Pydantic v2 immutable contracts & domain enums
│   │   │   └── schemas.py          # REST & SSE request/response schemas
│   │   ├── services/
│   │   │   ├── audit_chain.py      # Append-only SHA-256 audit ledger service
│   │   │   ├── fusion_engine.py    # Two-Level Contradiction Fusion & Hard Gate logic
│   │   │   ├── graph_engine.py     # Neo4j Cypher client with NetworkX local fallback
│   │   │   ├── ingestion_service.py# SHA-256 provenance hashing & entity extraction
│   │   │   ├── normalization_service.py # Canonical JSON sorting & RFC 3339 normalization
│   │   │   ├── report_service.py   # Publication PDF, CSV, and signed JSON dossier generator
│   │   │   ├── source_reliability_service.py # Decision #10 4-factor scoring & trust tiers
│   │   │   ├── sse_ticket_service.py # Ephemeral one-time ticket lifecycle service
│   │   │   ├── collectors/         # Benchmark & Manual upload collectors
│   │   │   └── engines/            # Canonical isolated analytical engines:
│   │   │       ├── cryptographic_engine.py # PGP key cross-certification & reuse
│   │   │       ├── financial_engine.py     # CIOH clustering & CoinJoin 0.60x dampener
│   │   │       ├── stylometric_engine.py   # NLP embeddings & >=150w/>=500t guardrail
│   │   │       ├── infrastructure_engine.py# Passive TLS & SSH fingerprinting
│   │   │       └── temporal_engine.py      # Cadence analysis & concurrency clash check
│   │   ├── api/endpoints/
│   │   │   ├── auth.py             # JWT issuance & ephemeral SSE ticket dispatch
│   │   │   ├── ingestion.py        # 10MB upload boundary, zip validator & benchmark loader
│   │   │   ├── pipeline.py         # Unbuffered SSE pipeline streaming & execution
│   │   │   ├── attribution.py      # Assessment retrieval, preview & weight commit
│   │   │   ├── reliability.py      # Source reliability evaluation & query endpoints
│   │   │   ├── graph.py            # Cytoscape property graph serialization & metrics
│   │   │   ├── reports.py          # Publication PDF, CSV, and JSON dossier downloads
│   │   │   └── audit.py            # Audit ledger verification & JSON export
│   │   └── data/
│   │       ├── benchmark_case_1.json # Frozen Case 1: Multi-Modal Convergence
│   │       └── benchmark_case_2.json # Frozen Case 2: Anti-False-Positive Contradiction
│   └── tests/                      # 17 test modules (95 committed pytest cases)
└── frontend/
    ├── Dockerfile                  # Multi-stage build (Node 20 Alpine -> Nginx Alpine)
    ├── nginx.conf                  # Nginx reverse proxy, 10MB limit & unbuffered SSE
    ├── package.json                # Frontend package dependencies & scripts
    ├── tsconfig.json               # TypeScript strict compilation options
    └── src/
        ├── App.tsx                 # Command Center shell, investigation state & SSE listener
        ├── types/index.ts          # Frontend domain types & contract mirrors
        ├── services/api.ts         # Axios client with JWT auto-injection & SSE tickets
        └── components/
            ├── Header.tsx          # Top navigation, benchmark switcher & export split-button
            ├── attribution/
            │   ├── AttributionCard.tsx # Fused score, confidence band & rationale
            │   ├── WhyNotLinkedCard.tsx# Hard gate refusal explanations (Case 2)
            │   ├── CoinJoinBanner.tsx  # Level 1 financial dampening indicator (Case 1)
            │   └── SensitivityTuner.tsx# Preview vs. Commit weight calibration
            ├── visualizers/
            │   ├── VisualizerContainer.tsx # Tabbed visualizer manager
            │   ├── GraphCanvas.tsx     # Cytoscape.js interactive threat graph
            │   ├── FinancialFlow.tsx   # UTXO peeling chain & VASP resolution tracker
            │   ├── TemporalMatrix.tsx  # Cadence matrix & concurrency clash timeline
            │   └── SourcesPanel.tsx    # Decision #10 Source Reliability breakdown
            ├── drawer/
            │   └── EvidenceDrawer.tsx  # Bidirectional graph-synchronized evidence inspector
            └── audit/
                └── AuditChainModal.tsx # Cryptographic ledger inspector & hash verifier
```

---

### Request & Ingestion Lifecycle

```
[ Evidence Package / Zip ]
             │ (POST multipart/form-data)
             ▼
[ Nginx Gateway (10 MB Boundary) ] ── (Exceeds 10 MB) ──► HTTP 413 (Rejected at Gateway)
             │
             ▼
[ FastAPI Ingestion Controller ]
  ├── 1. Size & Archive Verification (Max 50 entries, Max 25 MB uncompressed)
  ├── 2. Safe Extraction (Zip-Slip directory traversal rejection)
  ├── 3. Canonical SHA-256 Hashing of Artifact Payloads
  ├── 4. Deterministic Entity Extraction (PGP Fingerprints, Wallets, IPs, Hashes)
  └── 5. Idempotent SQLite Persistence (Composite Primary Key: investigation_id + evidence_id)
```

---

### Data Flow Architecture

```
                                  [ Authenticated Analyst ]
                                              │
                                              ▼
                                   [ POST /auth/sse-ticket ]
                                              │
                                              ▼
                                 [ Ephemeral Single-Use Ticket ]
                                              │
                                              ▼
                                [ EventSource Stream Connection ]
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
         [ Live SSE Progress Events ]                          [ Engine Execution ]
         (Stage 1..6 ~ 1.2s total)                             - Stylometry (MPNet / 64-dim)
                    │                                          - Blockchain (CIOH / CoinJoin)
                    │                                          - Graph & Infrastructure
                    │                                          - Behavioral Cadence
                    │                                                   │
                    │                                                   ▼
                    │                                   [ Two-Level Fusion Engine ]
                    │                                   - Level 1 Dampening (0.60x)
                    │                                   - Level 2 Hard Gate Check
                    │                                                   │
                    ▼                                                   ▼
         [ Attribution Determination ] ◄──────────────────── [ Persist Assessment ]
                    │                                                   │
                    ▼                                                   ▼
         [ Cytoscape Graph Render ]                              [ Append Audit Event ]
         [ Evidence Radar Render  ]                             (Linked to Hash Chain)
```

---

### Relational & Graph Database Schemas

#### SQLite Relational Tables (`backend/app/models/database.py`)
- **`investigations`**: `id` (PK), `title`, `target_persona_a`, `target_persona_b`, `status`, `assigned_analyst_id`, `classification`, `created_at`.
- **`evidence_records`**: `evidence_id` (Composite PK), `investigation_id` (Composite PK), `source_uri`, `artifact_type`, `collected_at`, `content_hash` (Indexed SHA-256), `raw_payload`, `extractor_version`, `provenance_chain`.
- **`extracted_entities`**: `entity_id` (PK), `investigation_id`, `evidence_id`, `entity_type`, `value` (Indexed), `confidence`, `created_at`.
- **`source_reliabilities`**: `id` (PK), `investigation_id`, `source_uri`, `trust_tier`, `reliability_score` ($R$), `reliability_class`, `reputation`, `freshness`, `corroboration`, `consistency`, `last_scan`, `scan_status`, `diagnostic_status`.
- **`attribution_assessments`**: `assessment_id` (PK), `investigation_id`, `attribution_state`, `confidence_band`, `base_score`, `evidence_score`, `real_world_identity`, `is_current` (Boolean Flag), `payload` (Full JSON contract snapshot).
- **`audit_events`**: `audit_id` (PK), `investigation_id`, `assessment_id`, `action`, `analyst_id`, `timestamp`, `rationale`, `prior_state`, `resulting_state`, `previous_hash` (SHA-256 link), `event_hash` (SHA-256 root).

#### Neo4j Property Graph Nodes & Relationships (`backend/app/services/graph_engine.py`)
- **Nodes**: `:Persona`, `:PGPKey`, `:WalletAddress`, `:VASP`, `:ForumPost`, `:ServerInfrastructure`.
- **Relationships**:
  - `(:Persona)-[:USES_KEY]->(:PGPKey)`
  - `(:Persona)-[:CONTROLS_WALLET]->(:WalletAddress)`
  - `(:WalletAddress)-[:TRANSFERRED_TO {hops: 2, coinjoin: true}]->(:VASP)`
  - `(:Persona)-[:POSTED_MESSAGE]->(:ForumPost)`
  - `(:Persona)-[:HOSTED_ON]->(:ServerInfrastructure)`
  - `(:Persona)-[:LIKELY_SAME_AS {base_score: 0.7532, state: 'LIKELY_LINK'}]->(:Persona)`

---

## 📐 Mathematical Attribution & Fusion Framework

### 1. Normalized Weighting Constraint
TRACE-X evaluates attribution across five canonical dimensions whose configured weights are mathematically guaranteed to sum to unity:
$$\sum_{i=1}^{5} w_i = 1.0 \quad (w_{\text{crypto}}=0.30,\; w_{\text{financial}}=0.25,\; w_{\text{stylometric}}=0.20,\; w_{\text{infra}}=0.15,\; w_{\text{behavior}}=0.10)$$

### 2. Level 1: Channel-Specific Reliability Dampening
When obfuscation technologies (such as CoinJoin or Samourai Whirlpool mixing) are detected, TRACE-X dampens **only** the affected channel's reliability factor ($R_{\text{financial}} = 0.60$), leaving independent cryptographic and linguistic vectors completely untainted:
$$s'_{\text{financial}} = s_{\text{raw}, \text{financial}} \times R_{\text{financial}} = 0.90 \times 0.60 = 0.5400$$

### 3. Decision #10: 4-Factor Source Reliability Engine
Evidence sources are scored transparently via four constituent factors:
$$R = 0.40 \cdot R_{\text{reputation}} + 0.30 \cdot R_{\text{freshness}} + 0.20 \cdot R_{\text{corroboration}} + 0.10 \cdot R_{\text{consistency}}$$

The resulting reliability score modulates evidence raw scores via the canonical channel modifier formula:
$$\text{Channel Modifier} = 0.50 + 0.50 \cdot R \in [0.50, 1.00]$$
$$s'_i = s_{\text{raw}, i} \cdot (0.50 + 0.50 \cdot R)$$

> **Mathematical Invariant**: Source unreliability cannot reduce a valid, corroborating evidence signal below 50% of its raw strength.

### 4. Base Fused Score Formulation
The baseline attribution score $S_{\text{base}}$ is calculated as the dot product of weights and adjusted signal scores:
$$S_{\text{base}} = \sum_{i=1}^{5} w_i \cdot s'_i$$

### 5. Level 2: Global Contradiction Hard Gate
When mutually exclusive operational realities are proven (such as simultaneous authenticated activity across geographically conflicting nodes within a 30-second window), Level 2 hard gating immediately triggers:
$$\text{If } \exists \, c \in C_{\text{global}} \text{ where } c.\text{is\_hard\_gate} = \text{True} \implies \begin{cases} \text{AttributionState} = \mathbf{INCONCLUSIVE} \\ \text{ConfidenceBand} = \mathbf{LOW} \\ S_{\text{base}} = \text{Preserved without artificial zeroing} \end{cases}$$

### 6. Confidence Band Calibration & State Mapping
| Attribution State | Score Range ($S_{\text{base}}$) | Confidence Band | Operational Interpretation |
| :--- | :---: | :---: | :--- |
| **CONFIRMED_LINK** | $[0.85, 1.00]$ | **VERY_HIGH** | Overwhelming convergence across multiple independent primary vectors. |
| **LIKELY_LINK** | $[0.70, 0.8499]$ | **HIGH** | Strong multi-modal convergence; minimal alternative explanations. |
| **POSSIBLE_LINK** | $[0.50, 0.6999]$ | **MEDIUM** | Moderate indicators observed; alternative operational hypotheses plausible. |
| **UNLIKELY_LINK** | $[0.30, 0.4999]$ | **LOW** | Low correlation; evidence suggests disparate actors or coincidence. |
| **NO_LINK_FOUND** | $[0.00, 0.2999]$ | **VERY_LOW** | Negligible correlation; no corroborating indicators observed. |
| **INCONCLUSIVE** | Preserved | **LOW** | Forced by Level 2 Hard Gate (e.g. `TEMPORAL_CONCURRENCY_CLASH`). |

---

## 🔬 Analytical Engines Breakdown

### 1. 🤖 AI Stylometry & NLP Engine (`StylometricEngine`)
- **Transformer Vectorization**: Embeds communication samples using `sentence-transformers/all-mpnet-base-v2` (768 dimensions).
- **Statistical Fallback**: Features a deterministic 64-dimension L2-normalized character tri-gram projection for offline/low-resource execution.
- **Evidentiary Guardrail**: Enforces a strict minimum of **150 whitespace-delimited words** AND **500 tokenizer tokens** per persona corpus. Returns `NOT_ENOUGH_EVIDENCE` if either threshold fails, preventing hallucinated linguistic matches.

### 2. ⛓️ Blockchain Forensics Engine (`FinancialEngine`)
- **UTXO Clustering**: Implements Common Input Ownership Heuristics (CIOH) to link multi-input spending transactions.
- **Peeling Chain Parser**: Follows change outputs hop-by-hop until reaching regulated VASP deposit addresses (e.g., Kraken Exchange).
- **Deterministic CoinJoin Dampener**: Detects collaborative multi-party transactions (Standard CoinJoin, Samourai Whirlpool) and applies a deterministic $0.60\times$ channel dampener to financial reliability.

### 3. 🕸️ Cryptographic & Infrastructure Engines (`CryptographicEngine`, `InfrastructureEngine`)
- **PGP Key Cross-Certification**: Parses OpenPGP key fingerprints, subkey bindings, and web-of-trust signatures. Flags shared primary keys (`PRIMARY_KEY_REUSE`) as very high confidence indicators.
- **Passive Infrastructure Fingerprinting**: Evaluates TLS certificate serial numbers and SSH server daemon fingerprints. Strictly adheres to passive observational metadata without inferring physical operator geography from Tor exit nodes.

### 4. ⏱️ Behavioral & Temporal Engine (`TemporalEngine`)
- **Sequential Cadence**: Tracks diurnal activity profiles and verifies operational vendor dormancy (e.g., Persona A ceasing forum activity before Persona B emerges).
- **Temporal Concurrency Clash**: Flags authenticated actions occurring within conflicting geographic networks inside 30 seconds as operational contradictions triggering the Level 2 Hard Gate.

---

## 🧪 Benchmark Evaluation Scenarios

TRACE-X includes two frozen benchmark scenarios locked to Phase 0 SHA-256 cryptographic anchors:

```
+-----------------------------------------------------------------------------------------------------------------+
|                                           TRACE-X BENCHMARK VALIDATION MATRIX                                   |
+------------------------------------+------------------------------------------+---------------------------------+
| Scenario                           | Ingested Evidence Artifacts              | Engine Determination & Action   |
+------------------------------------+------------------------------------------+---------------------------------+
| Case 1: Operation GhostSpecter     | • EV-001-PGP: Primary RSA-4096 (0x9B8A7C)| State: LIKELY_LINK              |
| (Multi-Modal Convergence)          | • EV-002-PGP-USE: Exact Key reuse        | Confidence Band: HIGH           |
|                                    | • EV-003-POSTS-A: Dread post (180 words) | Base Score (S_base): ~0.7532    |
|                                    | • EV-004-POSTS-B: Exploit post (180 words| Level 1 Dampening Applied:      |
|                                    | • EV-005-BTC-TX: Peeling chain to Kraken | CoinJoin dampens financial from |
|                                    | • EV-006-INFRA: Shared TLS cert & SSH    | 0.90 to 0.54. Multi-modal       |
|                                    |                                          | evidence cleanly converges.     |
+------------------------------------+------------------------------------------+---------------------------------+
| Case 2: Operation DeceptiveClone   | • EV-101-PGP-SHADOW: ED25519 Key         | State: INCONCLUSIVE             |
| (Anti-False-Positive Hard Gate)    | • EV-102-PGP-PHANTOM: RSA-4096 Key       | Confidence Band: LOW            |
|                                    | • EV-103-POSTS-SHADOW: 168 words         | Base Score (S_base): Preserved  |
|                                    | • EV-104-POSTS-PHANTOM: 169 words        | Level 2 Hard Gate Triggered:    |
|                                    | • EV-105-BTC-MIXING: Samourai Whirlpool  | TEMPORAL_CONCURRENCY_CLASH      |
|                                    | • EV-106-TEMPORAL-CLASH: 30s concurrent  | (Frankfurt vs Singapore nodes)  |
|                                    |   admin actions in Frankfurt & Singapore | Overrides fused score to        |
|                                    |                                          | prevent false-positive link.    |
+------------------------------------+------------------------------------------+---------------------------------+
```

---

## 📑 Publication-Grade Forensic Reporting Dossier (Decision #11)

TRACE-X features an automated reporting subsystem that reconstructs publication-grade investigation dossiers purely from persisted database state:

### Supported Export Formats
1. **Publication PDF Dossier (`/api/v1/reports/{id}/pdf`)**:
   - Built using ReportLab with a two-pass `NumberedCanvas` ("Page X of Y").
   - Official running header with NTRO evidentiary banner.
   - Prominent red identity disclaimer: `REAL-WORLD IDENTITY: NOT ESTABLISHED`.
   - Comprehensive investigation overview, radar breakdown table, and Level 2 hard gate alert box.
   - Decision #10 Source Reliability breakdown and ML model provenance metadata.
   - Complete chronological cryptographic audit ledger trail.
2. **Tabular CSV Export (`/api/v1/reports/{id}/csv`)**:
   - Structured multi-section CSV with fixed headers and sorted rows for spreadsheet analysis.
3. **Canonical JSON Dossier (`/api/v1/reports/{id}/json`)**:
   - Deterministic SHA-256 `report_hash` computed over canonicalized fields with sorted keys and compact separators.
   - Tamper-evident proof linking terminal audit hashes.

---

## 🖥️ Interactive Command Center & UI Workspace

The React frontend delivers a modern, high-contrast Dark Cyber CTI interface:

1. **Top Command Center Header**:
   - 1-Click Benchmark Loaders for Case 1 (Convergence) and Case 2 (Contradiction).
   - Case Selector dropdown (`INV-SIH-001`, `INV-SIH-002`, or custom uploads).
   - Multi-Format Export Split-Button (Instant PDF, CSV, and JSON download).
   - Real-time pipeline trigger button with live progress spinner.
2. **Attribution & Refusal Display**:
   - `AttributionCard`: Displays state badges, confidence gauges, and fused scores.
   - `WhyNotLinkedCard`: In Case 2, details the specific Level 2 hard gate rule, contradiction observation, and explains why correlation was refused.
   - `CoinJoinBanner`: In Case 1, highlights Level 1 channel dampening without alarming the analyst.
3. **Interactive Sensitivity Tuner**:
   - Dual-Mode Tuning: **Preview Mode** performs recalculations completely audit-neutral; **Commit Mode** appends an immutable SHA-256 event to the audit ledger.
4. **Tabbed Visualizer Workspace**:
   - **Threat Graph (Cytoscape.js)**: Hardware-accelerated property graph with category filters, degree centrality metrics, and bidirectional synchronization with the Evidence Drawer.
   - **Financial Flow**: Visual peeling chain following UTXO hops to Kraken Exchange.
   - **Temporal Cadence Matrix**: Activity heatmap and concurrency clash timeline.
   - **Sources Panel**: Decision #10 Source Reliability cards displaying trust tiers, $R$ scores, and factor breakdowns.

---

## 🔌 REST API Reference & SSE Streaming Contracts

FastAPI provides an interactive OpenAPI / Swagger specification at `/docs`.

### Core API Endpoints

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | Healthcheck returning identity scope and version |
| **System** | `GET` | `/healthz` | Nginx reverse proxy health check |
| **Auth** | `POST` | `/api/v1/auth/token` | Issues bcrypt-authenticated JWT access tokens |
| **Auth** | `GET` | `/api/v1/auth/me` | Returns current user profile and role |
| **Auth** | `POST` | `/api/v1/auth/sse-ticket` | Issues ephemeral, single-use ticket for SSE streaming |
| **Ingestion**| `POST` | `/api/v1/ingestion/benchmark/{case_id}` | 1-Click loader for Case 1 (`1`) or Case 2 (`2`) |
| **Ingestion**| `GET` | `/api/v1/ingestion/{id}/artifacts` | Returns all ingested evidence records for a case |
| **Ingestion**| `GET` | `/api/v1/ingestion/{id}/entities` | Returns extracted technical indicators for a case |
| **Ingestion**| `POST` | `/api/v1/ingestion/upload` | Ingests JSON evidence packages with SHA-256 hashing |
| **Ingestion**| `POST` | `/api/v1/ingestion/upload-file` | Multipart upload for `.json` and `.zip` archives (10 MB limit) |
| **Pipeline** | `GET` | `/api/v1/pipeline/stream/{id}` | Real-time SSE stream of 6-stage analytical pipeline |
| **Attribution**| `GET`| `/api/v1/attribution/{id}` | Retrieves latest attribution assessment |
| **Attribution**| `POST`| `/api/v1/attribution/recalculate` | Audit-neutral sensitivity recalculation preview |
| **Attribution**| `POST`| `/api/v1/attribution/commit-weights` | Commits tuned weights and logs immutable audit event |
| **Reliability**| `POST`| `/api/v1/reliability/evaluate` | Evaluates single source URI via Decision #10 |
| **Reliability**| `GET` | `/api/v1/reliability/{id}/sources` | Returns all evaluated source reliabilities for a case |
| **Graph** | `GET` | `/api/v1/graph/{id}` | Returns Cytoscape graph nodes and relationship edges |
| **Graph** | `GET` | `/api/v1/graph/{id}/metrics` | Returns topological metrics (density, central nodes) |
| **Reports** | `GET` | `/api/v1/reports/{id}/pdf` | Generates publication-grade PDF investigation dossier |
| **Reports** | `GET` | `/api/v1/reports/{id}/csv` | Generates structured tabular CSV dossier |
| **Reports** | `GET` | `/api/v1/reports/{id}/json` | Generates canonical JSON dossier with `report_hash` |
| **Audit** | `GET` | `/api/v1/audit/export/{id}` | Returns cryptographically verified audit ledger trail |

---

## ⚙️ Environment Variables Reference

Configure environment variables in `.env` or pass them directly to Docker Compose:

| Variable | Description | Default (Development) | Production Rule |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment environment mode | `development` | Set to `production` |
| `DATABASE_URL` | SQLAlchemy database connection URI | `sqlite:///./tracex.db` | `sqlite:////app/data/tracex.db` (Named Volume) |
| `SECRET_KEY` | JWT signing secret key | `DEV_SECRET_KEY_FOR_LOCAL_SIH_...` | **Required**: Minimum 32 chars, cannot start with `DEV_` |
| `NEO4J_URI` | Neo4j Bolt protocol endpoint | `bolt://localhost:7687` | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j administrative username | `neo4j` | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j administrative password | `DEV_NEO4J_PASSWORD_SIH26151` | **Required**: Secure password, cannot start with `DEV_` |
| `ENABLE_REAL_TRANSFORMER` | Toggle local MPNet transformer | `true` | `true` (Falls back cleanly to 64-dim L2 offline) |

---

## 📜 Available Scripts & Quality Verification Commands

| Command | Working Directory | Description |
| :--- | :--- | :--- |
| `python scripts/verify_sih_submission.py` | Root | Runs the 10-checkpoint SIH acceptance verification suite |
| `python -m pytest tests/ -v` | `backend/` | Runs all 95 committed unit and integration tests |
| `npm run build` | `frontend/` | Compiles TypeScript and builds production Vite bundle |
| `npm run dev` | `frontend/` | Starts local frontend development server |
| `docker compose up --build -d` | Root | Builds and launches all container services |
| `docker compose ps` | Root | Inspects container status and healthcheck states |
| `docker compose down -v` | Root | Shuts down containers and tears down volumes |

---

## 🧪 Automated Testing & SIH Verification Checkpoints

### 1. The 10 TRACE-X Acceptance Checkpoints (`scripts/verify_sih_submission.py`)
Run the automated standalone verification runner:
```bash
python scripts/verify_sih_submission.py
```

Expected Output:
```text
========================================================================================
TRACE-X SIH ACCEPTANCE VERIFICATION RUNNER
Standard: NTRO SIH26151 Evidentiary Framework  |  Mode: Decision Support System
========================================================================================
[01] RBAC & Authentication (ANALYST / AUDITOR / 401)  PASS  ( 0.22s)
     --> Enforced bcrypt JWT credentials & role authorization matrix
[02] Secure Evidence Ingestion (10MB / Anti-Zip-Bomb) PASS  ( 0.03s)
     --> Enforced 10MB input limit, 50 entries, 25MB uncompressed limit
[03] Entity Extraction & Investigation Isolation      PASS  ( 0.00s)
     --> Extracted 6 indicators with strict investigation-scoping
[04] Source Reliability Engine (Decision #10)         PASS  ( 0.01s)
     --> 4-factor formula validated with [0.50, 1.00] channel modulation
[05] Analytical Engines & Guardrails (Stylometry/CoinJoin) PASS  ( 0.00s)
     --> Enforced >=150w/500t boundary matrix & 0.60x CoinJoin dampening
[06] Case 1 Convergence & Numerical Consistency       PASS  ( 5.23s)
     --> Authoritative S_base=0.7532 (LIKELY_LINK) verified across Pipeline/DB/API/Report
[07] Case 2 Contradiction Gate & Score Preservation   PASS  ( 0.06s)
     --> Level 2 Hard Gate enforced INCONCLUSIVE while preserving authoritative S_base=0.2150
[08] Sensitivity Tuning (Preview vs. Commit Isolation) PASS  ( 0.02s)
     --> Preview is 100% audit-neutral; Commit appends immutable SHA-256 event
[09] Cryptographic Audit Chain Verification           PASS  ( 0.00s)
     --> Verified 5 events from genesis '0'*64 through terminal hash
[10] Dossier Reconstruction & Cross-Phase Consistency PASS  ( 0.08s)
     --> Pure DB reconstruction verified across PDF, CSV, and canonical JSON
========================================================================================
VERIFICATION RESULT: 10/10 CHECKPOINTS PASSED (Total: 5.64s)
STATUS: ALL SIH26151 ACCEPTANCE CRITERIA SATISFIED
========================================================================================
```

### 2. Full Pytest Backend Test Suite
```bash
cd backend
python -m pytest tests/ -v
```
All **95 tests pass** across 17 test modules in under 16 seconds with **zero failures** and **zero warnings**.

---

## 🔒 Security, Defense-in-Depth & Legal Boundary Disclaimers

### 1. Earliest-Layer Input Security Boundary
- Nginx strictly enforces `client_max_body_size 10M;`. Requests exceeding 10 MB are rejected at the edge gateway before allocating application worker threads.
- Archive extraction limits zip expansion to 50 files and 25 MB uncompressed, while blocking absolute paths and `../` directory traversals.

### 2. Append-Only Cryptographic Audit Ledger
- Every critical human and system action is signed into a linear hash chain ($E_1 \to E_2 \to \dots \to E_n$) anchored to genesis `'0'*64`.
- Audit logs cannot be modified or reordered without corrupting subsequent hashes.

### 3. Permanent Legal Identity Scope Guardrail
- **TRACE-X is an investigative decision-support system, not an automated judicial sentencing engine.**
- Every interface, REST response, CSV export, and PDF dossier prominently bears the mandatory notice:
  > **`REAL-WORLD IDENTITY: NOT ESTABLISHED`**  
  > *Real-world identity attribution requires appropriate authorized investigative and legal processes outside TRACE-X.*
- Network exit node geography (Tor / proxy infrastructure) is strictly separated from physical operator location.

---

## 👥 Team & Acknowledgments

- **Problem Statement**: SIH26151 — Threat Actor Persona De-Anonymization & Attribution
- **Agency**: National Technical Research Organisation (NTRO)
- **Competition**: Smart India Hackathon (SIH) 2026
- **Category**: Cybersecurity, Blockchain Intelligence & Multi-Modal CTI

---

*Engineered with mathematical rigor, transparent explainability, and zero false-positive tolerance for intelligence analysts and national cyber defense.*
