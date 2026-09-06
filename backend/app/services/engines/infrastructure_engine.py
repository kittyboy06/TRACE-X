from typing import List, Dict, Any, Optional
from app.models.contracts import (
    DimensionSignal,
    DimensionType,
    SignalStatus,
    ExtractedEntity,
    EntityType
)
from app.services.source_reliability_service import SourceReliabilityService


class InfrastructureEngine:
    """
    Canonical Infrastructure Correlation Engine.
    Analyzes authorized and synthetic server and network infrastructure metadata.

    LOCKED INVARIANTS:
    - Pure engine interface decoupled from database sessions.
    - Scope strictly limited to authorized/synthetic metadata: TLS certificates, SSH banners,
      server headers, known endpoint relationships, and synthetic circuit metadata.
    - Zero unrestricted live Tor probing or live network scanning.
    - Decision #10 channel modifier: adjusted_score = raw_score * (0.5 + 0.5 * R).
    """
    CANONICAL_WEIGHT = 0.15

    @classmethod
    def analyze(
        cls,
        artifacts: List[Dict[str, Any]],
        entities: Optional[List[ExtractedEntity]] = None,
        reliability_context: float = 1.0
    ) -> DimensionSignal:
        infra_artifacts = [
            a for a in artifacts
            if a.get("artifact_type") in ("INFRASTRUCTURE_HEADER", "INFRASTRUCTURE_METRICS", "NETWORK_TELEMETRY")
        ]
        infra_entities = [
            e for e in (entities or [])
            if getattr(e, "entity_type", None) in (
                EntityType.ONION_SERVICE,
                EntityType.DOMAIN,
                EntityType.CERTIFICATE,
                EntityType.IP_ENDPOINT
            )
        ]

        evidence_ids = [
            a.get("evidence_id") for a in infra_artifacts if a.get("evidence_id")
        ] + [
            getattr(e, "evidence_id", "") for e in infra_entities if getattr(e, "evidence_id", "")
        ]
        evidence_ids = sorted(list(set(filter(None, evidence_ids))))

        clamped_r = max(0.0, min(1.0, float(reliability_context)))
        reliability_factor = round(0.5 + 0.5 * clamped_r, 4)

        if not infra_artifacts and not infra_entities:
            return DimensionSignal(
                dimension=DimensionType.INFRASTRUCTURE,
                raw_score=0.0,
                reliability_factor=reliability_factor,
                adjusted_score=0.0,
                status=SignalStatus.NOT_ENOUGH_EVIDENCE,
                evidence_ids=[],
                engine_metadata={
                    "engine": "InfrastructureEngine",
                    "version": "1.0.0",
                    "operating_mode": "PASSIVE_METADATA_ONLY"
                },
                findings=[{"observation": "No server or network infrastructure telemetry available in evidence package."}]
            )

        findings = []
        rare_fingerprint_match = False
        shared_dedicated = False
        generic_cdn = False
        conflicting_infra = False
        observed_fingerprints = []

        for a in infra_artifacts:
            payload = a.get("raw_payload", {})
            if payload.get("rare_fingerprint_match"):
                rare_fingerprint_match = True
            if payload.get("shared_dedicated_ip") or payload.get("shared_hosting"):
                shared_dedicated = True
            if payload.get("generic_cdn") or payload.get("cloudflare_proxy"):
                generic_cdn = True
            if payload.get("conflicting_dedicated_nodes") or payload.get("conflicting_infrastructure"):
                conflicting_infra = True

            tls_serial = payload.get("tls_cert_serial") or payload.get("persona_a_infra", {}).get("tls_cert_serial")
            ssh_banner = payload.get("ssh_banner") or payload.get("persona_a_infra", {}).get("ssh_banner")
            if tls_serial or ssh_banner:
                observed_fingerprints.append({"tls_cert_serial": tls_serial, "ssh_banner": ssh_banner})

        # Evaluate scoring rules
        if rare_fingerprint_match or (observed_fingerprints and len(observed_fingerprints) >= 2 and observed_fingerprints[0] == observed_fingerprints[1]):
            raw_score = 0.65
            findings.append({
                "rule": "RARE_FINGERPRINT_MATCH",
                "evidence_strength": "HIGH",
                "observation": "Shared TLS certificate serial and identical SSH server daemon fingerprint identified across persona hosting endpoints."
            })
        elif shared_dedicated:
            raw_score = 0.50
            findings.append({
                "rule": "SHARED_DEDICATED_HOSTING",
                "evidence_strength": "MEDIUM",
                "observation": "Personas hosted on identical dedicated IP subnet or unique hosting provider."
            })
        elif conflicting_infra:
            raw_score = 0.10
            findings.append({
                "rule": "CONFLICTING_INFRASTRUCTURE",
                "evidence_strength": "LOW",
                "observation": "Evidence demonstrates disparate dedicated non-overlapping hosting infrastructure."
            })
        elif generic_cdn or infra_artifacts:
            raw_score = 0.20
            findings.append({
                "rule": "GENERIC_SHARED_INFRASTRUCTURE",
                "evidence_strength": "LOW",
                "observation": "Generic CDN / commercial hosting infrastructure; inconclusive fingerprint without dedicated indicator correlation."
            })
        else:
            raw_score = 0.20
            findings.append({
                "rule": "PASSIVE_ENDPOINT_OBSERVATION",
                "evidence_strength": "LOW",
                "observation": "Observed domain/onion endpoints without confirmed deep configuration overlap."
            })

        # Apply Decision #10 channel modifier
        adjusted_score = SourceReliabilityService.apply_channel_modifier(raw_score, clamped_r)

        # Enforce mathematical invariants
        assert 0.0 <= raw_score <= 1.0, f"Raw score out of bounds: {raw_score}"
        assert 0.0 <= clamped_r <= 1.0, f"Reliability out of bounds: {clamped_r}"
        assert (0.5 * raw_score) - 1e-4 <= adjusted_score <= raw_score + 1e-4, (
            f"Channel modifier invariant violated: {adjusted_score} not in [{0.5 * raw_score}, {raw_score}]"
        )

        return DimensionSignal(
            dimension=DimensionType.INFRASTRUCTURE,
            raw_score=raw_score,
            reliability_factor=reliability_factor,
            adjusted_score=adjusted_score,
            status=SignalStatus.VALID,
            evidence_ids=evidence_ids,
            engine_metadata={
                "engine": "InfrastructureEngine",
                "version": "1.0.0",
                "canonical_weight": cls.CANONICAL_WEIGHT,
                "operating_mode": "PASSIVE_METADATA_ONLY",
                "live_probing_executed": False
            },
            findings=findings
        )
