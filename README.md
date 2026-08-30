# 🛡️ TRACE-X: Threat Relationship & Attribution Correlation Engine
### Next-Generation Explainable Cyber Threat Intelligence (CTI) & Multi-Modal Attribution Platform
**Problem Statement SIH26151 | National Technical Research Organisation (NTRO) | Smart India Hackathon 2026**

---

[![CI Tests](https://img.shields.io/badge/Tests-19%2F19%20Passed-emerald?style=flat-square&logo=pytest)](https://pytest.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com)
[![Cytoscape.js](https://img.shields.io/badge/Cytoscape.js-3.28-orange?style=flat-square)](https://js.cytoscape.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.18-008CC1?style=flat-square&logo=neo4j)](https://neo4j.com)
[![Docker](https://img.shields.io/badge/Docker-Compose%20v2-2496ED?style=flat-square&logo=docker)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [Core Innovations for SIH26151](#-core-innovations-for-sih26151)
- [System Architecture](#-system-architecture)
- [Mathematical Attribution Framework](#-mathematical-attribution-framework)
- [Analytical Engines Breakdown](#-analytical-engines-breakdown)
- [Benchmark Evaluation Scenarios](#-benchmark-evaluation-scenarios)
- [Interactive Visualizers & UI Features](#-interactive-visualizers--ui-features)
- [API Reference & SSE Contracts](#-api-reference--sse-contracts)
- [Quick Start Guide (Docker & Standalone)](#-quick-start-guide)
- [Automated Testing & Quality Gates](#-automated-testing--quality-gates)
- [Repository Structure](#-repository-structure)
- [Security, Privacy & Legal Scope](#-security-privacy--legal-scope)
- [Team & Acknowledgments](#-team--acknowledgments)

---

## 🎯 Executive Overview

**TRACE-X** is an explainable, multi-modal Cyber Threat Intelligence (CTI) platform engineered to correlate dark-web operational personas, cryptocurrency flows, infrastructure fingerprints, linguistic stylometry, and behavioral dormancy patterns. It transforms disparate darknet artifacts into explainable, evidence-backed attribution assessments for analyst decision support while preventing artificial intelligence hallucinations and false-positive attributions.

Traditional attribution tools often rely on naive similarity heuristics or black-box neural aggregations that conflate financial obfuscation with innocence or treat coincidence as definitive proof. **TRACE-X introduces a Two-Level Contradiction Fusion Model** with channel-specific dampening and global hard gates, ensuring that threat intelligence analysts receive auditable, structured evidence dossiers.

---

## 💡 Core Innovations for SIH26151

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            5 CORE DIFFERENTIATORS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Two-Level Contradiction Fusion Model                                     │
│    • Level 1: Channel-Specific Dampening (CoinJoin affects only Financial) │
│    • Level 2: Global Hard Gate (Temporal Concurrency overrides to Inconclusive)│
│                                                                             │
│ 2. Transparent & Reproducible Mathematical Scoring                          │
│    • Sum of weighted signals equals exactly 1.0 (Case 1 Score: 0.7655)      │
│    • Real-time dynamic sensitivity tuner for analyst what-if analysis        │
│                                                                             │
│ 3. Strict Stylometric Statistical Guardrail                                 │
│    • Enforces minimum 150 words / 500 tokens before calculating embeddings   │
│    • Returns NOT_ENOUGH_EVIDENCE to separate missing data from dissimilarity│
│                                                                             │
│ 4. Append-Only Tamper-Evident SHA-256 Audit Trail                           │
│    • Human-in-the-loop decisions (CONFIRM/REJECT/INVESTIGATE) logged with   │
│      cryptographic hashes, analyst ID, and timestamp                        │
│                                                                             │
│ 5. Permanent Real-World Identity Scope Guard                                │
│    • UI/API explicitly renders "REAL-WORLD IDENTITY: NOT ESTABLISHED"       │
│    • Delineates persona correlation from lawful citizen KYC de-anonymization│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

TRACE-X follows a modular, reactive microservice-ready architecture powered by **FastAPI** (Python 3.11) on the backend and **React 18 + TypeScript + Tailwind CSS** on the frontend, with **Neo4j** for property graph persistence.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND UI LAYER                                     │
│  React 18 • TypeScript • Tailwind CSS • Lucide Icons • Cytoscape.js • Recharts Visuals │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Threat Graph (SVG)│  │ Peeling Flow (BTC)│  │  Temporal Matrix │  │ Sensitivity    │ │
│  │ Interactive Nodes │  │ VASP Hops / Whale │  │  Cadence Timeline│  │ Live Tuner    │ │
│  └───────────────────┘  └───────────────────┘  └──────────────────┘  └────────────────┘ │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ REST API + Real-Time SSE Stream (~1.2s)
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                BACKEND ORCHESTRATION                                    │
│                              FastAPI • Uvicorn • Pydantic v2                            │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         EVIDENCE INGESTION & VALIDATION                           │  │
│  │   Benchmark Case Loader • SHA-256 Content Hashing • Cross-Investigation Deduplication│  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            │                                            │
│                     ┌──────────────────────┴──────────────────────┐                     │
│                     ▼                                             ▼                     │
│     ┌──────────────────────────────┐              ┌──────────────────────────────┐      │
│     │  AI Stylometry & NLP Engine  │              │ Blockchain Forensics Engine  │      │
│     │  • MPNet Embeddings          │              │  • UTXO & Peeling Parser     │      │
│     │  • ≥150 Word Guardrail       │              │  • CoinJoin Dampener         │      │
│     └───────────────┬──────────────┘              │  • Kraken / VASP Resolution  │      │
│                     │                             └──────────────┬───────────────┘      │
│                     │       ┌────────────────────────────┐       │                      │
│                     ├──────►│ Graph Intelligence Engine  │◄──────┤                      │
│                     │       │ • Neo4j Property Graph     │       │                      │
│                     │       │ • PGP Key & Infra Fingerpr.│       │                      │
│                     │       └──────────────┬─────────────┘       │                      │
│                     │                      │                     │                      │
│                     │       ┌──────────────▼─────────────┐       │                      │
│                     ├──────►│ Behavioral/Temporal Engine │◄──────┤                      │
│                     │       │ • Sequential Dormancy      │       │                      │
│                     │       │ • Concurrency Clash Window │       │                      │
│                     │       └──────────────┬─────────────┘       │                      │
│                     │                      │                     │                      │
│                     └──────────────────────┼─────────────────────┘                      │
│                                            ▼                                            │
│                      ┌───────────────────────────────────────────┐                      │
│                      │   EVIDENCE FUSION & CONTRADICTION ENGINE  │                      │
│                      │   • Level 1: Channel Reliability Adjust   │                      │
│                      │   • Level 2: Global Hard Gate Override    │                      │
│                      │   • Exact Math: S_base = Σ (w_i * s'_i)   │                      │
│                      └─────────────────────┬─────────────────────┘                      │
│                                            │                                            │
│                                            ▼                                            │
│                      ┌───────────────────────────────────────────┐                      │
│                      │        ATTRIBUTION ASSESSMENT             │                      │
│                      │  CONFIRMED | LIKELY | POSSIBLE | INCONCL. │                      │
│                      └─────────────────────┬─────────────────────┘                      │
│                                            │                                            │
│                                            ▼                                            │
│                      ┌───────────────────────────────────────────┐                      │
│                      │    APPEND-ONLY TAMPER-EVIDENT AUDIT TRAIL │                      │
│                      │    SHA-256 Signed Human-in-the-Loop Logs  │                      │
│                      └───────────────────────────────────────────┘                      │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   STORAGE & DATA LAYER                                  │
│           SQLite / PostgreSQL (Metadata & Ingestion)  •  Neo4j (CTI Property Graph)     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📐 Mathematical Attribution Framework

### 1. Normalized Weighting Constraint
The platform enforces five canonical evidence dimensions with strictly normalized weights:
$$\sum_{i=1}^{5} w_i = 1.0 \quad (w_{\text{crypto}}=0.30,\; w_{\text{financial}}=0.25,\; w_{\text{stylometric}}=0.20,\; w_{\text{infra}}=0.15,\; w_{\text{behavior}}=0.10)$$

### 2. Level 1: Channel-Specific Reliability Dampening
When obfuscation or privacy tooling (such as Bitcoin CoinJoin or Whirlpool mixing) is detected, it dampens **only** the associated channel's reliability factor ($R_i$), rather than indiscriminately penalizing unrelated cryptographic or linguistic evidence:
$$s'_i = s_{\text{raw}, i} \times R_i$$

### 3. Base Score Formulation
$$S_{\text{base}} = \sum_{i=1}^{5} w_i \cdot s'_i = (w_{\text{crypto}} \cdot s'_{\text{crypto}}) + (w_{\text{financial}} \cdot s'_{\text{financial}}) + (w_{\text{style}} \cdot s'_{\text{style}}) + (w_{\text{infra}} \cdot s'_{\text{infra}}) + (w_{\text{behavior}} \cdot s'_{\text{behavior}})$$

### 4. Level 2: Global Contradiction Hard Gate
Global contradictions that indicate mutually exclusive operational realities (e.g. simultaneous authenticated activity geolocated to Frankfurt and Singapore within 30 seconds) trigger a **Hard Gate**:
$$\text{If } \exists \, c \in C_{\text{global}} \text{ where } c.\text{triggers\_hard\_gate} = \text{True} \implies \text{AttributionState} = \mathbf{INCONCLUSIVE}$$

### 5. Benchmark Arithmetic Verification (Case 1)
| Dimension | Raw Score ($s_i$) | Reliability ($R_i$) | Adjusted ($s'_i$) | Weight ($w_i$) | Contribution |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Cryptographic** | $0.95$ | $1.00$ | $0.95$ | $0.30$ | **$0.2850$** |
| **Financial (BTC)** | $0.90$ | $0.60$ *(CoinJoin)* | $0.54$ | $0.25$ | **$0.1350$** |
| **Stylometric** | $0.84$ | $1.00$ | $0.84$ | $0.20$ | **$0.1680$** |
| **Infrastructure** | $0.65$ | $1.00$ | $0.65$ | $0.15$ | **$0.0975$** |
| **Behavioral** | $0.80$ | $1.00$ | $0.80$ | $0.10$ | **$0.0800$** |
| **Total Fused Score** | — | — | — | **$1.00$** | $\mathbf{0.7655}$ |

**Result**: $\mathbf{0.7655} \implies$ **`LIKELY LINK`** (Confidence: **`HIGH`**).

---

## 🔬 Analytical Engines Breakdown

### 1. 🤖 AI Stylometry & NLP Engine (`app/services/stylometry_engine.py`)
- **Underlying Model**: Transformer embedding model (`sentence-transformers/all-mpnet-base-v2`).
- **Statistical Guardrail**: Enforces a minimum corpus length of **150 words** (or 500 tokens).
- **Graceful Failure**: If corpus is insufficient, returns status `NOT_ENOUGH_EVIDENCE` (score $0.0$, reliability $0.0$), explicitly differentiating between lack of evidence and true negative dissimilarity.

### 2. ⛓️ Blockchain Forensics Engine (`app/services/blockchain_engine.py`)
- **UTXO Clustering**: Implements Common Input Ownership Heuristics (CIOH) to cluster related darknet wallet addresses.
- **Peeling Chain Reconstruction**: Follows change addresses hop-by-hop until reaching deposit addresses tied to regulated Virtual Asset Service Providers (e.g. Kraken Exchange).
- **CoinJoin Detection**: Detects equal-output multi-party mixing transactions and applies a $-40\%$ channel reliability penalty.

### 3. 🕸️ Graph Intelligence Engine (`app/services/graph_engine.py`)
- **Property Graph Mapping**: Normalizes personas, PGP keys, forum posts, darknet marketplaces, and infrastructure headers into labeled nodes and directed edges.
- **Traceable Graph Edges**: Inferred attribution edges carry explicit evidence references:
  ```cypher
  (:Persona)-[:LIKELY_SAME_AS {
      fused_score: 0.7655,
      state: "LIKELY_LINK",
      assessment_id: "ASSESS-INV-SIH-001",
      evidence_ids: ["EV-001-PGP", "EV-002-PGP-USE", "EV-005-BTC-TX", "EV-006-INFRA"]
  }]->(:Persona)
  ```

### 4. ⏱️ Behavioral & Temporal Intelligence Engine (`app/services/behavioral_engine.py`)
- **Dormancy Windows**: Validates vendor migration timelines (verifying that Persona A went dormant on Forum 1 prior to Persona B emerging on Forum 2).
- **Concurrency Clash Detection**: Flags overlapping authenticated sessions within a configurable 15-minute window.

---

## 🧪 Benchmark Evaluation Scenarios

TRACE-X includes pre-loaded, standard benchmark scenarios designed for automated validation during NTRO evaluation:

```
+---------------------------------------------------------------------------------------------------------+
|                                    BENCHMARK VALIDATION MATRIX                                          |
+------------------------------------+------------------------------------+-------------------------------+
| Scenario                           | Observed Evidence                  | System Decision & Rationale   |
+------------------------------------+------------------------------------+-------------------------------+
| Case 1: GhostSpecter Migration     | • Direct PGP Key reuse (0x9B8A7C)  | State: LIKELY_LINK            |
| (Convergence & Vendor Migration)   | • Peeling chain to Kraken VASP     | Score: 0.7655                 |
|                                    | • Stylometry cosine: 0.84          | Channel Dampening:            |
|                                    | • Clean sequential migration       | CoinJoin dampens Financial    |
|                                    | • Shared TLS cert & SSH daemon     | channel to 0.54. Base score   |
|                                    |                                    | perfectly converges.          |
+------------------------------------+------------------------------------+-------------------------------+
| Case 2: Deceptive Concurrency      | • Stylometry similarity: 0.86      | State: INCONCLUSIVE           |
| (Anti-False-Positive Hard Gate)    | • Distinct, non-overlapping PGP    | Score: Overridden (0.115)     |
|                                    | • Samourai Whirlpool mixing        | Hard Gate Triggered:          |
|                                    | • Simultaneous activity in         | TEMPORAL_CONCURRENCY_CLASH    |
|                                    |   Frankfurt & Singapore (30s delta)| Safely fails closed to        |
|                                    |                                    | prevent false attribution.    |
+------------------------------------+------------------------------------+-------------------------------+
```

---

## 🖥️ Interactive Visualizers & UI Features

The frontend provides an intuitive, high-craft CTI workspace:

1. **Cyber Threat Graph (Cytoscape.js)**:
   - Custom, hardware-accelerated SVG icons for Personas, PGP Keys, Wallets, VASPs, Forums, Posts, and Infrastructure.
   - Dynamic collision avoidance (`nodeDimensionsIncludeLabels: true`, high-repulsion physics) ensuring zero label overlap.
   - Interactive filtering by evidence category (*PGP Keys, Wallets & VASP, Forums & Posts*).
2. **Bitcoin Peeling Chain Flow**:
   - Visual hop-by-hop ledger tracking tainted funds from darknet vendor reserves to exchange deposit endpoints.
3. **Temporal Activity Matrix**:
   - Visualizes operational cadences, dormancy transitions, and concurrent collision windows.
4. **Live Sensitivity Tuner Drawer**:
   - Allows investigators to interactively adjust slider weights with instant mathematical recalculation.
5. **Tamper-Evident Action Commitment**:
   - Analysts submit formal decisions with justification notes, instantly rendering a signed SHA-256 audit record.

---

## 🔌 API Reference & SSE Contracts

FastAPI delivers an interactive Swagger interface at `/docs`.

### Primary REST & Streaming Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health check and legal identity scope declaration |
| `POST` | `/api/v1/ingestion/benchmark/{case_id}` | Loads pre-configured benchmark scenario (`case_1` or `case_2`) |
| `POST` | `/api/v1/ingestion/artifacts` | Ingests custom evidence artifacts with SHA-256 provenance |
| `GET` | `/api/v1/pipeline/stream/{investigation_id}` | Real-time Server-Sent Events (SSE) stream of the 6-stage pipeline |
| `GET` | `/api/v1/attribution/{investigation_id}` | Retrieves latest fused attribution assessment |
| `POST` | `/api/v1/attribution/recalculate` | Live sensitivity weight tuning & recalculation |
| `GET` | `/api/v1/graph/{investigation_id}` | Retrieves Cytoscape graph nodes and relationship edges |
| `POST` | `/api/v1/audit/action` | Logs human-in-the-loop analyst action with SHA-256 hash |
| `GET` | `/api/v1/audit/{investigation_id}` | Retrieves append-only audit trail for an investigation |

---

## ⚡ Quick Start Guide

### Option 1: One-Command Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-org/TRACE-X.git
cd TRACE-X

# 2. Build and start all microservices in detached mode
docker compose up --build -d

# 3. Verify running containers
docker compose ps
```

**Access URLs:**
- 🖥️ **Analyst Dashboard**: [http://localhost:5173](http://localhost:5173)
- 📚 **FastAPI Swagger API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🗄️ **Neo4j Graph Console**: [http://localhost:7474](http://localhost:7474) (`neo4j` / `tracex2026`)

---

### Option 2: Standalone Local Setup

#### Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Automated Testing & Quality Gates

The backend includes a comprehensive pytest suite covering SHA-256 ingestion provenance, fusion arithmetic, hard gate enforcement, and end-to-end SSE pipelines:

```bash
cd backend
python -m pytest tests/ -v
```

### Test Suite Output:
```text
tests/test_audit.py::test_append_only_audit_event PASSED                 [ 12%]
tests/test_e2e.py::test_health_endpoint PASSED                           [ 25%]
tests/test_e2e.py::test_e2e_case_1_convergence PASSED                    [ 37%]
tests/test_e2e.py::test_e2e_case_2_contradiction_clash PASSED            [ 50%]
tests/test_fusion.py::test_fusion_arithmetic_case1_convergence PASSED    [ 62%]
tests/test_fusion.py::test_fusion_hard_gate_concurrency_clash PASSED     [ 75%]
tests/test_ingestion.py::test_sha256_deterministic_hashing PASSED        [ 87%]
tests/test_ingestion.py::test_artifact_provenance_and_deduplication PASSED [100%]

======================= 8 passed in 1.30s ========================
```

---

## 📁 Repository Structure

```text
TRACE-X/
├── docker-compose.yml              # Multi-container stack (Backend, Frontend, Neo4j)
├── README.md                       # Comprehensive project documentation
├── backend/
│   ├── Dockerfile                  # Python 3.11 slim production container
│   ├── .dockerignore               # Backend context exclusion rules
│   ├── requirements.txt            # Python dependencies
│   ├── app/
│   │   ├── main.py                 # FastAPI initialization & CORS setup
│   │   ├── core/config.py          # Environment settings & Pydantic models
│   │   ├── models/
│   │   │   ├── database.py         # SQLAlchemy models (Composite keys, SHA-256 index)
│   │   │   └── schemas.py          # Pydantic v2 validation contracts & Enums
│   │   ├── services/
│   │   │   ├── ingestion_service.py # Artifact validation, SHA-256 provenance hashing
│   │   │   ├── stylometry_engine.py# Sentence transformer embeddings & guardrail
│   │   │   ├── blockchain_engine.py# UTXO parser, CoinJoin dampener, VASP tracking
│   │   │   ├── graph_engine.py     # Neo4j property graph & Cytoscape edge builder
│   │   │   ├── behavioral_engine.py# Sequential dormancy & concurrency clash logic
│   │   │   └── fusion_engine.py    # Two-Level Contradiction Fusion Model
│   │   ├── api/endpoints/
│   │   │   ├── ingestion.py        # Benchmark loader & upload endpoints
│   │   │   ├── pipeline.py         # SSE streaming pipeline executor
│   │   │   ├── attribution.py      # Assessment fetch & dynamic tuner
│   │   │   ├── graph.py            # Cytoscape graph serialization
│   │   │   └── audit.py            # Append-only SHA-256 audit logger
│   │   └── data/
│   │       ├── benchmark_case_1.json # GhostSpecter convergence scenario
│   │       └── benchmark_case_2.json # Deceptive concurrency clash scenario
│   └── tests/                      # Automated test suite (8 test cases)
└── frontend/
    ├── Dockerfile                  # Node 20 multi-stage build + Nginx Alpine
    ├── .dockerignore               # Frontend context exclusion rules
    ├── nginx.conf                  # Production reverse proxy config
    ├── package.json                # Dependencies (React 18, Cytoscape, Lucide)
    └── src/
        ├── App.tsx                 # Main layout, benchmark runner & state
        ├── types/index.ts          # TypeScript domain interfaces
        ├── utils/graphIcons.ts     # Custom CTI SVG node graphics
        └── components/
            ├── Header.tsx          # Top navigation & legal scope banner
            ├── AttributionCard.tsx # Fused score, confidence band & rationale
            ├── EvidenceRadar.tsx   # 5-dimension radar breakdown & dampening alerts
            ├── ContradictionBox.tsx# Level 1 dampening & Level 2 hard gate callout
            ├── SensitivityDrawer.tsx# Live weight sliders & instant recalculator
            ├── AuditTrail.tsx      # Human-in-the-loop confirmation & SHA-256 hashes
            └── visualizers/
                ├── GraphCanvas.tsx # Cytoscape interactive property graph
                ├── FinancialFlow.tsx# Bitcoin peeling chain & VASP tracker
                └── TemporalMatrix.tsx# Sequential migration timeline
```

---

## 🔒 Security, Privacy & Legal Scope

1. **Legal Scope Guardrail**:
   - TRACE-X explicitly recognizes the legal boundary between digital persona correlation and real-world human attribution. The banner `LEGAL SCOPE: REAL-WORLD IDENTITY: NOT ESTABLISHED` is permanently displayed across all interfaces. Real-world identity verification requires lawful KYC subpoenas issued to identified VASPs or hosting entities.
2. **Data Integrity**:
   - All ingested darknet artifacts receive an immutable SHA-256 content hash upon entry. Cross-investigation artifact sharing is permitted via composite keying while duplicate submissions within the same investigation are rejected.
3. **Tamper-Evident Audit Logging**:
   - Every analyst intervention (`CONFIRM_ATTRIBUTION`, `REJECT_HYPOTHESIS`) produces an append-only audit event with an integrity hash combining `investigation_id`, `analyst_id`, `action`, `rationale`, and UTC timestamp.

---

## 👥 Team & Acknowledgments

- **Problem Statement**: SIH26151 — Threat Actor Persona De-Anonymization & Attribution
- **Agency**: National Technical Research Organisation (NTRO)
- **Competition**: Smart India Hackathon (SIH) 2026
- **Category**: Blockchain, Cybersecurity & Cyber Threat Intelligence

---
*Built with evidentiary rigor and zero false-positive tolerance for intelligence analysts and law enforcement operations.*
