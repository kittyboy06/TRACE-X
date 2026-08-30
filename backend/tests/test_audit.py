import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, AuditEventModel
from app.models.schemas import AuditDecisionRequest, AnalystAction
from app.api.endpoints.audit import record_analyst_decision

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_append_only_audit_event():
    db = TestingSession()
    
    req1 = AuditDecisionRequest(
        investigation_id="INV-TEST-001",
        assessment_id="ASSESS-001",
        action=AnalystAction.CONFIRMED,
        analyst_id="ANALYST-LEAD-01",
        rationale="Corroborated across PGP and wallet CIOH cluster."
    )
    event1 = record_analyst_decision(req1, db)
    assert event1.event_hash is not None
    assert event1.action == AnalystAction.CONFIRMED

    # Log second decision (e.g. subsequent review step)
    req2 = AuditDecisionRequest(
        investigation_id="INV-TEST-001",
        assessment_id="ASSESS-001",
        action=AnalystAction.INVESTIGATE,
        analyst_id="ANALYST-SEC-02",
        rationale="Requesting additional VASP KYC subpoena."
    )
    event2 = record_analyst_decision(req2, db)

    # Check that both distinct audit records exist in append-only history
    audits = db.query(AuditEventModel).filter(AuditEventModel.investigation_id == "INV-TEST-001").all()
    assert len(audits) == 2
    assert audits[0].event_hash != audits[1].event_hash
    db.close()
