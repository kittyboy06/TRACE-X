import json
import hashlib
import io
import csv
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.database import (
    InvestigationModel,
    EvidenceRecordModel,
    ExtractedEntityModel,
    SourceReliabilityModel,
    AttributionAssessmentModel,
    AuditEventModel
)
from app.services.audit_chain import AuditChainService

# ReportLab imports for publication-grade PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count
    and legal/confidentiality footers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header on page 2+
        if self._pageNumber > 1:
            self.drawString(54, 750, "TRACE-X — FORENSIC INVESTIGATION DOSSIER | NTRO SIH26151")
            self.drawRightString(558, 750, "OFFICIAL USE ONLY")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running Footer on all pages
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 7.5)
        self.drawString(
            54, 32,
            "REAL-WORLD IDENTITY: NOT ESTABLISHED | CTI INVESTIGATIVE DECISION SUPPORT"
        )
        self.drawRightString(
            558, 32,
            f"Page {self._pageNumber} of {page_count}"
        )
        self.restoreState()


class ReportService:
    """
    Forensic Reporting Engine for TRACE-X.
    Governed strictly by Decision #11:
    - Pure database reconstruction (zero network queries, zero live pipeline re-runs).
    - Deterministic JSON, CSV, and PDF dossier generation.
    - Defensible terminology (never claims automatic legal admissibility).
    - Canonical report_hash with stable collection sorting.
    """

    @classmethod
    def generate_dossier_data(cls, investigation_id: str, db: Session) -> Dict[str, Any]:
        """
        Purely reconstructs all investigation facts, assessments, evidence, and audit events
        from the database and returns a deterministic, canonical representation.
        """
        inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found")

        # 1. Current Assessment
        assess = db.query(AttributionAssessmentModel).filter(
            AttributionAssessmentModel.investigation_id == investigation_id,
            AttributionAssessmentModel.is_current == True
        ).order_by(AttributionAssessmentModel.created_at.desc()).first()

        # 2. Evidence Records (Deterministic sort: evidence_id ASC)
        evidence_records = db.query(EvidenceRecordModel).filter(
            EvidenceRecordModel.investigation_id == investigation_id
        ).order_by(EvidenceRecordModel.evidence_id.asc()).all()

        # 3. Extracted Entities (Deterministic sort: entity_id ASC)
        entities = db.query(ExtractedEntityModel).filter(
            ExtractedEntityModel.investigation_id == investigation_id
        ).order_by(ExtractedEntityModel.entity_id.asc()).all()

        # 4. Source Reliabilities (Deterministic sort: source_uri ASC)
        sources = db.query(SourceReliabilityModel).filter(
            SourceReliabilityModel.investigation_id == investigation_id
        ).order_by(SourceReliabilityModel.source_uri.asc()).all()

        # 5. Audit Events (Deterministic sort: timestamp ASC, audit_id ASC)
        audit_events = db.query(AuditEventModel).filter(
            AuditEventModel.investigation_id == investigation_id
        ).order_by(AuditEventModel.timestamp.asc(), AuditEventModel.audit_id.asc()).all()

        # Cryptographic verification of audit chain from genesis
        is_chain_valid, verified_records, chain_error = AuditChainService.verify_investigation_chain(
            investigation_id, db
        )
        terminal_audit_hash = verified_records[-1]["event_hash"] if verified_records else ("0" * 64)
        first_event_timestamp = verified_records[0]["timestamp"] if verified_records else None

        # Extract distinct Analyst Decisions from audit log
        analyst_decisions = []
        for a in audit_events:
            if a.action in ("CONFIRMED", "REJECTED", "INVESTIGATE") or "BY_ANALYST" in a.action:
                analyst_decisions.append({
                    "audit_id": a.audit_id,
                    "action": a.action,
                    "analyst_id": a.analyst_id,
                    "timestamp": a.timestamp.isoformat() if hasattr(a.timestamp, "isoformat") else str(a.timestamp),
                    "rationale": a.rationale,
                    "prior_state": a.prior_state,
                    "resulting_state": a.resulting_state
                })
        analyst_decisions.sort(key=lambda x: (x["timestamp"], x["audit_id"]))

        # Extract truthful ML and Analytical Engine provenance from persisted assessment
        assessment_payload = assess.payload if assess and assess.payload else {}
        dim_signals = (
            assessment_payload.get("evidence_dimensions")
            or assessment_payload.get("dimension_signals")
            or {}
        )

        def get_dim_signal(name: str) -> Dict[str, Any]:
            return dim_signals.get(name.lower()) or dim_signals.get(name.upper()) or {}

        stylometry_signal = get_dim_signal("stylometric")
        engine_metadata = (
            stylometry_signal.get("engine_metadata")
            or stylometry_signal.get("supporting_details")
            or {}
        )
        engine_type = engine_metadata.get("engine") or engine_metadata.get("engine_type") or "TRANSFORMER"
        model_name = engine_metadata.get("model") or engine_metadata.get("model_name")
        if not model_name:
            model_name = "sentence-transformers/all-mpnet-base-v2" if engine_type == "TRANSFORMER" else "DETERMINISTIC_FALLBACK"

        embedding_dim = engine_metadata.get("dimension") or engine_metadata.get("embedding_dimension")
        if not embedding_dim:
            embedding_dim = 768 if engine_type == "TRANSFORMER" else 64

        # Blockchain & Financial findings from persisted payload
        financial_signal = get_dim_signal("financial")
        financial_findings = (
            financial_signal.get("findings")
            or financial_signal.get("supporting_details", {}).get("findings")
            or []
        )

        # Contradictions & Dampenings from persisted payload (support both schema variants)
        contradictions = assessment_payload.get("contradictions") or []
        if not contradictions:
            for gc in assessment_payload.get("global_contradictions", []):
                contradictions.append({
                    "level": "LEVEL_2_HARD_GATE",
                    "contradiction_type": gc.get("contradiction_type", "GLOBAL_CONTRADICTION"),
                    "target_dimension": None,
                    "dampening_factor": None,
                    "trigger_hard_gate": gc.get("triggers_hard_gate", True),
                    "explanation": gc.get("detail", ""),
                    "evidence_ids": []
                })
            for cd in assessment_payload.get("channel_dampenings", []):
                factor_val = cd.get("factor_applied", 1.0)
                reason_val = cd.get("reason", "Channel dampening")
                dim_val = cd.get("dimension", "")
                contradictions.append({
                    "level": "LEVEL_1_CHANNEL_DAMPENING",
                    "contradiction_type": reason_val,
                    "target_dimension": dim_val,
                    "dampening_factor": factor_val,
                    "trigger_hard_gate": False,
                    "explanation": f"Channel reliability factor reduced to {factor_val:.2f} due to {reason_val}.",
                    "evidence_ids": []
                })

        channel_dampenings = [
            c for c in contradictions
            if c.get("level") == "LEVEL_1_CHANNEL_DAMPENING" or c.get("dampening_factor") is not None
        ]
        hard_gates = [
            c for c in contradictions
            if c.get("level") == "LEVEL_2_HARD_GATE" or c.get("trigger_hard_gate") is True
        ]

        # Structure normalized evidence items
        evidence_list = [
            {
                "evidence_id": e.evidence_id,
                "artifact_type": e.artifact_type,
                "source_uri": e.source_uri,
                "collected_at": e.collected_at.isoformat() if hasattr(e.collected_at, "isoformat") else str(e.collected_at),
                "content_hash": e.content_hash,
                "extractor_version": e.extractor_version,
                "model_version": e.model_version
            }
            for e in evidence_records
        ]
        evidence_list.sort(key=lambda x: x["evidence_id"])

        # Structure extracted entities
        entity_list = [
            {
                "entity_id": ent.entity_id,
                "entity_type": ent.entity_type,
                "value": ent.value,
                "evidence_id": ent.evidence_id,
                "confidence": ent.confidence
            }
            for ent in entities
        ]
        entity_list.sort(key=lambda x: x["entity_id"])

        # Structure source reliabilities
        source_list = [
            {
                "source_uri": s.source_uri,
                "trust_tier": s.trust_tier,
                "reliability_score": round(float(s.reliability_score), 4),
                "reputation": round(float(s.reputation), 4),
                "freshness": round(float(s.freshness), 4),
                "corroboration": round(float(s.corroboration), 4),
                "consistency": round(float(s.consistency), 4),
                "reliability_class": s.reliability_class,
                "channel_modifier": round(0.5 + 0.5 * float(s.reliability_score), 4),
                "last_scan": s.last_scan.isoformat() if hasattr(s.last_scan, "isoformat") else str(s.last_scan),
                "scan_status": s.scan_status
            }
            for s in sources
        ]
        source_list.sort(key=lambda x: x["source_uri"])

        # Structure audit ledger
        audit_trail = [
            {
                "audit_id": a.audit_id,
                "action": a.action,
                "analyst_id": a.analyst_id,
                "timestamp": a.timestamp.isoformat() if hasattr(a.timestamp, "isoformat") else str(a.timestamp),
                "rationale": a.rationale,
                "previous_hash": a.previous_hash,
                "event_hash": a.event_hash
            }
            for a in audit_events
        ]
        audit_trail.sort(key=lambda x: (x["timestamp"], x["audit_id"]))

        # Structure current assessment summary
        hard_gate_applied = bool(
            assess.payload.get("hard_gate_applied", False)
            or bool(hard_gates)
        ) if assess else False

        hard_gate_reason = (
            assess.payload.get("hard_gate_reason")
            or (hard_gates[0].get("explanation") if hard_gates else None)
        ) if assess else None

        rationale = (
            assess.payload.get("assessment_rationale")
            or assess.payload.get("rationale")
            or ""
        ) if assess else ""

        canonical_dimensions = {
            "CRYPTOGRAPHIC": get_dim_signal("cryptographic"),
            "FINANCIAL": get_dim_signal("financial"),
            "STYLOMETRIC": get_dim_signal("stylometric"),
            "INFRASTRUCTURE": get_dim_signal("infrastructure"),
            "BEHAVIORAL_TEMPORAL": get_dim_signal("behavioral_temporal")
        }

        current_assessment_data = {
            "assessment_id": assess.assessment_id if assess else "ASSESS-NONE",
            "attribution_state": assess.attribution_state if assess else "INCONCLUSIVE",
            "confidence_band": assess.confidence_band if assess else "LOW",
            "base_score": round(float(assess.base_score), 4) if assess else 0.0,
            "hard_gate_applied": hard_gate_applied,
            "hard_gate_reason": hard_gate_reason,
            "rationale": rationale,
            "real_world_identity": "NOT ESTABLISHED",
            "created_at": assess.created_at.isoformat() if assess and hasattr(assess.created_at, "isoformat") else None,
            "dimension_signals": canonical_dimensions,
            "contradictions": contradictions
        }

        # Canonical structure for report hashing
        canonical_investigation_data = {
            "analyst_decisions": analyst_decisions,
            "audit_chain": audit_trail,
            "current_assessment": current_assessment_data,
            "entities": entity_list,
            "evidence": evidence_list,
            "investigation": {
                "id": inv.id,
                "title": inv.title,
                "persona_a": inv.target_persona_a,
                "persona_b": inv.target_persona_b,
                "classification": inv.classification or "UNRESTRICTED",
                "assigned_analyst_id": inv.assigned_analyst_id
            },
            "source_reliability": source_list
        }

        # Deterministic JSON canonical string
        canonical_json = json.dumps(
            canonical_investigation_data,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        )
        report_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        now_utc = datetime.now(timezone.utc).isoformat()

        return {
            "report_metadata": {
                "title": "Forensic Investigation Dossier",
                "system": "TRACE-X (Threat Relationship & Attribution Correlation Engine)",
                "standard": "NTRO SIH26151 Evidentiary Framework",
                "generated_at": now_utc,
                "report_hash": report_hash,
                "assessment_id": current_assessment_data["assessment_id"],
                "terminal_audit_hash": terminal_audit_hash,
                "audit_chain_valid": is_chain_valid,
                "audit_chain_error": chain_error,
                "verified_event_count": len(verified_records),
                "first_event_timestamp": first_event_timestamp,
                "legal_disclaimer": "Forensic Investigation Dossier — Not automatically legally admissible without judicial chain-of-custody corroboration.",
                "identity_disclaimer": "REAL-WORLD IDENTITY: NOT ESTABLISHED. Real-world identity attribution requires appropriate authorized investigative and legal processes outside TRACE-X."
            },
            "investigation": canonical_investigation_data["investigation"],
            "current_assessment": current_assessment_data,
            "dimension_signals": canonical_dimensions,
            "contradictions": contradictions,
            "channel_dampenings": channel_dampenings,
            "hard_gates": hard_gates,
            "blockchain_findings": financial_findings,
            "model_provenance": {
                "engine": engine_type,
                "model_name": model_name,
                "embedding_dimensions": embedding_dim,
                "stylometry_guardrail": ">= 150 words AND >= 500 tokenizer tokens"
            },
            "evidence_inventory": evidence_list,
            "extracted_entities": entity_list,
            "source_reliabilities": source_list,
            "analyst_decisions": analyst_decisions,
            "audit_trail": audit_trail
        }

    @classmethod
    def generate_json_dossier(cls, investigation_id: str, db: Session) -> Dict[str, Any]:
        """
        Returns the complete structured JSON dossier.
        """
        return cls.generate_dossier_data(investigation_id, db)

    @classmethod
    def generate_csv_dossier(cls, investigation_id: str, db: Session) -> str:
        """
        Generates a deterministic multi-section CSV document with stable ordering.
        """
        data = cls.generate_dossier_data(investigation_id, db)
        meta = data["report_metadata"]
        inv = data["investigation"]
        assess = data["current_assessment"]

        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Header & Disclaimers
        writer.writerow(["=== TRACE-X FORENSIC INVESTIGATION DOSSIER CSV EXPORT ==="])
        writer.writerow(["SYSTEM", meta["system"]])
        writer.writerow(["STANDARD", meta["standard"]])
        writer.writerow(["TITLE", meta["title"]])
        writer.writerow(["REPORT HASH", meta["report_hash"]])
        writer.writerow(["GENERATED AT (UTC)", meta["generated_at"]])
        writer.writerow(["TERMINAL AUDIT HASH", meta["terminal_audit_hash"]])
        writer.writerow(["AUDIT CHAIN INTEGRITY", "VALID" if meta["audit_chain_valid"] else f"INVALID ({meta['audit_chain_error']})"])
        writer.writerow(["VERIFIED EVENTS COUNT", meta["verified_event_count"]])
        writer.writerow(["SCOPE RESTRICTION", meta["identity_disclaimer"]])
        writer.writerow(["LEGAL NOTICE", meta["legal_disclaimer"]])
        writer.writerow([])

        # 2. Investigation Overview
        writer.writerow(["=== INVESTIGATION OVERVIEW ==="])
        writer.writerow(["INVESTIGATION ID", inv["id"]])
        writer.writerow(["TITLE", inv["title"]])
        writer.writerow(["PERSONA A", inv["persona_a"]])
        writer.writerow(["PERSONA B", inv["persona_b"]])
        writer.writerow(["CLASSIFICATION", inv["classification"]])
        writer.writerow(["ASSIGNED ANALYST", inv["assigned_analyst_id"]])
        writer.writerow([])

        # 3. Attribution Assessment
        writer.writerow(["=== ATTRIBUTION ASSESSMENT ==="])
        writer.writerow(["ASSESSMENT ID", assess["assessment_id"]])
        writer.writerow(["ATTRIBUTION STATE", assess["attribution_state"]])
        writer.writerow(["CONFIDENCE BAND", assess["confidence_band"]])
        writer.writerow(["AUTHORITATIVE S_BASE", f"{assess['base_score']:.4f}"])
        writer.writerow(["HARD GATE APPLIED", assess["hard_gate_applied"]])
        writer.writerow(["HARD GATE REASON", assess["hard_gate_reason"] or "N/A"])
        writer.writerow(["RATIONALE", assess["rationale"]])
        writer.writerow([])

        # 4. 5-Dimension Evidence Breakdown
        writer.writerow(["=== 5-DIMENSION EVIDENCE BREAKDOWN ==="])
        writer.writerow(["DIMENSION", "RAW SCORE", "RELIABILITY FACTOR", "ADJUSTED SCORE", "WEIGHT", "CONTRIBUTION"])
        dims = data["dimension_signals"]
        default_weights = {
            "CRYPTOGRAPHIC": 0.30,
            "FINANCIAL": 0.25,
            "STYLOMETRIC": 0.20,
            "INFRASTRUCTURE": 0.15,
            "BEHAVIORAL_TEMPORAL": 0.10
        }
        for d_name in sorted(default_weights.keys()):
            sig = dims.get(d_name.lower()) or dims.get(d_name.upper()) or {}
            raw = float(sig.get("raw_score", 0.0))
            rel = float(sig.get("reliability_factor", 1.0))
            adj = float(sig.get("adjusted_score", raw * rel))
            w = float(sig.get("configured_weight", default_weights[d_name]))
            contrib = adj * w
            writer.writerow([d_name, f"{raw:.4f}", f"{rel:.4f}", f"{adj:.4f}", f"{w:.2f}", f"{contrib:.4f}"])
        writer.writerow([])

        # 5. Normalized Evidence Inventory
        writer.writerow(["=== NORMALIZED EVIDENCE INVENTORY ==="])
        writer.writerow(["EVIDENCE ID", "ARTIFACT TYPE", "SOURCE URI", "COLLECTED AT (UTC)", "CONTENT HASH (SHA-256)", "EXTRACTOR"])
        for ev in data["evidence_inventory"]:
            writer.writerow([
                ev["evidence_id"],
                ev["artifact_type"],
                ev["source_uri"],
                ev["collected_at"],
                ev["content_hash"],
                ev["extractor_version"]
            ])
        writer.writerow([])

        # 6. Extracted Technical Indicators
        writer.writerow(["=== EXTRACTED TECHNICAL INDICATORS ==="])
        writer.writerow(["ENTITY ID", "ENTITY TYPE", "VALUE", "CONFIDENCE", "PARENT EVIDENCE ID"])
        for ent in data["extracted_entities"]:
            writer.writerow([
                ent["entity_id"],
                ent["entity_type"],
                ent["value"],
                f"{ent['confidence']:.2f}",
                ent["evidence_id"]
            ])
        writer.writerow([])

        # 7. Evidence Sources & Trust Tiers
        writer.writerow(["=== EVIDENCE SOURCES & TRUST TIERS ==="])
        writer.writerow(["SOURCE URI", "TRUST TIER", "RELIABILITY CLASS", "SCORE (R)", "CHANNEL MODIFIER", "REPUTATION", "FRESHNESS", "CORROBORATION", "CONSISTENCY"])
        for s in data["source_reliabilities"]:
            writer.writerow([
                s["source_uri"],
                s["trust_tier"],
                s["reliability_class"],
                f"{s['reliability_score']:.4f}",
                f"{s['channel_modifier']:.4f}",
                f"{s['reputation']:.4f}",
                f"{s['freshness']:.4f}",
                f"{s['corroboration']:.4f}",
                f"{s['consistency']:.4f}"
            ])
        writer.writerow([])

        # 8. Analyst Decisions
        writer.writerow(["=== ANALYST DECISIONS ==="])
        writer.writerow(["TIMESTAMP (UTC)", "ACTION", "ANALYST ID", "RATIONALE", "PRIOR STATE", "RESULTING STATE"])
        for d in data["analyst_decisions"]:
            writer.writerow([
                d["timestamp"],
                d["action"],
                d["analyst_id"],
                d["rationale"],
                d["prior_state"],
                d["resulting_state"]
            ])
        writer.writerow([])

        # 9. Audit Ledger Trail
        writer.writerow(["=== AUDIT LEDGER TRAIL ==="])
        writer.writerow(["AUDIT ID", "TIMESTAMP (UTC)", "ACTION", "ANALYST ID", "PREVIOUS HASH (SHA-256)", "EVENT HASH (SHA-256)"])
        for a in data["audit_trail"]:
            writer.writerow([
                a["audit_id"],
                a["timestamp"],
                a["action"],
                a["analyst_id"],
                a["previous_hash"],
                a["event_hash"]
            ])

        return output.getvalue()

    @classmethod
    def generate_pdf_dossier(cls, investigation_id: str, db: Session) -> bytes:
        """
        Generates a publication-grade multi-page Forensic Investigation Dossier PDF using ReportLab.
        Enforces Decision #11:
        - Pure database reconstruction
        - Prominent legal & identity disclaimers
        - Authentic ML model provenance
        - Tabular 5-dimension breakdown
        - Complete audit chain verification summary and table
        """
        data = cls.generate_dossier_data(investigation_id, db)
        meta = data["report_metadata"]
        inv = data["investigation"]
        assess = data["current_assessment"]
        dims = data["dimension_signals"]
        model_prov = data["model_provenance"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=44,
            rightMargin=44,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#0284C7")
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155")
        )
        body_bold = ParagraphStyle(
            "BodyDarkBold",
            parent=body_style,
            fontName="Helvetica-Bold"
        )
        disclaimer_title = ParagraphStyle(
            "DisclaimerTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#991B1B")
        )
        disclaimer_text = ParagraphStyle(
            "DisclaimerText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#7F1D1D")
        )
        mono_small = ParagraphStyle(
            "MonoSmall",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#1E293B")
        )
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E293B")
        )
        table_cell_mono = ParagraphStyle(
            "TableCellMono",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#0F172A")
        )

        elements = []

        # -------------------------------------------------------------
        # 1. Header Banner
        # -------------------------------------------------------------
        elements.append(Paragraph("TRACE-X — THREAT RELATIONSHIP & ATTRIBUTION CORRELATION ENGINE", subtitle_style))
        elements.append(Paragraph("Forensic Investigation Dossier", title_style))
        elements.append(Paragraph(
            f"<b>STANDARD:</b> NTRO SIH26151 Evidentiary Framework &nbsp;|&nbsp; "
            f"<b>CLASSIFICATION:</b> {inv['classification']} &nbsp;|&nbsp; "
            f"<b>MODE:</b> Decision Support System",
            body_style
        ))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceBefore=0, spaceAfter=8))

        # -------------------------------------------------------------
        # 2. Prominent Legal & Identity Disclaimer Box (Mandatory)
        # -------------------------------------------------------------
        disclaimer_content = [
            [
                Paragraph("<b>REAL-WORLD IDENTITY: NOT ESTABLISHED</b>", disclaimer_title)
            ],
            [
                Paragraph(
                    "Real-world identity attribution requires appropriate authorized investigative and legal processes outside TRACE-X. "
                    "This dossier provides digital correlation decision support for cybercrime intelligence. Digital persona convergence, "
                    "cryptocurrency cluster heuristics (CIOH), and network exit node associations do NOT prove real-world human citizen identity "
                    "or physical location. <i>Forensic Investigation Dossier — Not automatically legally admissible without judicial chain-of-custody corroboration.</i>",
                    disclaimer_text
                )
            ]
        ]
        disclaimer_table = Table(disclaimer_content, colWidths=[524])
        disclaimer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#EF4444")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ]))
        elements.append(disclaimer_table)
        elements.append(Spacer(1, 10))

        # -------------------------------------------------------------
        # 3. Report Integrity & Audit Verification Stamp
        # -------------------------------------------------------------
        chain_status_text = (
            "<font color='#047857'><b>VALID</b> (Verified from Genesis '0'*64)</font>"
            if meta["audit_chain_valid"]
            else f"<font color='#B91C1C'><b>INVALID</b> ({meta['audit_chain_error']})</font>"
        )
        integrity_rows = [
            [
                Paragraph("<b>Report Hash (SHA-256):</b>", body_style),
                Paragraph(meta["report_hash"], mono_small)
            ],
            [
                Paragraph("<b>Terminal Audit Hash:</b>", body_style),
                Paragraph(meta["terminal_audit_hash"], mono_small)
            ],
            [
                Paragraph("<b>Audit Chain Integrity:</b>", body_style),
                Paragraph(f"{chain_status_text} &nbsp;|&nbsp; <b>Verified Events:</b> {meta['verified_event_count']}", body_style)
            ],
            [
                Paragraph("<b>Generated At (UTC):</b>", body_style),
                Paragraph(f"{meta['generated_at']} &nbsp;|&nbsp; <b>Assessment ID:</b> {meta['assessment_id']}", body_style)
            ]
        ]
        integrity_table = Table(integrity_rows, colWidths=[130, 394])
        integrity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        elements.append(integrity_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 4. Section 1: Investigation Overview
        # -------------------------------------------------------------
        elements.append(Paragraph("1. Investigation Overview", section_heading))
        inv_overview_rows = [
            [
                Paragraph("<b>Investigation ID:</b>", body_style),
                Paragraph(inv["id"], body_style),
                Paragraph("<b>Title:</b>", body_style),
                Paragraph(inv["title"], body_style)
            ],
            [
                Paragraph("<b>Target Persona A:</b>", body_style),
                Paragraph(f"<font color='#0284C7'><b>{inv['persona_a']}</b></font>", body_style),
                Paragraph("<b>Target Persona B:</b>", body_style),
                Paragraph(f"<font color='#0284C7'><b>{inv['persona_b']}</b></font>", body_style)
            ],
            [
                Paragraph("<b>Assigned Analyst:</b>", body_style),
                Paragraph(inv["assigned_analyst_id"] or "ANALYST-001", body_style),
                Paragraph("<b>Scope Invariant:</b>", body_style),
                Paragraph("REAL-WORLD IDENTITY: NOT ESTABLISHED", body_bold)
            ]
        ]
        inv_table = Table(inv_overview_rows, colWidths=[95, 167, 95, 167])
        inv_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4)
        ]))
        elements.append(inv_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 5. Section 2: Attribution Determination & Fused Score
        # -------------------------------------------------------------
        elements.append(Paragraph("2. Attribution Determination & State Evaluation", section_heading))
        state_color = "#047857" if assess["attribution_state"] in ("LIKELY_LINK", "CONFIRMED_LINK") else (
            "#B91C1C" if assess["hard_gate_applied"] else "#64748B"
        )
        assess_rows = [
            [
                Paragraph("<b>Authoritative Base Score (S_base):</b>", body_style),
                Paragraph(f"<font size=11 color='#0284C7'><b>{assess['base_score']:.4f}</b></font>", body_style),
                Paragraph("<b>Attribution State:</b>", body_style),
                Paragraph(f"<font size=10 color='{state_color}'><b>{assess['attribution_state']}</b></font>", body_style)
            ],
            [
                Paragraph("<b>Confidence Band:</b>", body_style),
                Paragraph(f"<b>{assess['confidence_band']}</b>", body_style),
                Paragraph("<b>Level 2 Hard Gate:</b>", body_style),
                Paragraph("ACTIVE (Override to INCONCLUSIVE)" if assess["hard_gate_applied"] else "INACTIVE", body_style)
            ]
        ]
        assess_table = Table(assess_rows, colWidths=[140, 122, 122, 140])
        assess_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4)
        ]))
        elements.append(assess_table)
        elements.append(Spacer(1, 4))

        if assess["hard_gate_applied"]:
            c_rule = "TEMPORAL_CONCURRENCY_CLASH"
            hard_gate_box = [
                [
                    Paragraph(f"<font color='#991B1B'><b>LEVEL 2 HARD GATE ACTIVE: {c_rule}</b></font>", body_bold)
                ],
                [
                    Paragraph(
                        f"<b>Triggering Reason:</b> {assess['hard_gate_reason']}<br/>"
                        f"<b>Operational Impact:</b> Forced override of fused score to <b>INCONCLUSIVE</b> state (Confidence: <b>LOW</b>). "
                        f"Operationally incompatible under single-operator concurrency constraint.",
                        body_style
                    )
                ]
            ]
            hg_table = Table(hard_gate_box, colWidths=[524])
            hg_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DC2626")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ]))
            elements.append(hg_table)
            elements.append(Spacer(1, 4))

        elements.append(Paragraph(f"<b>Operational Rationale:</b> {assess['rationale']}", body_style))
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 6. Section 3: 5-Dimension Radar Breakdown Table
        # -------------------------------------------------------------
        elements.append(Paragraph("3. Five-Dimensional Evidence Contribution Breakdown", section_heading))
        elements.append(Paragraph(
            "<b>Formula:</b> S_base = sum(w_i &times; adjusted_score_i), where adjusted_score_i = raw_score_i &times; reliability_factor_i.",
            body_style
        ))
        elements.append(Spacer(1, 4))

        radar_headers = [
            Paragraph("DIMENSION", table_header_style),
            Paragraph("RAW SCORE", table_header_style),
            Paragraph("RELIABILITY", table_header_style),
            Paragraph("ADJUSTED", table_header_style),
            Paragraph("WEIGHT", table_header_style),
            Paragraph("CONTRIBUTION", table_header_style)
        ]
        radar_table_rows = [radar_headers]

        default_weights = {
            "CRYPTOGRAPHIC": 0.30,
            "FINANCIAL": 0.25,
            "STYLOMETRIC": 0.20,
            "INFRASTRUCTURE": 0.15,
            "BEHAVIORAL_TEMPORAL": 0.10
        }
        for d_name in ["CRYPTOGRAPHIC", "FINANCIAL", "STYLOMETRIC", "INFRASTRUCTURE", "BEHAVIORAL_TEMPORAL"]:
            sig = dims.get(d_name.lower()) or dims.get(d_name.upper()) or {}
            raw = float(sig.get("raw_score", 0.0))
            rel = float(sig.get("reliability_factor", 1.0))
            adj = float(sig.get("adjusted_score", raw * rel))
            w = float(sig.get("configured_weight", default_weights[d_name]))
            contrib = adj * w

            rel_text = f"{rel:.2f}"
            if rel < 1.0:
                rel_text += " (Dampened)"

            radar_table_rows.append([
                Paragraph(d_name.replace("_", " "), table_cell_style),
                Paragraph(f"{raw:.4f}", table_cell_style),
                Paragraph(rel_text, table_cell_style),
                Paragraph(f"{adj:.4f}", table_cell_style),
                Paragraph(f"{w:.2f}", table_cell_style),
                Paragraph(f"{contrib:.4f}", table_cell_style)
            ])

        # Summary total row
        radar_table_rows.append([
            Paragraph("<b>TOTAL FUSED S_base</b>", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("<b>1.00</b>", table_cell_style),
            Paragraph(f"<b>{assess['base_score']:.4f}</b>", table_cell_style)
        ])

        radar_table = Table(radar_table_rows, colWidths=[134, 78, 88, 74, 60, 90])
        radar_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
            ("PADDING", (0, 0), (-1, -1), 3.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT")
        ]))
        elements.append(radar_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 7. Section 4: Operational Contradictions & Level 1 / Level 2 Gates
        # -------------------------------------------------------------
        elements.append(Paragraph("4. Operational Contradictions & Level 1 / Level 2 Gates", section_heading))
        if not data["contradictions"]:
            elements.append(Paragraph("✓ No contradictory findings recorded for this investigation.", body_style))
        else:
            contra_rows = [
                [
                    Paragraph("LEVEL", table_header_style),
                    Paragraph("CONTRADICTION TYPE", table_header_style),
                    Paragraph("IMPACT & OPERATIONAL ASSESSMENT", table_header_style)
                ]
            ]
            for c in data["contradictions"]:
                level_str = "LEVEL 1 (Channel)" if c.get("level") == "LEVEL_1_CHANNEL_DAMPENING" else "LEVEL 2 (Hard Gate)"
                c_type = c.get("contradiction_type", "UNKNOWN")
                expl = c.get("explanation", "")
                if c.get("level") == "LEVEL_2_HARD_GATE":
                    expl = f"<b>FORCED OVERRIDE TO INCONCLUSIVE:</b> {expl}"
                elif c.get("dampening_factor"):
                    expl = f"Dampened channel factor by {c['dampening_factor']:.2f}&times;. {expl}"

                contra_rows.append([
                    Paragraph(level_str, table_cell_style),
                    Paragraph(f"<b>{c_type}</b>", table_cell_style),
                    Paragraph(expl, table_cell_style)
                ])
            contra_table = Table(contra_rows, colWidths=[90, 160, 274])
            contra_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4)
            ]))
            elements.append(contra_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 8. Section 5: Evidence Source Reliability & Trust Tiers
        # -------------------------------------------------------------
        elements.append(Paragraph("5. Evidence Source Reliability & Trust Tiers (Decision #10)", section_heading))
        elements.append(Paragraph(
            "<b>Formula:</b> R = 0.40(Reputation) + 0.30(Freshness) + 0.20(Corroboration) + 0.10(Consistency). "
            "Channel Modifier = 0.50 + 0.50 &times; R in [0.50, 1.00].",
            body_style
        ))
        elements.append(Spacer(1, 4))

        src_rows = [
            [
                Paragraph("SOURCE URI", table_header_style),
                Paragraph("TRUST TIER", table_header_style),
                Paragraph("CLASS", table_header_style),
                Paragraph("R SCORE", table_header_style),
                Paragraph("MODIFIER", table_header_style),
                Paragraph("FACTORS (Rep / Fr / Corr / Cons)", table_header_style)
            ]
        ]
        for s in data["source_reliabilities"]:
            factors_str = f"{s['reputation']:.2f} / {s['freshness']:.2f} / {s['corroboration']:.2f} / {s['consistency']:.2f}"
            src_rows.append([
                Paragraph(s["source_uri"], table_cell_style),
                Paragraph(s["trust_tier"], table_cell_style),
                Paragraph(s["reliability_class"], table_cell_style),
                Paragraph(f"{s['reliability_score']:.4f}", table_cell_style),
                Paragraph(f"{s['channel_modifier']:.4f}&times;", table_cell_style),
                Paragraph(factors_str, table_cell_style)
            ])
        src_table = Table(src_rows, colWidths=[144, 90, 48, 52, 60, 130])
        src_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 3.5)
        ]))
        elements.append(src_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 9. Section 6: Blockchain & Financial Intelligence
        # -------------------------------------------------------------
        elements.append(Paragraph("6. Blockchain & Financial Intelligence", section_heading))
        if not data["blockchain_findings"]:
            elements.append(Paragraph("No specific financial peeling or collaborative mixing patterns flagged.", body_style))
        else:
            fin_rows = [
                [
                    Paragraph("FINDING TYPE", table_header_style),
                    Paragraph("OBSERVATION & HEURISTIC ASSESSMENT", table_header_style)
                ]
            ]
            for f in data["blockchain_findings"]:
                fin_rows.append([
                    Paragraph(f.get("type", "FINANCIAL_FINDING"), table_cell_style),
                    Paragraph(f.get("description", str(f)), table_cell_style)
                ])
            fin_table = Table(fin_rows, colWidths=[144, 380])
            fin_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4)
            ]))
            elements.append(fin_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 10. Section 7: Machine Learning & Engine Provenance
        # -------------------------------------------------------------
        elements.append(Paragraph("7. Machine Learning & Analytical Engine Provenance", section_heading))
        prov_rows = [
            [
                Paragraph("<b>Stylometry Engine:</b>", body_style),
                Paragraph(f"{model_prov['engine']} ({model_prov['model_name']})", body_style),
                Paragraph("<b>Embedding Dimensions:</b>", body_style),
                Paragraph(str(model_prov["embedding_dimensions"]), body_style)
            ],
            [
                Paragraph("<b>Corpus Guardrail:</b>", body_style),
                Paragraph(model_prov["stylometry_guardrail"], body_style),
                Paragraph("<b>Deterministic Fallback:</b>", body_style),
                Paragraph("SHA-256 Projected 64-dim L2 Normalized", body_style)
            ]
        ]
        prov_table = Table(prov_rows, colWidths=[114, 188, 114, 108])
        prov_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4)
        ]))
        elements.append(prov_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 11. Section 8: Evidence Inventory & Cryptographic Hashes
        # -------------------------------------------------------------
        elements.append(Paragraph("8. Normalized Evidence Inventory & Cryptographic Hashes", section_heading))
        ev_rows = [
            [
                Paragraph("EVIDENCE ID", table_header_style),
                Paragraph("TYPE", table_header_style),
                Paragraph("SOURCE URI", table_header_style),
                Paragraph("COLLECTED AT (UTC)", table_header_style),
                Paragraph("CONTENT HASH (SHA-256)", table_header_style)
            ]
        ]
        for ev in data["evidence_inventory"]:
            ev_rows.append([
                Paragraph(f"<b>{ev['evidence_id']}</b>", table_cell_style),
                Paragraph(ev["artifact_type"], table_cell_style),
                Paragraph(ev["source_uri"], table_cell_style),
                Paragraph(ev["collected_at"][:19], table_cell_style),
                Paragraph(ev["content_hash"], table_cell_mono)
            ])
        ev_table = Table(ev_rows, colWidths=[88, 76, 120, 90, 150])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 3)
        ]))
        elements.append(ev_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 12. Section 9: Human-in-the-Loop Analyst Decisions
        # -------------------------------------------------------------
        elements.append(Paragraph("9. Human-in-the-Loop Analyst Decisions", section_heading))
        if not data["analyst_decisions"]:
            elements.append(Paragraph("No analyst manual review decisions recorded yet.", body_style))
        else:
            dec_rows = [
                [
                    Paragraph("TIMESTAMP (UTC)", table_header_style),
                    Paragraph("ANALYST ID", table_header_style),
                    Paragraph("DECISION", table_header_style),
                    Paragraph("OPERATIONAL RATIONALE", table_header_style)
                ]
            ]
            for d in data["analyst_decisions"]:
                dec_rows.append([
                    Paragraph(d["timestamp"][:19], table_cell_style),
                    Paragraph(d["analyst_id"], table_cell_style),
                    Paragraph(f"<b>{d['action']}</b>", table_cell_style),
                    Paragraph(d["rationale"], table_cell_style)
                ])
            dec_table = Table(dec_rows, colWidths=[100, 84, 80, 260])
            dec_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4)
            ]))
            elements.append(dec_table)
        elements.append(Spacer(1, 12))

        # -------------------------------------------------------------
        # 13. Section 10: Cryptographic Chain-of-Custody Audit Ledger
        # -------------------------------------------------------------
        elements.append(Paragraph("10. Cryptographic Audit Ledger & Investigation Chain", section_heading))
        elements.append(Paragraph(
            f"<b>Chain Integrity:</b> {chain_status_text} &nbsp;|&nbsp; "
            f"<b>Events Count:</b> {meta['verified_event_count']} &nbsp;|&nbsp; "
            f"<b>Terminal Hash:</b> <font name='Courier' size=7>{meta['terminal_audit_hash'][:24]}...</font>",
            body_style
        ))
        elements.append(Spacer(1, 4))

        audit_table_rows = [
            [
                Paragraph("ACTION", table_header_style),
                Paragraph("ANALYST", table_header_style),
                Paragraph("PREVIOUS HASH (SHA-256)", table_header_style),
                Paragraph("EVENT HASH (SHA-256)", table_header_style)
            ]
        ]
        for a in data["audit_trail"]:
            audit_table_rows.append([
                Paragraph(a["action"], table_cell_style),
                Paragraph(a["analyst_id"], table_cell_style),
                Paragraph(a["previous_hash"], table_cell_mono),
                Paragraph(a["event_hash"], table_cell_mono)
            ])

        audit_table = Table(audit_table_rows, colWidths=[114, 70, 170, 170])
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 2.8)
        ]))
        elements.append(audit_table)

        # Build PDF using NumberedCanvas
        doc.build(elements, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
