# 📊 TRACE-X Master Slide Deck Script (10 Slides)

> **Competition**: Smart India Hackathon 2026 | **Ministry**: National Technical Research Organisation (NTRO)  
> **Problem Statement**: SIH26151 — Advanced Cyber Threat Intelligence & Persona Correlation  
> **Governance**: Decision #13 — Non-Invasive Presentation & Submission Layer  

---

## Slide 1: Title & Problem Statement

### Slide Visual
- **Header**: TRACE-X: Threat Relationship & Attribution Correlation Engine
- **Subtitle**: Explainable, Multi-Modal Cyber Threat Attribution for Analyst Decision Support
- **Badges**: NTRO SIH26151 | FastAPI + React + Neo4j + Docker | 100% Offline Resilience
- **Footer**: Team TRACE-X | Smart India Hackathon 2026

### Speaker Notes (30 seconds)
> *"Good morning, respected evaluators. We present TRACE-X, an explainable Cyber Threat Intelligence correlation platform engineered for NTRO problem statement SIH26151. Our mission is to transform fragmented darknet signals—forum communications, cryptocurrency transaction graphs, infrastructure fingerprints, and behavioral cadences—into transparent, mathematically verified attribution assessments for expert decision support."*

---

## Slide 2: The Core Challenge: Obfuscation vs. Hallucinated Attribution

### Slide Visual
- **Left Column: Failure Mode 1 (Naive Similarity)**:
  - Text: Black-box LLMs match casual hacker slang and hallucinate false links.
  - Consequence: Severe operational misdirection and wasted intelligence resources.
- **Right Column: Failure Mode 2 (Obfuscation Overreach)**:
  - Text: Standard tools treat Bitcoin CoinJoin mixing or Tor hosting as a total block.
  - Consequence: High-confidence primary vectors (like PGP key reuse) are ignored.
- **Center Banner**:
  - *"Traditional tools either hallucinate links or surrender to obfuscation. TRACE-X provides mathematical discrimination."*

### Speaker Notes (30 seconds)
> *"Dark-web threat actors deliberately deploy asymmetric obfuscation: CoinJoin mixers to hide funds, proxy routing to scramble IPs, and deceptive forum personas. Existing attribution tools fail in two opposing directions: black-box neural models hallucinate connections based on trivial slang, while naive heuristics give up completely whenever a CoinJoin mixer appears. TRACE-X was built from the ground up to solve both problems through rigorous mathematical isolation."*

---

## Slide 3: TRACE-X High-Level Architecture

### Slide Visual
- **Diagram (Architecture Ingestion Flow)**:
  ```
  Darknet Artifacts (Posts, BTC, PGP, Infra, Timing)
                          ↓
      [Earliest-Layer Security: Nginx 10MB + Zip Defense]
                          ↓
      [Decision #10: 4-Factor Source Reliability Engine]
                          ↓
      [4 Multi-Modal Analytical Engines: NLP, UTXO, Graph, Cadence]
                          ↓
      [Two-Level Contradiction Fusion Engine]
             ├── Level 1: Channel Dampening (CoinJoin 0.60x)
             └── Level 2: Global Hard Gate (Temporal Clashes)
                          ↓
      [Explainable UI: Cytoscape Graph + Sensitivity Tuner]
                          ↓
      [Tamper-Evident SHA-256 Audit Chain + PDF Dossier]
  ```

### Speaker Notes (35 seconds)
> *"Our architecture enforces defense-in-depth from the earliest layer. Evidence packages are validated against a 10 MB strict limit and anti-zip-bomb guardrails. Artifacts pass into our 4-Factor Source Reliability Engine, modulate into four specialized analytical engines, and converge at our Two-Level Contradiction Fusion Core. The results feed an interactive Cytoscape graph canvas and an immutable SHA-256 cryptographic audit ledger."*

---

## Slide 4: Two-Level Contradiction Fusion Framework

### Slide Visual
- **Formulation Box**:
  $$S_{\text{base}} = \sum_{i=1}^{5} w_i \cdot s'_i \quad \text{where } \sum w_i = 1.0000$$
- **Level 1: Channel-Specific Reliability Dampening**:
  - $s'_{\text{financial}} = s_{\text{raw}, \text{financial}} \times 0.60$ (CoinJoin affects financial only).
  - Cryptographic and stylometric signals remain 100% untainted.
- **Level 2: Global Contradiction Hard Gate**:
  - $\text{If Hard Gate Triggered} \implies \text{Verdict} = \mathbf{INCONCLUSIVE}, \; \text{Band} = \mathbf{LOW}$.
  - $S_{\text{base}}$ is preserved without artificial zeroing for full analytical auditability.

### Speaker Notes (35 seconds)
> *"Our core mathematical innovation is Two-Level Fusion. At Level 1, detected obfuscation—such as a CoinJoin transaction—penalizes only the affected financial vector by 0.60x, leaving independent cryptographic key reuse untouched. At Level 2, physical operational contradictions—such as simultaneous administrative actions across conflicting geographic networks—immediately trigger a global hard gate, overriding the assessment to INCONCLUSIVE while preserving the underlying score for transparency."*

---

## Slide 5: 4-Factor Source Reliability Engine (Decision #10)

### Slide Visual
- **Formula**:
  $$R = 0.40 \cdot R_{\text{reputation}} + 0.30 \cdot R_{\text{freshness}} + 0.20 \cdot R_{\text{corroboration}} + 0.10 \cdot R_{\text{consistency}}$$
- **Channel Modifier Range**:
  $$\text{Channel Modifier} = 0.50 + 0.50 \cdot R \in [0.50, 1.00]$$
- **Core Invariant**:
  - High unreliability can reduce evidentiary weight, but cannot discount valid corroborating evidence below 50%.

### Speaker Notes (30 seconds)
> *"Intelligence is only as good as its source. Under Decision #10, TRACE-X evaluates every evidence source across four weighted factors: reputation, freshness, corroboration, and internal consistency. The resulting reliability score maps into a [0.50, 1.00] channel modifier. This guarantees that unverified darknet forums cannot produce false high-confidence correlations, while preventing unreliability from artificially erasing hard evidence."*

---

## Slide 6: Benchmark Case 1: Multi-Modal Evidentiary Convergence

### Slide Visual
- **Scenario**: Operation GhostSpecter (`INV-SIH-001`)
- **Ingested Signals**:
  - Cryptographic: Primary RSA-4096 key reuse (Score: 0.95, Weight: 0.30)
  - Financial: UTXO peeling chain to Kraken deposit with CoinJoin mixing (Score: 0.54, Weight: 0.25)
  - Stylometry: Dread forum posts $\ge 150$ words & $\ge 500$ tokens (Score: 0.83, Weight: 0.20)
  - Infrastructure: Shared TLS certificate serial & SSH fingerprint (Score: 0.65, Weight: 0.15)
  - Behavioral: Sequential vendor dormancy handoff (Score: 0.80, Weight: 0.10)
- **Authoritative Outcome**:
  - $S_{\text{base}} \approx 0.7639$ (fallback) / $0.7735$ (transformer)
  - State: **`LIKELY_LINK`** | Confidence: **`HIGH`**

### Speaker Notes (35 seconds)
> *"In Benchmark Case 1, we demonstrate clean multi-modal convergence. Despite a CoinJoin mixing transaction attempting to break the financial trail, our financial engine dampens only the UTXO score to 0.54. Because the PGP primary key was reused across personas and linguistic stylometry satisfied our 150-word and 500-token guardrails, the evidence converges to LIKELY_LINK with High confidence."*

---

## Slide 7: Benchmark Case 2: Anti-False-Positive Hard Gating

### Slide Visual
- **Scenario**: Operation DeceptiveClone (`INV-SIH-002`)
- **Key Evidentiary Determinations**:
  - Stylometry Guardrail Withheld: Corpus has only 118 & 114 words ($< 150$ words / $< 500$ tokens floor).
  - Temporal Engine: Detected simultaneous authenticated sessions in Frankfurt and Singapore within 14.2 seconds.
- **Attribution Outcome**:
  - State: **`INCONCLUSIVE`** (Forced by Level 2 Hard Gate)
  - Confidence: **`LOW`**
  - Authoritative $S_{\text{base}}$: **0.2150** (Preserved)
- **Takeaway**: *"The killer moment: TRACE-X knows when similarity isn't enough."*

### Speaker Notes (35 seconds)
> *"Case 2 represents the critical test for threat attribution. A deceptive actor created an alias mimicking the target. First, because both text corpora fell below our 150-word and 500-token threshold, TRACE-X withheld stylometric scoring completely rather than generating a hallucinated match. Second, our temporal engine proved simultaneous authenticated activity across geographically conflicting networks. Level 2 hard gating triggered immediately, overriding the verdict to INCONCLUSIVE. TRACE-X protects analysts from wrongful attribution."*

---

## Slide 8: Interactive Sensitivity Tuner & Cryptographic Audit Trail

### Slide Visual
- **Sensitivity Tuner (Preview vs. Commit)**:
  - Real-time weight adjustment with automated normalization ($\sum w_i = 1.0000$).
  - Simulation Preview is **100% audit-neutral**.
- **Cryptographic Audit Chain**:
  - Append-only ledger linking events:
    $$\text{Hash}_k = \text{SHA-256}(\text{Hash}_{k-1} \parallel \text{Timestamp} \parallel \text{Action} \parallel \text{AnalystID} \parallel \text{Payload})$$
  - Genesis anchor: `00000000...0000` (64 zeros).
  - Live cryptographic verification endpoint: `/api/v1/audit/verify/{id}`.

### Speaker Notes (35 seconds)
> *"Supervisory oversight requires flexibility without compromising chain-of-custody. Our Sensitivity Tuner allows analysts to simulate alternative weighting hypotheses in Preview Mode with zero database writes. Only upon formal commitment is an append-only event recorded in our cryptographic audit chain. Every event hashes the prior event's hash, timestamp, and analyst credentials, creating a tamper-evident audit record verified from genesis to terminal hash."*

---

## Slide 9: Publication-Grade Forensic Reporting & Database Reconstruction

### Slide Visual
- **Core Invariant**: Reports reconstructed **strictly from persisted DB state**; never by re-running non-deterministic models.
- **Multi-Format Export**:
  - **Publication PDF**: Two-pass ReportLab `NumberedCanvas` ("Page X of Y"), official NTRO running header, dynamic radar chart, and cryptographic audit table.
  - **Tabular CSV**: Multi-section CSV export for analytical cross-referencing.
  - **Canonical JSON**: Full structured model with `report_hash` for automated ingestion into SIEM / TIP platforms.

### Speaker Notes (30 seconds)
> *"When intelligence must be escalated for legal or operational review, TRACE-X generates publication-grade dossiers purely from persisted database state. Non-deterministic models are never re-run during export. The resulting PDF features a two-pass NumberedCanvas with running headers, evidence radar geometry, and the full audit hash ledger, alongside standardized CSV and canonical JSON formats."*

---

## Slide 10: System Verification, Deployment & Conclusion

### Slide Visual
- **Verification Scorecard**:
  - ✅ **100% of Committed Backend Test Suite Passing** (Zero failures, zero warnings).
  - ✅ **10/10 TRACE-X SIH Acceptance Checkpoints Verified**.
  - ✅ **7/7 Docker Desktop Runtime Acceptance Tests Verified**.
  - ✅ **0 TypeScript Build Errors** in production frontend bundle.
- **Deployment**:
  - Fully containerized on Docker Desktop (`frontend`, `backend`, `neo4j`).
  - Transparent offline fallbacks for classified or air-gapped environments.
- **Closing Motto**:
  > *"TRACE-X: Mathematically rigorous, explainable, and hallucination-resistant threat intelligence for national security."*

### Speaker Notes (30 seconds)
> *"To conclude: TRACE-X is fully deployed, containerized, and rigorously verified. 100% of our backend test suite passes with zero warnings, all 10 SIH acceptance checkpoints pass, and our Docker Desktop stack runs with unbuffered SSE streaming and volume persistence. TRACE-X gives national security analysts what they need most: transparent, verifiable, and explainable threat attribution. Thank you."*
