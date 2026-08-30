import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, EvidenceRecordModel
from app.services.ingestion_service import IngestionService, compute_sha256

# In-memory SQLite for testing
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_sha256_deterministic_hashing():
    payload_a = {"author": "Ghost", "timestamp": "2026-01-01T00:00:00Z", "id": 123}
    payload_b = {"id": 123, "timestamp": "2026-01-01T00:00:00Z", "author": "Ghost"}
    
    # Key ordering shouldn't change hash
    assert compute_sha256(payload_a) == compute_sha256(payload_b)


def test_artifact_provenance_and_deduplication():
    db = TestingSession()
    raw_artifact = {
        "source_uri": "dread.onion/thread/999",
        "artifact_type": "FORUM_POST",
        "raw_payload": {"text": "Custom exploit release", "language": "en"}
    }

    # Ingest first time
    rec1 = IngestionService.process_and_store_artifact(db, "INV-TEST-001", raw_artifact)
    assert rec1.content_hash is not None
    assert rec1.provenance_chain == ["RAW_INGEST", "NORMALIZED"]

    # Ingest exact duplicate
    rec2 = IngestionService.process_and_store_artifact(db, "INV-TEST-001", raw_artifact)
    assert rec1.content_hash == rec2.content_hash

    # Ensure single DB row exists within INV-TEST-001
    count = db.query(EvidenceRecordModel).filter(
        EvidenceRecordModel.investigation_id == "INV-TEST-001",
        EvidenceRecordModel.content_hash == rec1.content_hash
    ).count()
    assert count == 1

    # Ingest same artifact under a distinct investigation (cross-investigation reference)
    rec3 = IngestionService.process_and_store_artifact(db, "INV-TEST-002", raw_artifact)
    assert rec3.content_hash == rec1.content_hash
    
    total_count = db.query(EvidenceRecordModel).filter(
        EvidenceRecordModel.content_hash == rec1.content_hash
    ).count()
    assert total_count == 2
    db.close()
