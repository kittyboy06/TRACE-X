import pytest
import json
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.services.sse_ticket_service import SSETicketService, SSETicket

client = TestClient(app)


@pytest.fixture
def auth_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_stepwise_sse_pipeline_with_ticket(auth_headers):
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Issue ephemeral SSE ticket
    ticket_resp = client.post(
        "/api/v1/auth/sse-ticket",
        json={"investigation_id": inv_id},
        headers=auth_headers
    )
    assert ticket_resp.status_code == 200
    ticket = ticket_resp.json()["ticket"]

    # 3. Connect to SSE stream using ticket
    with client.stream("GET", f"/api/v1/pipeline/stream/{inv_id}?ticket={ticket}") as response:
        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line.replace("data: ", "").strip()
                if data_str:
                    event = json.loads(data_str)
                    events.append(event)

        # Verify stages executed sequentially
        stages = [e.get("stage") for e in events]
        assert "EVIDENCE_INGESTION" in stages
        assert "AI_STYLOMETRY" in stages
        assert "BLOCKCHAIN_FORENSICS" in stages
        assert "GRAPH_INTELLIGENCE" in stages
        assert "BEHAVIORAL_TEMPORAL" in stages
        assert "EVIDENCE_FUSION" in stages
        assert "COMPLETE" in stages

        # Verify completion assessment payload
        final_event = events[-1]
        assert final_event["stage"] == "COMPLETE"
        assert "assessment" in final_event
        assert final_event["assessment"]["attribution_state"] == "LIKELY_LINK"
        assert 0.75 <= final_event["assessment"]["base_score"] <= 0.80

    # 4. Attempt to REUSE the ticket (replay attack prevention) -> Must fail with 401
    resp_reuse = client.get(f"/api/v1/pipeline/stream/{inv_id}?ticket={ticket}")
    assert resp_reuse.status_code == 401
    assert "already been consumed" in resp_reuse.json()["detail"]


def test_sse_ticket_validation_guards(auth_headers):
    """Verifies that unauthenticated, expired, or investigation-mismatched tickets are rejected."""
    # 1. No ticket and no auth header -> 401
    r_no_ticket = client.get("/api/v1/pipeline/stream/INV-SIH-001")
    assert r_no_ticket.status_code == 401

    # 2. Non-existent ticket -> 401
    r_bad_ticket = client.get("/api/v1/pipeline/stream/INV-SIH-001?ticket=completely_fake_ticket_12345")
    assert r_bad_ticket.status_code == 401

    # 3. Expired ticket -> 401
    expired_ticket = SSETicketService.create_ticket(
        investigation_id="INV-SIH-001",
        analyst_id="ANALYST-001",
        role="CTI_ANALYST",
        ttl_seconds=-10  # Created already expired
    )
    r_expired = client.get(f"/api/v1/pipeline/stream/INV-SIH-001?ticket={expired_ticket.ticket_id}")
    assert r_expired.status_code == 401
    assert "expired" in r_expired.json()["detail"]

    # 4. Ticket scoped to INV-SIH-001 used against INV-SIH-002 -> 403 Forbidden
    cross_ticket = SSETicketService.create_ticket(
        investigation_id="INV-SIH-001",
        analyst_id="ANALYST-001",
        role="CTI_ANALYST",
        ttl_seconds=60
    )
    r_cross = client.get(f"/api/v1/pipeline/stream/INV-SIH-002?ticket={cross_ticket.ticket_id}")
    assert r_cross.status_code == 403
    assert "scoped to investigation" in r_cross.json()["detail"]


@pytest.mark.asyncio
async def test_sse_ticket_concurrency_lock():
    """Verify that concurrent consumers of the exact same ticket cannot race to consume it twice."""
    ticket = SSETicketService.create_ticket(
        investigation_id="INV-CONCURRENT-01",
        analyst_id="ANALYST-001",
        role="CTI_ANALYST",
        ttl_seconds=60
    )

    results = []

    async def attempt_consume():
        try:
            consumed = await SSETicketService.consume_ticket(ticket.ticket_id, "INV-CONCURRENT-01")
            results.append(("SUCCESS", consumed))
        except Exception as e:
            results.append(("ERROR", str(e)))

    # Launch 5 concurrent consume attempts
    await asyncio.gather(
        attempt_consume(),
        attempt_consume(),
        attempt_consume(),
        attempt_consume(),
        attempt_consume()
    )

    # Exactly one must succeed, all others must fail
    successes = [r for r in results if r[0] == "SUCCESS"]
    failures = [r for r in results if r[0] == "ERROR"]

    assert len(successes) == 1
    assert len(failures) == 4
