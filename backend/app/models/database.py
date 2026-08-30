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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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


class AttributionAssessmentModel(Base):
    __tablename__ = "attribution_assessments"
    assessment_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    attribution_state = Column(String, nullable=False)
    confidence_band = Column(String, nullable=False)
    base_score = Column(Float, nullable=False)
    evidence_score = Column(Float, nullable=False)
    real_world_identity = Column(String, default="NOT ESTABLISHED")
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    audit_id = Column(String, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    assessment_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    analyst_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    rationale = Column(Text, nullable=False)
    prior_state = Column(String, nullable=False)
    resulting_state = Column(String, nullable=False)
    event_hash = Column(String, nullable=False, unique=True)


# Database Connection Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracex.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
