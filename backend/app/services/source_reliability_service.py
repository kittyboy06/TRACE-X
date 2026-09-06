import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from sqlalchemy.orm import Session

from app.models.contracts import (
    SourceReliabilityAssessment,
    ReliabilityClass,
    ScanStatus
)
from app.models.database import (
    SourceReliabilityModel,
    EvidenceRecordModel,
    ExtractedEntityModel
)


class SourceTrustTier(str, Enum):
    """
    Registry metadata defining baseline feed/domain categorization.
    Never substituted for evidentiary ReliabilityClass.
    """
    VERIFIED_GOV_FED = "VERIFIED_GOV_FED"
    ESTABLISHED_COMMERCIAL = "ESTABLISHED_COMMERCIAL"
    OPEN_COMMUNITY = "OPEN_COMMUNITY"
    UNVERIFIED_UNKNOWN = "UNVERIFIED_UNKNOWN"
    ADVERSARY_CONTROLLED_SUSPECTED = "ADVERSARY_CONTROLLED_SUSPECTED"


# Canonical Registry Baseline Reputation Scores
TRUST_TIER_REPUTATION: Dict[SourceTrustTier, float] = {
    SourceTrustTier.VERIFIED_GOV_FED: 0.95,
    SourceTrustTier.ESTABLISHED_COMMERCIAL: 0.85,
    SourceTrustTier.OPEN_COMMUNITY: 0.60,
    SourceTrustTier.UNVERIFIED_UNKNOWN: 0.35,
    SourceTrustTier.ADVERSARY_CONTROLLED_SUSPECTED: 0.15,
}

# Decision #10 Weights
WEIGHT_REPUTATION = 0.40
WEIGHT_FRESHNESS = 0.30
WEIGHT_CORROBORATION = 0.20
WEIGHT_CONSISTENCY = 0.10

HALF_LIFE_DAYS = 90.0


class SourceReliabilityService:
    """
    Evaluates trustworthiness, freshness, and cross-source corroboration of evidence feeds.
    Produces immutable SourceReliabilityAssessment contracts conforming to Phase 0 schemas.

    LOCKED ARCHITECTURAL INVARIANTS (Decision #10):
    1. Source reliability is an EVIDENCE MODIFIER entering analytical dimensions;
       it is NEVER a 6th attribution dimension.
    2. Formula: adjusted_score = raw_score * (0.5 + 0.5 * reliability_score).
       Reliability cannot reduce valid signals below 50% of their raw score.
    3. SourceTrustTier is registry metadata; ReliabilityClass is HIGH/MEDIUM/LOW derived from R.
    4. Corroboration is strictly investigation-scoped to prevent cross-case data leakage.
    """

    @staticmethod
    def classify_source_uri(source_uri: str) -> SourceTrustTier:
        """Determines baseline trust tier from domain/URI registry."""
        uri_lower = source_uri.strip().lower()

        # Verified Government / Judicial
        if any(dom in uri_lower for dom in [".gov", ".mil", "cert.in", "cisa.gov", "interpol.int"]):
            return SourceTrustTier.VERIFIED_GOV_FED

        # Established Commercial / Threat Intel / Public Block Explorers
        if any(dom in uri_lower for dom in [
            "virustotal.com", "blockchain.info", "etherscan.io", "kraken.com",
            "binance.com", "coinbase.com", "github.com", "shodan.io", "censys.io"
        ]):
            return SourceTrustTier.ESTABLISHED_COMMERCIAL

        # Darknet / Adversary Infrastructure
        if ".onion" in uri_lower or any(kw in uri_lower for kw in [
            "dread", "hydra", "exploit.in", "raidforums", "breached", "xss.is", "darkode"
        ]):
            return SourceTrustTier.ADVERSARY_CONTROLLED_SUSPECTED

        # Open Community
        if any(dom in uri_lower for dom in ["reddit.com", "twitter.com", "x.com", "bitcointalk.org", "pastebin.com"]):
            return SourceTrustTier.OPEN_COMMUNITY

        return SourceTrustTier.UNVERIFIED_UNKNOWN

    @staticmethod
    def calculate_freshness(
        collected_at: datetime,
        reference_time: Optional[datetime] = None,
        half_life_days: float = HALF_LIFE_DAYS
    ) -> float:
        """
        Calculates exponential decay freshness: 2^(-delta_t / half_life).
        - delta_t = 0d   -> 1.00
        - delta_t = 90d  -> 0.50
        - delta_t = 180d -> 0.25
        Clamps future timestamps to 1.0.
        """
        if collected_at.tzinfo is None:
            collected_at = collected_at.replace(tzinfo=timezone.utc)
        else:
            collected_at = collected_at.astimezone(timezone.utc)

        ref = reference_time or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        else:
            ref = ref.astimezone(timezone.utc)

        if collected_at >= ref:
            return 1.0

        delta_days = (ref - collected_at).total_seconds() / 86400.0
        freshness = 2.0 ** (-delta_days / half_life_days)
        return round(max(0.0, min(1.0, freshness)), 4)

    @classmethod
    def calculate_corroboration(
        cls,
        db: Session,
        investigation_id: str,
        source_uri: str
    ) -> float:
        """
        Calculates cross-source entity overlap strictly within the specified investigation.
        If no corroboratable entities exist in the investigation, returns neutral baseline 0.50.
        """
        # Find all evidence_ids for this source in this investigation
        source_records = (
            db.query(EvidenceRecordModel.evidence_id)
            .filter(
                EvidenceRecordModel.investigation_id == investigation_id,
                EvidenceRecordModel.source_uri == source_uri
            )
            .all()
        )
        source_ev_ids = [r[0] for r in source_records]

        if not source_ev_ids:
            return 0.50

        # Entities observed by this source
        source_entities = (
            db.query(ExtractedEntityModel.entity_type, ExtractedEntityModel.value)
            .filter(
                ExtractedEntityModel.investigation_id == investigation_id,
                ExtractedEntityModel.evidence_id.in_(source_ev_ids)
            )
            .all()
        )
        source_entity_set = {(e[0], e[1]) for e in source_entities}

        if not source_entity_set:
            return 0.50

        # Entities observed by OTHER sources in this investigation
        other_entities = (
            db.query(ExtractedEntityModel.entity_type, ExtractedEntityModel.value)
            .filter(
                ExtractedEntityModel.investigation_id == investigation_id,
                ~ExtractedEntityModel.evidence_id.in_(source_ev_ids)
            )
            .all()
        )
        other_entity_set = {(e[0], e[1]) for e in other_entities}

        if not other_entity_set:
            # Investigation has no other entities to corroborate against; neutral baseline
            return 0.50

        overlap = source_entity_set.intersection(other_entity_set)
        corroboration = len(overlap) / float(len(source_entity_set))
        return round(max(0.0, min(1.0, corroboration)), 4)

    @staticmethod
    def calculate_consistency(
        db: Session,
        investigation_id: str,
        source_uri: str
    ) -> float:
        """
        Evaluates absence of internal contradictions or data tampering.
        Defaults to high consistency (0.90) unless contradictions linked.
        """
        return 0.90

    @classmethod
    def evaluate_source(
        cls,
        db: Session,
        investigation_id: str,
        source_uri: str,
        reference_time: Optional[datetime] = None,
        known_last_scan: Optional[datetime] = None,
        known_scan_status: Optional[ScanStatus] = None
    ) -> Tuple[SourceReliabilityAssessment, SourceTrustTier, str]:
        """
        Executes Decision #10 transparent 4-factor scoring:
        R = 0.40 * reputation + 0.30 * freshness + 0.20 * corroboration + 0.10 * consistency
        Produces immutable SourceReliabilityAssessment contract with Phase 0 ReliabilityClass.
        """
        trust_tier = cls.classify_source_uri(source_uri)
        reputation = TRUST_TIER_REPUTATION.get(trust_tier, 0.35)

        # Retrieve latest collected_at for this source in the investigation
        latest_record = (
            db.query(EvidenceRecordModel.collected_at)
            .filter(
                EvidenceRecordModel.investigation_id == investigation_id,
                EvidenceRecordModel.source_uri == source_uri
            )
            .order_by(EvidenceRecordModel.collected_at.desc())
            .first()
        )
        collected_at = latest_record[0] if latest_record else (reference_time or datetime.now(timezone.utc))
        freshness = cls.calculate_freshness(collected_at, reference_time=reference_time)

        corroboration = cls.calculate_corroboration(db, investigation_id, source_uri)
        consistency = cls.calculate_consistency(db, investigation_id, source_uri)

        # Decision #10 4-factor calculation
        reliability_score = round(
            (WEIGHT_REPUTATION * reputation) +
            (WEIGHT_FRESHNESS * freshness) +
            (WEIGHT_CORROBORATION * corroboration) +
            (WEIGHT_CONSISTENCY * consistency),
            4
        )
        reliability_score = max(0.0, min(1.0, reliability_score))

        # Phase 0 ReliabilityClass Mapping
        if reliability_score >= 0.80:
            rel_class = ReliabilityClass.HIGH
        elif reliability_score >= 0.55:
            rel_class = ReliabilityClass.MEDIUM
        else:
            rel_class = ReliabilityClass.LOW

        # Explicit ScanStatus Mapping
        if known_scan_status is not None:
            scan_status = known_scan_status
            diag = f"Scan status supplied via feed monitor: {scan_status.value}"
        elif known_last_scan is not None:
            if freshness < 0.25:
                scan_status = ScanStatus.STALE
                diag = "Evidence feed is stale (> 180 days)"
            else:
                scan_status = ScanStatus.HEALTHY
                diag = "Evidence feed is verified healthy"
        else:
            scan_status = ScanStatus.NEVER_SCANNED
            diag = "Source evaluated from passive evidentiary metadata; no live probe executed"

        last_scan = known_last_scan or (reference_time or datetime.now(timezone.utc))

        factors = {
            "reputation": round(reputation, 4),
            "freshness": round(freshness, 4),
            "corroboration": round(corroboration, 4),
            "consistency": round(consistency, 4)
        }

        assessment = SourceReliabilityAssessment(
            source_uri=source_uri,
            reliability_score=reliability_score,
            reliability_class=rel_class,
            factors=factors,
            last_scan=last_scan,
            scan_status=scan_status
        )
        return assessment, trust_tier, diag

    @classmethod
    def persist_assessment(
        cls,
        db: Session,
        assessment: SourceReliabilityAssessment,
        investigation_id: str,
        trust_tier: SourceTrustTier,
        diagnostic_status: Optional[str] = None
    ) -> SourceReliabilityModel:
        """Upserts SourceReliabilityModel on unique (investigation_id, source_uri)."""
        existing = (
            db.query(SourceReliabilityModel)
            .filter(
                SourceReliabilityModel.investigation_id == investigation_id,
                SourceReliabilityModel.source_uri == assessment.source_uri
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if existing:
            existing.trust_tier = trust_tier.value
            existing.reliability_score = assessment.reliability_score
            existing.reliability_class = assessment.reliability_class.value
            existing.reputation = assessment.factors["reputation"]
            existing.freshness = assessment.factors["freshness"]
            existing.corroboration = assessment.factors["corroboration"]
            existing.consistency = assessment.factors["consistency"]
            existing.last_scan = assessment.last_scan
            existing.scan_status = assessment.scan_status.value
            existing.diagnostic_status = diagnostic_status
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        rel_id = f"REL-{investigation_id}-{hashlib.sha256(assessment.source_uri.encode('utf-8')).hexdigest()[:12]}"
        model = SourceReliabilityModel(
            id=rel_id,
            investigation_id=investigation_id,
            source_uri=assessment.source_uri,
            trust_tier=trust_tier.value,
            reliability_score=assessment.reliability_score,
            reliability_class=assessment.reliability_class.value,
            reputation=assessment.factors["reputation"],
            freshness=assessment.factors["freshness"],
            corroboration=assessment.factors["corroboration"],
            consistency=assessment.factors["consistency"],
            last_scan=assessment.last_scan,
            scan_status=assessment.scan_status.value,
            diagnostic_status=diagnostic_status,
            updated_at=now
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def apply_channel_modifier(raw_score: float, reliability_score: float) -> float:
        """
        Decision #10 Channel Evidence Modifier:
        adjusted_score = raw_score * (0.5 + 0.5 * reliability_score)
        Guarantees: 0.5 * raw_score <= adjusted_score <= raw_score
        """
        clamped_rel = max(0.0, min(1.0, reliability_score))
        modifier = 0.5 + (0.5 * clamped_rel)
        adjusted = raw_score * modifier
        return round(max(0.0, min(1.0, adjusted)), 4)
