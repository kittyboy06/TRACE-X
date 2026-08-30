# TRACE-X — Threat Relationship & Attribution Correlation Engine
**SIH26151 (National Technical Research Organisation - NTRO) | Blockchain & Cybersecurity**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.18-008CC1?style=flat&logo=neo4j)](https://neo4j.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com)

---

## 🎯 Executive Summary & Innovation

**TRACE-X** is an explainable, multi-modal Cyber Threat Intelligence (CTI) platform engineered to correlate dark-web personas, cryptocurrency flows, infrastructure fingerprints, linguistic stylometry, and temporal behavioral patterns to generate evidence-backed threat-actor attribution assessments.

### Key Innovations for SIH26151 Evaluators:
1. **Two-Level Contradiction Model**:
   - **Level 1 (Channel Reliability Dampening)**: Anomalies like CoinJoin collaborative transactions reduce financial signal confidence rather than globally penalizing unrelated cryptographic or stylometric evidence.
   - **Level 2 (Global Hard Gating Overrides)**: Mutually exclusive operational activities (e.g. simultaneous authenticated activity associated with infrastructure endpoints geolocated to Frankfurt and Singapore) trigger a **Hard Gate**, overriding the numerical score and safely failing closed to **`INCONCLUSIVE`** (preventing false-positive hallucinations).
2. **Permanent Identity Scope Guard**:
   - Explicitly displays `REAL-WORLD IDENTITY: NOT ESTABLISHED` by default, recognizing that darknet de-anonymization provides persona correlation while physical citizen identification requires authorized external KYC subpoenas and warrants.
3. **Append-Only Tamper-Evident Audit Trail**:
   - Human analysts validate hypotheses via `[✔ CONFIRM]`, `[✖ REJECT]`, or `[? INVESTIGATE]`. Every decision is recorded in an append-only audit log with a SHA-256 integrity hash.
4. **Interactive Sensitivity Tuner**:
   - Evaluators can tune evidentiary weights (*Cryptographic, Financial, Stylometric, Infrastructure, Behavioral*) in real-time and observe instant transparent recalculation.

---

## 🏗️ Architecture & Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│ React + TypeScript + Vite + Tailwind CSS + Cytoscape.js     │
│ Dashboard | Graph Visualizer | Peeling Flow | Tuner Drawer  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API + SSE Stream
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  FASTAPI ORCHESTRATION                      │
│ Ingestion Service → SHA-256 Provenance → Async Task Manager │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────────┐
│ AI Stylometry  │ │ Blockchain     │ │ Graph Intelligence │
│ + NLP Engine   │ │ Forensics      │ │ Neo4j + Cypher     │
└───────┬────────┘ └───────┬────────┘ └──────────┬─────────┘
        │                  │                     │
        └──────────────────┼─────────────────────┘
                           │
                 ┌─────────▼─────────┐
                 │ Behavioral &       │
                 │ Temporal Engine    │
                 └─────────┬─────────┘
                           │ Normalized Dimension Signals
                           ▼
              ┌─────────────────────────┐
              │ Evidence Fusion &       │
              │ Contradiction Engine    │
              │ (Two-Level Model)       │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Attribution Assessment  │
              │ (CONFIRMED / LIKELY /   │
              │ POSSIBLE / INCONCLUSIVE)│
              └────────────┬────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA & EVIDENCE                         │
│ MinIO/Local Object Store | SQLite/PostgreSQL | Neo4j Graph  │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start & Live Demo Guide

### Option 1: Full Docker Compose Deployment (Recommended)
```bash
# 1. Clone & enter repository
git clone https://github.com/your-org/TRACE-X.git
cd TRACE-X

# 2. Launch the entire containerized stack
docker compose up --build -d

# 3. Access interfaces:
# - Frontend Analyst Dashboard: http://localhost:5173
# - Backend FastAPI Docs:        http://localhost:8000/docs
# - Neo4j Browser:               http://localhost:7474 (neo4j / tracex2026)
```

### Option 2: Local Development Execution

#### 1. Backend Setup:
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup:
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173 in your browser
```

---

## 🧪 Evaluation Benchmark Scenarios

| Scenario | Objective | Observed Evidence | Two-Level Contradiction Behavior | Final Attribution State |
| :--- | :--- | :--- | :--- | :--- |
| **Case 1: GhostSpecter Migration** | Multi-Modal Convergence | PGP Key reuse (`0x9B8A7C`), UTXO peeling chain to Kraken VASP, 0.84 NLP stylometry similarity ($\ge 150$ words), sequential dormancy window | CoinJoin hop detected $\to$ Level 1 Financial reliability dampened to 54%. Base score: **0.766**. | **`LIKELY LINK`** (High Confidence) |
| **Case 2: Deceptive Concurrency** | Anti-False-Positive Safety | High stylometry similarity (0.86), but distinct PGP keys, Samourai Whirlpool mixing, and simultaneous authenticated activity across distinct infrastructure endpoints | Hard Gate Triggered: `TEMPORAL_CONCURRENCY_CLASH` $\to$ Score overridden. | **`INCONCLUSIVE`** (Safe Fail-Closed) |

---

## 🔒 Evidentiary Data Contract & Schemas

### Fused Evidence Formula
$$S_{\text{base}} = \sum_{i=1}^{5} w_i \cdot s'_i \quad \text{where } s'_i = s_i \times \text{reliability}_i$$
$$S_{\text{fused}} = S_{\text{base}} \times \prod_{j=1}^{m} (1 - p_j) \quad \text{(overridden by Hard Gate)}$$

### Decision Boundary Mapping
- **`CONFIRMED LINK`**: Score $\ge 0.85$ + Direct cryptographic key reuse / corroboration + Zero hard contradictions.
- **`LIKELY LINK`**: Score $0.70 - 0.84$ + Multi-source alignment across financial, stylometric, and behavioral channels.
- **`POSSIBLE LINK`**: Score $0.50 - 0.69$ + Correlative signals, plausible alternative hypotheses remain.
- **`INCONCLUSIVE`**: Score $< 0.50$ OR **Hard Contradiction Gate Triggered**.
- **`LIKELY DIFFERENT`**: Low alignment with confirmed mutually exclusive provenance.

---

## 📄 License & Team
Developed for **Smart India Hackathon 2026** (Problem Statement SIH26151).  
Sponsored by **National Technical Research Organisation (NTRO)**.
