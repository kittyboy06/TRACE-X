import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.contracts import EntityType, ExtractedEntity, NormalizedArtifact, ArtifactType
from app.services.normalization_service import NormalizationService
from app.services.entity_extraction_service import EntityExtractionService
from app.models.database import SessionLocal, ExtractedEntityModel

client = TestClient(app)


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_frozen_entity_type_enum_compliance():
    """Verify that extracted entities adhere strictly to the Phase 0 frozen EntityType enum values."""
    raw_artifact = {
        "artifact_type": "FORUM_POST",
        "raw_payload": {
            "persona": "DarkSpecter",
            "key_fingerprint": "8F9B2D1C9B8A7C44E31055F6A901C4889B8A7C",
            "wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "domain": "secure-vault.onion",
            "origin_ip": "185.220.101.5",
            "tls_sha256": "3b7b85522e032906e0f317d7b93ff5ad2b1a8d0112440938f32bc1946059d047"
        }
    }
    norm = NormalizationService.normalize_artifact(raw_artifact, "INV-TEST-ENT-001")
    entities = EntityExtractionService.extract_entities(norm)

    allowed_types = {
        EntityType.PERSONA,
        EntityType.PGP_FINGERPRINT,
        EntityType.WALLET,
        EntityType.ONION_SERVICE,
        EntityType.DOMAIN,
        EntityType.CERTIFICATE,
        EntityType.IP_ENDPOINT
    }

    assert len(entities) >= 6
    for ent in entities:
        assert ent.entity_type in allowed_types
        # Invariants
        assert 0.0 <= ent.confidence <= 1.0
        assert ent.evidence_id == norm.evidence_id
        assert ent.entity_id.startswith("ENT-")
        assert len(ent.entity_id) == 20  # "ENT-" + 16 hex chars

    extracted_types = {e.entity_type for e in entities}
    assert EntityType.PERSONA in extracted_types
    assert EntityType.PGP_FINGERPRINT in extracted_types
    assert EntityType.WALLET in extracted_types
    assert EntityType.ONION_SERVICE in extracted_types
    assert EntityType.IP_ENDPOINT in extracted_types
    assert EntityType.CERTIFICATE in extracted_types

    # Ensure forbidden aliases are NOT present
    for ent in entities:
        assert ent.entity_type.value not in ["PGP_KEY", "CRYPTO_WALLET", "IP_ADDRESS", "TEMPORAL_BURST"]


def test_deep_text_entity_regex_parsing():
    """Verify regex extraction of crypto wallets, onion addresses, IPv4 headers, and PGP IDs from raw post text."""
    text = (
        "Send 0.5 BTC to 1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ or bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq. "
        "ETH accepted at 0x71C7656EC7ab88b098defB751B7401B5f6d8976F. "
        "Mirror active at ex4pyio3mgt62f6bpxd4s7pxh7lq63q5e5h67vj6t7h6s4z5x6c7v8b9.onion. "
        "Contact relay at 198.51.100.42. Key ID: 0x44E31055."
    )
    raw_artifact = {
        "artifact_type": "FORUM_POST",
        "raw_payload": {
            "post_text": text
        }
    }
    norm = NormalizationService.normalize_artifact(raw_artifact, "INV-TEXT-PARSING-01")
    entities = EntityExtractionService.extract_entities(norm)

    entity_map = {e.value: e.entity_type for e in entities}

    # BTC Base58
    assert "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ" in entity_map
    assert entity_map["1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ"] == EntityType.WALLET

    # BTC Bech32
    assert "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in entity_map
    assert entity_map["bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"] == EntityType.WALLET

    # ETH
    assert "0x71C7656EC7ab88b098defB751B7401B5f6d8976F" in entity_map
    assert entity_map["0x71C7656EC7ab88b098defB751B7401B5f6d8976F"] == EntityType.WALLET

    # Onion
    assert "ex4pyio3mgt62f6bpxd4s7pxh7lq63q5e5h67vj6t7h6s4z5x6c7v8b9.onion" in entity_map
    assert entity_map["ex4pyio3mgt62f6bpxd4s7pxh7lq63q5e5h67vj6t7h6s4z5x6c7v8b9.onion"] == EntityType.ONION_SERVICE

    # IP Endpoint
    assert "198.51.100.42" in entity_map
    assert entity_map["198.51.100.42"] == EntityType.IP_ENDPOINT

    # PGP Key ID
    assert "0x44E31055" in entity_map
    assert entity_map["0x44E31055"] == EntityType.PGP_FINGERPRINT


def test_extracted_entities_endpoint_and_scoping(lead_auditor_headers):
    """Verify GET /api/v1/ingestion/{investigation_id}/entities returns persisted entities."""
    # 1. Load benchmark 1
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=lead_auditor_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Query entities endpoint
    entities_resp = client.get(f"/api/v1/ingestion/{inv_id}/entities", headers=lead_auditor_headers)
    assert entities_resp.status_code == 200
    data = entities_resp.json()
    assert data["investigation_id"] == inv_id
    assert data["count"] > 0
    assert len(data["entities"]) == data["count"]

    first = data["entities"][0]
    assert "entity_id" in first
    assert "entity_type" in first
    assert "value" in first
    assert "confidence" in first
    assert 0.0 <= first["confidence"] <= 1.0
