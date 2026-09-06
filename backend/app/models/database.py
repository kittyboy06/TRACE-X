from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

Base = declarative_base()


class InvestigationModel(Base):
    __tablename__ = "investigations"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    target_persona_a = Column(String, nullable=False)
    target_persona_b = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    assigned_analyst_id = Column(String, nullable=True, default="ANALYST-001")
    classification = Column(String, default="UNRESTRICTED")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class EvidenceRecordModel(Base):
    __tablename__ = "evidence_records"
    evidence_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, primary_key=True, index=True)
    source_uri = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)
    collected_at = Column(DateTime, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    raw_payload = Column(JSON, nullable=False)
    extractor_version = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    provenance_chain = Column(JSON, nullable=False)
    normalized_payload = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("investigation_id", "content_hash", name="uq_investigation_content_hash"),
    )


class ExtractedEntityModel(Base):
    __tablename__ = "extracted_entities"
    entity_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    evidence_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        UniqueConstraint("investigation_id", "evidence_id", "entity_type", "value", name="uq_investigation_evidence_entity"),
    )


class SourceReliabilityModel(Base):
    __tablename__ = "source_reliabilities"
    id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    source_uri = Column(String, nullable=False, index=True)
    trust_tier = Column(String, nullable=False)
    reliability_score = Column(Float, nullable=False)
    reputation = Column(Float, nullable=False)
    freshness = Column(Float, nullable=False)
    corroboration = Column(Float, nullable=False)
    consistency = Column(Float, nullable=False)
    reliability_class = Column(String, nullable=False)
    last_scan = Column(DateTime, nullable=False)
    scan_status = Column(String, nullable=False)
    diagnostic_status = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        UniqueConstraint("investigation_id", "source_uri", name="uq_investigation_source_uri"),
    )


class AttributionAssessmentModel(Base):
    __tablename__ = "attribution_assessments"
    assessment_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    attribution_state = Column(String, nullable=False)
    confidence_band = Column(String, nullable=False)
    base_score = Column(Float, nullable=False)
    evidence_score = Column(Float, nullable=False)
    real_world_identity = Column(String, default="NOT ESTABLISHED")
    is_current = Column(Boolean, default=True, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    audit_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    assessment_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    analyst_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    rationale = Column(Text, nullable=False)
    prior_state = Column(String, nullable=False)
    resulting_state = Column(String, nullable=False)
    previous_hash = Column(String, nullable=False, default="0" * 64)
    event_hash = Column(String, nullable=False, unique=True)


# Database Connection Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracex.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
