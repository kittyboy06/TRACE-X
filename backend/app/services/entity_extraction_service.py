import re
import hashlib
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session

from app.models.contracts import ExtractedEntity, EntityType, NormalizedArtifact
from app.models.database import ExtractedEntityModel

# Regular Expressions for Deterministic Entity Parsing
BITCOIN_BASE58_REGEX = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
BITCOIN_BECH32_REGEX = re.compile(r"\bbc1[a-z0-9]{25,62}\b", re.IGNORECASE)
ETHEREUM_WALLET_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
IPV4_REGEX = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
ONION_REGEX = re.compile(r"\b[a-z0-9]{16,56}\.onion\b", re.IGNORECASE)
DOMAIN_REGEX = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|in|io|is|to|cc|su|me|ru)\b", re.IGNORECASE)
PGP_FINGERPRINT_REGEX = re.compile(r"\b[0-9a-fA-F]{32,40}\b")
PGP_KEY_ID_REGEX = re.compile(r"\b0x[0-9a-fA-F]{6,16}\b", re.IGNORECASE)


class EntityExtractionService:
    """
    Extracts discrete technical, cryptographic, and network indicators from
    normalized evidentiary artifacts into immutable ExtractedEntity contracts.

    IMPORTANT SEMANTIC PRINCIPLES:
    1. Extraction confidence represents PARSER confidence that the indicator was correctly
       parsed from the raw text/format; it DOES NOT imply attribution, identity, or ownership.
    2. Extracted indicators reflect evidence observation ('OBSERVED_IN_EVIDENCE'), NOT persona
       guilt or ownership conclusions.
    """

    @staticmethod
    def generate_entity_id(evidence_id: str, entity_type: EntityType, value: str) -> str:
        """Deterministically generates entity_id scoped by evidence_id, entity_type, and value."""
        canon = f"{evidence_id}:{entity_type.value}:{value.strip().lower()}"
        return f"ENT-{hashlib.sha256(canon.encode('utf-8')).hexdigest()[:16]}"

    @classmethod
    def extract_entities(cls, artifact: NormalizedArtifact) -> List[ExtractedEntity]:
        """
        Parses indicators from a NormalizedArtifact into immutable ExtractedEntity contracts.
        Enforces Phase 0 canonical EntityType values only.
        """
        payload = artifact.normalized_payload
        evidence_id = artifact.evidence_id
        entities: List[ExtractedEntity] = []
        seen: Set[str] = set()

        def add_entity(entity_type: EntityType, value: str, confidence: float):
            clean_val = value.strip()
            if not clean_val:
                return
            key = (entity_type.value, clean_val.lower())
            if key in seen:
                return
            seen.add(key)
            eid = cls.generate_entity_id(evidence_id, entity_type, clean_val)
            entities.append(ExtractedEntity(
                entity_id=eid,
                entity_type=entity_type,
                value=clean_val,
                evidence_id=evidence_id,
                confidence=round(confidence, 4)
            ))

        # 1. PERSONA Extraction
        # Look for explicit persona declarations
        if "persona" in payload and isinstance(payload["persona"], str):
            add_entity(EntityType.PERSONA, payload["persona"], 0.95)

        # 2. PGP FINGERPRINT Extraction
        if "key_fingerprint" in payload and isinstance(payload["key_fingerprint"], str):
            add_entity(EntityType.PGP_FINGERPRINT, payload["key_fingerprint"], 1.0)
        elif "key_id" in payload and isinstance(payload["key_id"], str):
            add_entity(EntityType.PGP_FINGERPRINT, payload["key_id"], 0.95)

        # 3. WALLET Extraction (Bitcoin & Ethereum)
        if "wallet_address" in payload and isinstance(payload["wallet_address"], str):
            add_entity(EntityType.WALLET, payload["wallet_address"], 1.0)
        if "sender_address" in payload and isinstance(payload["sender_address"], str):
            add_entity(EntityType.WALLET, payload["sender_address"], 1.0)
        if "receiver_address" in payload and isinstance(payload["receiver_address"], str):
            add_entity(EntityType.WALLET, payload["receiver_address"], 1.0)

        # 4. IP_ENDPOINT Extraction
        if "origin_ip" in payload and isinstance(payload["origin_ip"], str):
            add_entity(EntityType.IP_ENDPOINT, payload["origin_ip"], 1.0)
        if "relay_ip" in payload and isinstance(payload["relay_ip"], str):
            add_entity(EntityType.IP_ENDPOINT, payload["relay_ip"], 1.0)
        if "ip_address" in payload and isinstance(payload["ip_address"], str):
            add_entity(EntityType.IP_ENDPOINT, payload["ip_address"], 1.0)

        # 5. DOMAIN & ONION_SERVICE Extraction
        if "domain" in payload and isinstance(payload["domain"], str):
            dom = payload["domain"]
            if dom.lower().endswith(".onion"):
                add_entity(EntityType.ONION_SERVICE, dom, 1.0)
            else:
                add_entity(EntityType.DOMAIN, dom, 0.95)

        # 6. CERTIFICATE Extraction
        if "cert_fingerprint" in payload and isinstance(payload["cert_fingerprint"], str):
            add_entity(EntityType.CERTIFICATE, payload["cert_fingerprint"], 1.0)
        if "tls_sha256" in payload and isinstance(payload["tls_sha256"], str):
            add_entity(EntityType.CERTIFICATE, payload["tls_sha256"], 1.0)

        # 7. Deep Text Parsing (for forum posts, narratives, or raw message text)
        text_content = ""
        if "post_text" in payload and isinstance(payload["post_text"], str):
            text_content += " " + payload["post_text"]
        if "message" in payload and isinstance(payload["message"], str):
            text_content += " " + payload["message"]

        if text_content:
            # Match BTC Base58 Wallets
            for btc in BITCOIN_BASE58_REGEX.findall(text_content):
                add_entity(EntityType.WALLET, btc, 1.0)
            # Match BTC Bech32 Wallets
            for bech in BITCOIN_BECH32_REGEX.findall(text_content):
                add_entity(EntityType.WALLET, bech, 1.0)
            # Match ETH Wallets
            for eth in ETHEREUM_WALLET_REGEX.findall(text_content):
                add_entity(EntityType.WALLET, eth, 1.0)
            # Match Onion Services
            for on in ONION_REGEX.findall(text_content):
                add_entity(EntityType.ONION_SERVICE, on, 1.0)
            # Match IPv4 Endpoints
            for ip in IPV4_REGEX.findall(text_content):
                add_entity(EntityType.IP_ENDPOINT, ip, 1.0)
            # Match Key IDs
            for kid in PGP_KEY_ID_REGEX.findall(text_content):
                add_entity(EntityType.PGP_FINGERPRINT, kid, 0.90)

        return entities

    @classmethod
    def persist_entities(
        cls,
        db: Session,
        entities: List[ExtractedEntity],
        investigation_id: str
    ) -> List[ExtractedEntityModel]:
        """
        Persists extracted entities into the database with deduplication across
        (investigation_id, evidence_id, entity_type, value).
        """
        persisted: List[ExtractedEntityModel] = []
        for ent in entities:
            existing = (
                db.query(ExtractedEntityModel)
                .filter(
                    ExtractedEntityModel.investigation_id == investigation_id,
                    ExtractedEntityModel.evidence_id == ent.evidence_id,
                    ExtractedEntityModel.entity_type == ent.entity_type.value,
                    ExtractedEntityModel.value == ent.value
                )
                .first()
            )
            if not existing:
                record = ExtractedEntityModel(
                    entity_id=ent.entity_id,
                    investigation_id=investigation_id,
                    evidence_id=ent.evidence_id,
                    entity_type=ent.entity_type.value,
                    value=ent.value,
                    confidence=ent.confidence
                )
                db.add(record)
                persisted.append(record)
            else:
                persisted.append(existing)

        db.commit()
        return persisted
