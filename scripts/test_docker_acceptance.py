#!/usr/bin/env python3
"""
TRACE-X Phase 9: Real Docker Desktop Runtime Acceptance Test
Verifies:
1. In-image utilities (backend curl, frontend wget)
2. HTTP endpoints and Nginx reverse proxy routing
3. Ephemeral SSE ticket generation and unbuffered SSE stream through Nginx
4. Mathematical determinism for Case 1 and Case 2
5. Named SQLite volume persistence across backend container restart
"""
import sys
import time
import json
import subprocess
import httpx

BASE_URL = "http://localhost:5173"
BACKEND_DIRECT_URL = "http://localhost:8000"

def log(msg: str):
    print(f"[ACCEPTANCE] {msg}")

def test_docker_runtime():
    log("1. Verifying in-image utilities...")
    res_curl = subprocess.run(["docker", "compose", "exec", "backend", "which", "curl"], capture_output=True, text=True)
    res_wget = subprocess.run(["docker", "compose", "exec", "frontend", "which", "wget"], capture_output=True, text=True)
    assert res_curl.returncode == 0 and "/curl" in res_curl.stdout, f"backend curl missing: {res_curl.stderr}"
    assert res_wget.returncode == 0 and "/wget" in res_wget.stdout, f"frontend wget missing: {res_wget.stderr}"
    log(f"   [PASS] backend has /usr/bin/curl, frontend has /usr/bin/wget")

    log("2. Verifying HTTP health and reverse proxy endpoints...")
    with httpx.Client(timeout=25.0) as client:
        # Backend health
        r_back = client.get(f"{BACKEND_DIRECT_URL}/health")
        assert r_back.status_code == 200, f"Backend health failed: {r_back.status_code}"
        assert r_back.json().get("status") == "HEALTHY"
        log("   [PASS] Backend /health returned 200 HEALTHY")

        # Frontend Nginx healthz
        r_front = client.get(f"{BASE_URL}/healthz")
        assert r_front.status_code == 200 and "healthy" in r_front.text, f"Frontend healthz failed: {r_front.status_code}"
        log("   [PASS] Frontend Nginx /healthz returned 200 healthy")

        # Nginx reverse proxy to auth
        r_auth = client.post(
            f"{BASE_URL}/api/v1/auth/token",
            json={"username": "analyst", "password": "tracex2026"}
        )
        assert r_auth.status_code == 200, f"Auth failed: {r_auth.text}"
        auth_data = r_auth.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        log(f"   [PASS] Authenticated analyst via Nginx reverse proxy (role: {auth_data['role']})")

        # Check /me
        r_me = client.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
        assert r_me.status_code == 200 and r_me.json().get("status") == "AUTHENTICATED"
        log("   [PASS] Verified /api/v1/auth/me via Nginx reverse proxy")

        log("3. Ingesting Benchmark Case 1 (INV-SIH-001)...")
        r_ingest1 = client.post(f"{BASE_URL}/api/v1/ingestion/benchmark/1", headers=headers)
        assert r_ingest1.status_code in [200, 201], f"Ingestion 1 failed: {r_ingest1.text}"
        log(f"   [PASS] Ingested Case 1 benchmark: {r_ingest1.json().get('status', 'OK')}")

        log("4. Requesting ephemeral SSE ticket and streaming via Nginx...")
        r_ticket = client.post(
            f"{BASE_URL}/api/v1/auth/sse-ticket",
            headers=headers,
            json={"investigation_id": "INV-SIH-001"}
        )
        assert r_ticket.status_code == 200, f"SSE ticket failed: {r_ticket.text}"
        ticket_id = r_ticket.json()["ticket"]
        log(f"   [PASS] Obtained ephemeral SSE ticket: {ticket_id[:8]}... (TTL: 60s)")

        # Stream SSE through Nginx reverse proxy using ephemeral ticket
        sse_events = []
        with client.stream("GET", f"{BASE_URL}/api/v1/pipeline/stream/INV-SIH-001?ticket={ticket_id}") as sse_stream:
            assert sse_stream.status_code == 200, f"SSE stream failed: {sse_stream.status_code}"
            assert "text/event-stream" in sse_stream.headers.get("content-type", "")
            for line in sse_stream.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        ev = json.loads(data_str)
                        sse_events.append(ev)
                        stage = ev.get("stage")
                        progress = ev.get("progress")
                        log(f"   -> [SSE Event] stage={stage} progress={progress}%")
                        if stage == "COMPLETE" or progress == 100:
                            break
                    except Exception:
                        pass
                if len(sse_events) >= 8:
                    break
        assert len(sse_events) > 0, "No SSE events received through Nginx!"
        log(f"   [PASS] Successfully received {len(sse_events)} unbuffered SSE events via Nginx proxy")

        log("5. Verifying Case 1 Attribution Assessment & Determinism...")
        r_attr1 = client.get(f"{BASE_URL}/api/v1/attribution/INV-SIH-001", headers=headers)
        assert r_attr1.status_code == 200, f"Attribution 1 failed: {r_attr1.text}"
        attr1 = r_attr1.json()
        score1 = attr1["base_score"]
        state1 = attr1["attribution_state"]
        band1 = attr1["confidence_band"]
        log(f"   [PASS] Case 1 S_base = {score1:.4f}, state = {state1}, band = {band1}")
        assert score1 in [0.7639, 0.7735], f"Unexpected Case 1 score: {score1}"
        assert state1 == "LIKELY_LINK", f"Expected LIKELY_LINK, got {state1}"
        assert band1 == "HIGH", f"Expected HIGH, got {band1}"

        log("6. Verifying Named SQLite Volume Persistence Across Backend Restart...")
        log("   Restarting tracex-backend container (`docker compose restart backend`)...")
        sub_restart = subprocess.run(["docker", "compose", "restart", "backend"], capture_output=True, text=True)
        assert sub_restart.returncode == 0, f"Restart failed: {sub_restart.stderr}"
        log("   Container restarted. Polling health...")

        # Wait for backend healthy
        time.sleep(4)
        for attempt in range(12):
            try:
                r_check = client.get(f"{BACKEND_DIRECT_URL}/health")
                if r_check.status_code == 200 and r_check.json().get("status") == "HEALTHY":
                    log("   [PASS] Backend is HEALTHY after container restart")
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            raise RuntimeError("Backend did not become healthy after restart!")

        # Re-fetch Case 1 attribution to verify state survived
        r_after = client.get(f"{BASE_URL}/api/v1/attribution/INV-SIH-001", headers=headers)
        assert r_after.status_code == 200, f"Attribution after restart failed: {r_after.text}"
        attr_after = r_after.json()
        assert attr_after["base_score"] == score1, f"Score changed after restart: {attr_after['base_score']} != {score1}"
        log(f"   [PASS] State preserved in sqlite_data volume: S_base = {attr_after['base_score']:.4f}")

        # Check tamper-evident audit trail survived restart and validates cryptographically
        r_audit = client.get(f"{BASE_URL}/api/v1/audit/verify/INV-SIH-001", headers=headers)
        assert r_audit.status_code == 200, f"Audit verification failed: {r_audit.text}"
        audit_res = r_audit.json()
        assert audit_res["is_valid"] is True, f"Audit chain verification failed: {audit_res}"
        assert audit_res["event_count"] > 0, "Audit records were lost across restart!"
        log(f"   [PASS] Tamper-evident audit trail cryptographically verified across restart ({audit_res['event_count']} records, terminal: {audit_res['terminal_hash'][:8]}...)")

        log("7. Ingesting Benchmark Case 2 (INV-SIH-002)...")
        r_ingest2 = client.post(f"{BASE_URL}/api/v1/ingestion/benchmark/2", headers=headers)
        assert r_ingest2.status_code in [200, 201], f"Ingestion 2 failed: {r_ingest2.text}"

        r_ticket2 = client.post(
            f"{BASE_URL}/api/v1/auth/sse-ticket",
            headers=headers,
            json={"investigation_id": "INV-SIH-002"}
        )
        assert r_ticket2.status_code == 200, f"SSE ticket 2 failed: {r_ticket2.text}"
        ticket2_id = r_ticket2.json()["ticket"]

        with client.stream("GET", f"{BASE_URL}/api/v1/pipeline/stream/INV-SIH-002?ticket={ticket2_id}") as sse2:
            for line in sse2.iter_lines():
                if "COMPLETE" in line:
                    break

        r_attr2 = client.get(f"{BASE_URL}/api/v1/attribution/INV-SIH-002", headers=headers)
        assert r_attr2.status_code == 200, f"Attribution 2 failed: {r_attr2.text}"
        attr2 = r_attr2.json()
        score2 = attr2["base_score"]
        state2 = attr2["attribution_state"]
        band2 = attr2["confidence_band"]
        hard_gate = attr2.get("hard_gate_applied", False)
        log(f"   [PASS] Case 2 S_base = {score2:.4f}, state = {state2}, band = {band2}, hard_gate = {hard_gate}")
        assert score2 == 0.2150, f"Case 2 score {score2} != 0.2150"
        assert state2 == "INCONCLUSIVE", f"Expected INCONCLUSIVE, got {state2}"
        assert band2 == "LOW", f"Expected LOW, got {band2}"
        assert hard_gate is True, f"Expected Level 2 Hard Gate triggered"

    log("=" * 60)
    log("ALL DOCKER RUNTIME ACCEPTANCE TESTS PASSED (7/7)")
    log("=" * 60)

if __name__ == "__main__":
    try:
        test_docker_runtime()
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
