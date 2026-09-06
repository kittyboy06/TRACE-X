import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.database import AuditEventModel

GENESIS_HASH = "0" * 64


class AuditChainService:
    """
    Manages the per-investigation tamper-evident SHA-256 audit hash chain.
    - Thread-safe serialization prevents concurrent audit write forks.
    - Deterministic canonicalization ensures reproducible verification.
    - Atomic transaction boundary: append_event() does NOT commit; the caller
      commits the assessment and audit event atomically in one transaction.
    """
    _audit_lock = threading.Lock()
    _chain_state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def reset_chain_state(cls, investigation_id: Optional[str] = None):
        """Clears in-memory chain tracker for test isolation or manual reset."""
        with cls._audit_lock:
            if investigation_id:
                cls._chain_state.pop(investigation_id, None)
            else:
                cls._chain_state.clear()

    @staticmethod
    def _format_timestamp(ts: Any) -> str:
        """Ensures consistent ISO-8601 UTC timestamp formatting."""
        if isinstance(ts, str):
            return ts
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()

    @staticmethod
    def canonicalize(data: Dict[str, Any]) -> str:
        """Produces deterministic, compact JSON string with sorted keys."""
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def compute_event_hash(canonical_data: str, previous_hash: str) -> str:
        """Computes SHA-256 fingerprint over canonical data + previous_hash."""
        payload = (canonical_data + previous_hash).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def get_last_event_hash(cls, investigation_id: str, db: Session) -> str:
        """
        Retrieves the terminal event hash for an investigation.
        Returns the 64-zero genesis root hash if no prior events exist.
        """
        with cls._audit_lock:
            state = cls._chain_state.get(investigation_id)
            if state and state.get("last_hash"):
                return state["last_hash"]

            last_event = (
                db.query(AuditEventModel)
                .filter(AuditEventModel.investigation_id == investigation_id)
                .order_by(AuditEventModel.timestamp.desc(), AuditEventModel.audit_id.desc())
                .first()
            )
            return last_event.event_hash if last_event else GENESIS_HASH

    @classmethod
    def append_event(
        cls,
        db: Session,
        investigation_id: str,
        assessment_id: str,
        action: str,
        analyst_id: str,
        rationale: str,
        prior_state: str,
        resulting_state: str,
        payload_details: Optional[Dict[str, Any]] = None
    ) -> AuditEventModel:
        """
        Constructs and adds an AuditEventModel to the current database session under a lock.
        Maintains linear sequence and monotonic timestamps across concurrent threads.
        DOES NOT COMMIT so the caller can commit assessment state and audit event atomically.
        """
        with cls._audit_lock:
            state = cls._chain_state.get(investigation_id)
            if state is None:
                db_last = (
                    db.query(AuditEventModel)
                    .filter(AuditEventModel.investigation_id == investigation_id)
                    .order_by(AuditEventModel.timestamp.desc(), AuditEventModel.audit_id.desc())
                    .first()
                )
                prev_hash = db_last.event_hash if db_last else GENESIS_HASH
                last_time = db_last.timestamp if db_last else datetime.min.replace(tzinfo=timezone.utc)
                if hasattr(last_time, "tzinfo") and last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                state = {
                    "last_hash": prev_hash,
                    "last_time": last_time,
                    "sequence": 0
                }
                cls._chain_state[investigation_id] = state

            previous_hash = state["last_hash"]

            # Strictly monotonic timestamps guarantee deterministic ordering
            now = datetime.now(timezone.utc)
            if now <= state["last_time"]:
                from datetime import timedelta
                now = state["last_time"] + timedelta(milliseconds=1)
            state["last_time"] = now
            state["sequence"] += 1
            seq = state["sequence"]

            audit_id = f"AUDIT-{now.strftime('%Y%m%d%H%M%S%f')}-{seq:04d}"
            now_iso = cls._format_timestamp(now)

            canonical_dict = {
                "action": action,
                "analyst_id": analyst_id,
                "assessment_id": assessment_id,
                "audit_id": audit_id,
                "investigation_id": investigation_id,
                "prior_state": prior_state,
                "rationale": rationale,
                "resulting_state": resulting_state,
                "timestamp": now_iso
            }
            canonical_data = cls.canonicalize(canonical_dict)
            event_hash = cls.compute_event_hash(canonical_data, previous_hash)

            # Advance in-memory state for immediate chaining by concurrent workers
            state["last_hash"] = event_hash

            event = AuditEventModel(
                audit_id=audit_id,
                investigation_id=investigation_id,
                assessment_id=assessment_id,
                action=action,
                analyst_id=analyst_id,
                timestamp=now,
                rationale=rationale,
                prior_state=prior_state,
                resulting_state=resulting_state,
                previous_hash=previous_hash,
                event_hash=event_hash
            )
            db.add(event)
            return event

    @classmethod
    def verify_investigation_chain(
        cls,
        investigation_id: str,
        db: Session
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Cryptographically verifies the append-only hash chain for an investigation.
        Returns (is_valid, event_records, failure_reason).
        """
        events = (
            db.query(AuditEventModel)
            .filter(AuditEventModel.investigation_id == investigation_id)
            .order_by(AuditEventModel.timestamp.asc(), AuditEventModel.audit_id.asc())
            .all()
        )
        if not events:
            return True, [], None

        records: List[Dict[str, Any]] = []
        expected_prev = GENESIS_HASH

        for idx, ev in enumerate(events):
            if ev.previous_hash != expected_prev:
                reason = (
                    f"Chain broken at event {ev.audit_id} (index {idx}): "
                    f"expected previous_hash '{expected_prev}', got '{ev.previous_hash}'."
                )
                return False, records, reason

            ts_str = cls._format_timestamp(ev.timestamp)
            canonical_dict = {
                "action": ev.action,
                "analyst_id": ev.analyst_id,
                "assessment_id": ev.assessment_id,
                "audit_id": ev.audit_id,
                "investigation_id": ev.investigation_id,
                "prior_state": ev.prior_state,
                "rationale": ev.rationale,
                "resulting_state": ev.resulting_state,
                "timestamp": ts_str
            }
            canonical_str = cls.canonicalize(canonical_dict)
            computed_hash = cls.compute_event_hash(canonical_str, ev.previous_hash)
            if computed_hash != ev.event_hash:
                reason = (
                    f"Cryptographic fingerprint mismatch at event {ev.audit_id} (index {idx}): "
                    f"computed hash '{computed_hash}', stored hash '{ev.event_hash}'."
                )
                return False, records, reason

            records.append({
                "audit_id": ev.audit_id,
                "action": ev.action,
                "analyst_id": ev.analyst_id,
                "timestamp": ts_str,
                "previous_hash": ev.previous_hash,
                "event_hash": ev.event_hash
            })
            expected_prev = ev.event_hash

        return True, records, None
