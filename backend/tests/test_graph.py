import pytest
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


def test_graph_generation_and_source(auth_headers):
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Query graph endpoint
    graph_resp = client.get(f"/api/v1/graph/{inv_id}")
    assert graph_resp.status_code == 200
    data = graph_resp.json()
    
    assert "graph" in data
    graph = data["graph"]
    assert "nodes" in graph
    assert "edges" in graph
    assert "graph_source" in graph
    assert graph["graph_source"] in ["NEO4J_PROPERTY_GRAPH", "LOCAL_FALLBACK"]

    # Verify node types exist
    node_types = [n["data"]["type"] for n in graph["nodes"]]
    assert "Persona" in node_types
    assert "PGP_Key" in node_types
    assert "Wallet" in node_types

    # Verify edge labels
    edge_labels = [e["data"]["label"] for e in graph["edges"]]
    assert "USED" in edge_labels
    assert "LIKELY_SAME_AS" in edge_labels
