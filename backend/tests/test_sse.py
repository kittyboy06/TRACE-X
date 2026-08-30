import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_stepwise_sse_pipeline(auth_headers):
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Connect to SSE stream
    with client.stream("GET", f"/api/v1/pipeline/stream/{inv_id}") as response:
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
        assert 0.75 <= final_event["assessment"]["evidence_score"] <= 0.80
