import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.main import app
from app.models.database import SessionLocal, InvestigationModel, EvidenceRecordModel
from app.services.graph_engine import GraphEngine, _compute_and_attach_graph_metrics, _add_or_merge_edge
from app.core.config import settings

client = TestClient(app)


@pytest.fixture
def auth_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "analyst",
        "password": "tracex2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def lead_auditor_headers():
    login_resp = client.post("/api/v1/auth/token", json={
        "username": "lead_auditor",
        "password": "auditor2026"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. Graph Generation & Dynamic Topology Metrics
# =====================================================================

def test_graph_generation_and_metrics(auth_headers):
    """
    Verifies graph generation, node/edge Cytoscape payload structure,
    truthful graph source, and calculated topology metrics.
    """
    # 1. Load benchmark 1 (Protected)
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    assert bench_resp.status_code == 200
    inv_id = bench_resp.json()["investigation_id"]

    # 2. Query graph endpoint
    graph_resp = client.get(f"/api/v1/graph/{inv_id}", headers=auth_headers)
    assert graph_resp.status_code == 200
    data = graph_resp.json()

    assert "graph" in data
    assert "metrics" in data
    graph = data["graph"]
    assert "nodes" in graph
    assert "edges" in graph
    assert "graph_source" in graph
    assert graph["graph_source"] in ["NEO4J_PROPERTY_GRAPH", "LOCAL_FALLBACK"]

    if graph["graph_source"] == "LOCAL_FALLBACK":
        assert graph.get("fallback_reason") == "NEO4J_UNAVAILABLE"

    # Verify node types exist
    node_types = [n["data"]["type"] for n in graph["nodes"]]
    assert "Persona" in node_types
    assert "PGP_Key" in node_types
    assert "Wallet" in node_types

    # Verify per-node topology metrics
    for node in graph["nodes"]:
        data_node = node["data"]
        assert "degree" in data_node
        assert isinstance(data_node["degree"], int)
        assert "in_degree" in data_node
        assert isinstance(data_node["in_degree"], int)
        assert "out_degree" in data_node
        assert isinstance(data_node["out_degree"], int)
        assert "degree_centrality" in data_node
        assert 0.0 <= data_node["degree_centrality"] <= 1.0
        assert "investigation_id" in data_node
        assert data_node["investigation_id"] == inv_id

    # Verify graph summary metrics
    metrics = data["metrics"]
    assert metrics["node_count"] == len(graph["nodes"])
    assert metrics["edge_count"] == len(graph["edges"])
    assert 0.0 <= metrics["density"] <= 1.0
    assert metrics["max_degree"] >= 1
    assert metrics["central_node_id"] is not None
    assert metrics["persona_hop_distance"] is not None
    assert metrics["persona_hop_distance"] >= 1


# =====================================================================
# 2. Edge Provenance: Single Source of Truth (`evidence_ids: List[str]`)
# =====================================================================

def test_graph_edge_provenance_contracts(auth_headers):
    """
    Verifies that 100% of edges carry assessment_id: str and evidence_ids: List[str].
    Ensures that redundant scalar evidence_id is eliminated so there are not two sources of truth.
    """
    bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    inv_id = bench_resp.json()["investigation_id"]

    graph_resp = client.get(f"/api/v1/graph/{inv_id}", headers=auth_headers)
    graph = graph_resp.json()["graph"]

    assert len(graph["edges"]) > 0
    for edge in graph["edges"]:
        ed = edge["data"]
        assert "assessment_id" in ed
        assert isinstance(ed["assessment_id"], str)
        assert ed["assessment_id"].startswith("ASSESS-") or ed["assessment_id"].startswith("INV-")

        assert "evidence_ids" in ed
        assert isinstance(ed["evidence_ids"], list)

        # Confirm scalar evidence_id is removed to maintain single source of truth
        assert "evidence_id" not in ed, "Scalar evidence_id must be removed in favor of evidence_ids: List[str]"

        assert "association" in ed
        assert "evidence_strength" in ed


def test_graph_edge_provenance_multi_evidence():
    """
    Verifies that multi-evidence edges correctly aggregate all contributing evidence IDs
    without duplicates under _add_or_merge_edge.
    """
    edges_dict = {}
    _add_or_merge_edge(
        edges_dict,
        edge_id="e_Krypton_Specter_corr",
        source="KryptonGhost",
        target="SpecterOp",
        label="LIKELY_SAME_AS",
        association="MULTI_FACTOR_CORRELATION",
        evidence_strength="HIGH",
        assessment_id="ASSESS-001",
        evidence_ids=["EV-001-PGP"]
    )
    # Merge second evidence ID
    _add_or_merge_edge(
        edges_dict,
        edge_id="e_Krypton_Specter_corr",
        source="KryptonGhost",
        target="SpecterOp",
        label="LIKELY_SAME_AS",
        association="MULTI_FACTOR_CORRELATION",
        evidence_strength="HIGH",
        assessment_id="ASSESS-001",
        evidence_ids=["EV-005-BTC"]
    )
    # Merge third evidence ID (plus duplicate EV-001)
    _add_or_merge_edge(
        edges_dict,
        edge_id="e_Krypton_Specter_corr",
        source="KryptonGhost",
        target="SpecterOp",
        label="LIKELY_SAME_AS",
        association="MULTI_FACTOR_CORRELATION",
        evidence_strength="HIGH",
        assessment_id="ASSESS-001",
        evidence_ids=["EV-006-INFRA", "EV-001-PGP"]
    )

    edge_data = edges_dict["e_Krypton_Specter_corr"]["data"]
    assert edge_data["evidence_ids"] == ["EV-001-PGP", "EV-005-BTC", "EV-006-INFRA"]
    assert "evidence_id" not in edge_data


# =====================================================================
# 3. Cross-Case Isolation (Benchmark 1 vs Benchmark 2)
# =====================================================================

def test_graph_cross_case_isolation(auth_headers):
    """
    Loads both Case 1 and Case 2; verifies that querying Case 1 returns zero
    nodes/edges from Case 2, and vice versa.
    """
    client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
    client.post("/api/v1/ingestion/benchmark/2", headers=auth_headers)

    # 1. Query Case 1
    resp_1 = client.get("/api/v1/graph/INV-SIH-001", headers=auth_headers)
    assert resp_1.status_code == 200
    graph_1 = resp_1.json()["graph"]
    nodes_1 = [n["data"]["id"] for n in graph_1["nodes"]]

    assert "KryptonGhost" in nodes_1
    assert "SpecterOp" in nodes_1
    assert "ShadowBroker_X" not in nodes_1
    assert "PhantomAccess" not in nodes_1

    for n in graph_1["nodes"]:
        assert n["data"]["investigation_id"] == "INV-SIH-001"

    # 2. Query Case 2
    resp_2 = client.get("/api/v1/graph/INV-SIH-002", headers=auth_headers)
    assert resp_2.status_code == 200
    graph_2 = resp_2.json()["graph"]
    nodes_2 = [n["data"]["id"] for n in graph_2["nodes"]]

    assert "ShadowBroker_X" in nodes_2
    assert "PhantomAccess" in nodes_2
    assert "KryptonGhost" not in nodes_2
    assert "SpecterOp" not in nodes_2

    for n in graph_2["nodes"]:
        assert n["data"]["investigation_id"] == "INV-SIH-002"


def test_graph_shared_entity_cross_case_isolation():
    """
    Tests that when an identical technical indicator (e.g. crypto wallet address)
    is present in two distinct investigations, the graph engine isolates traversals
    and never bridges Investigation A into Investigation B.
    """
    shared_wallet = "1SharedDepositExchangeWalletXYZ"

    artifacts_a = [
        {
            "evidence_id": "EV-A-01",
            "artifact_type": "BTC_TRANSACTION",
            "raw_payload": {
                "cluster_id": shared_wallet,
                "persona": "PersonaAlpha",
                "clustering_method": "CIOH",
                "inputs": ["1Alpha"],
                "outputs": [shared_wallet]
            }
        }
    ]

    artifacts_b = [
        {
            "evidence_id": "EV-B-01",
            "artifact_type": "BTC_TRANSACTION",
            "raw_payload": {
                "cluster_id": shared_wallet,
                "persona": "PersonaBeta",
                "clustering_method": "CIOH",
                "inputs": ["1Beta"],
                "outputs": [shared_wallet]
            }
        }
    ]

    graph_a = GraphEngine._build_local_cytoscape_graph(
        investigation_id="INV-TEST-A",
        persona_a="PersonaAlpha",
        persona_b="PersonaGamma",
        artifacts=artifacts_a,
        attribution_state="POSSIBLE_LINK",
        hard_gate_triggered=False
    )

    graph_b = GraphEngine._build_local_cytoscape_graph(
        investigation_id="INV-TEST-B",
        persona_a="PersonaBeta",
        persona_b="PersonaDelta",
        artifacts=artifacts_b,
        attribution_state="POSSIBLE_LINK",
        hard_gate_triggered=False
    )

    nodes_a_ids = [n["data"]["id"] for n in graph_a["nodes"]]
    nodes_b_ids = [n["data"]["id"] for n in graph_b["nodes"]]

    # Both contain the shared wallet node within their respective graphs
    assert shared_wallet in nodes_a_ids
    assert shared_wallet in nodes_b_ids

    # But Case A has zero knowledge of PersonaBeta or PersonaDelta
    assert "PersonaBeta" not in nodes_a_ids
    assert "PersonaDelta" not in nodes_a_ids

    # And Case B has zero knowledge of PersonaAlpha or PersonaGamma
    assert "PersonaAlpha" not in nodes_b_ids
    assert "PersonaGamma" not in nodes_b_ids

    # Assert node investigation_id scoping
    for n in graph_a["nodes"]:
        assert n["data"]["investigation_id"] == "INV-TEST-A"
    for n in graph_b["nodes"]:
        assert n["data"]["investigation_id"] == "INV-TEST-B"


# =====================================================================
# 4. Topology Metrics Mathematical Accuracy
# =====================================================================

def test_graph_topology_metrics_computation():
    """
    Verifies mathematical correctness of topology calculations on a known synthetic graph:
    - Path A -> X -> B
    - A: degree 1, in_degree 0, out_degree 1
    - X: degree 2, in_degree 1, out_degree 1
    - B: degree 1, in_degree 1, out_degree 0
    - Total nodes = 3, density = 2 * 2 / (3 * 2) = 4 / 6 = 0.6667
    - persona_hop_distance between A and B = 2
    """
    nodes = {
        "A": {"data": {"id": "A", "type": "Persona"}},
        "X": {"data": {"id": "X", "type": "Wallet"}},
        "B": {"data": {"id": "B", "type": "Persona"}}
    }
    edges = {
        "e_A_X": {"data": {"id": "e_A_X", "source": "A", "target": "X"}},
        "e_X_B": {"data": {"id": "e_X_B", "source": "X", "target": "B"}}
    }

    metrics = _compute_and_attach_graph_metrics(nodes, edges, persona_a="A", persona_b="B")

    # Verify per-node metrics
    assert nodes["A"]["data"]["degree"] == 1
    assert nodes["A"]["data"]["in_degree"] == 0
    assert nodes["A"]["data"]["out_degree"] == 1
    assert nodes["A"]["data"]["degree_centrality"] == 0.5  # 1 / (3-1)

    assert nodes["X"]["data"]["degree"] == 2
    assert nodes["X"]["data"]["in_degree"] == 1
    assert nodes["X"]["data"]["out_degree"] == 1
    assert nodes["X"]["data"]["degree_centrality"] == 1.0  # 2 / (3-1)

    assert nodes["B"]["data"]["degree"] == 1
    assert nodes["B"]["data"]["in_degree"] == 1
    assert nodes["B"]["data"]["out_degree"] == 0
    assert nodes["B"]["data"]["degree_centrality"] == 0.5  # 1 / (3-1)

    # Verify graph-level summary metrics
    assert metrics["node_count"] == 3
    assert metrics["edge_count"] == 2
    assert metrics["unique_undirected_edges"] == 2
    assert metrics["density"] == 0.6667
    assert metrics["max_degree"] == 2
    assert metrics["central_node_id"] == "X"
    assert metrics["persona_hop_distance"] == 2


def test_graph_empty_and_single_node_metrics():
    """
    Verifies boundary edge cases (0 nodes and 1 node) to ensure no ZeroDivisionError.
    """
    # 0 nodes
    metrics_0 = _compute_and_attach_graph_metrics({}, {}, persona_a="A", persona_b="B")
    assert metrics_0["node_count"] == 0
    assert metrics_0["edge_count"] == 0
    assert metrics_0["density"] == 0.0
    assert metrics_0["max_degree"] == 0
    assert metrics_0["central_node_id"] is None
    assert metrics_0["persona_hop_distance"] is None

    # 1 node
    single_node = {"Single": {"data": {"id": "Single", "type": "Persona"}}}
    metrics_1 = _compute_and_attach_graph_metrics(single_node, {}, persona_a="Single", persona_b="Single")
    assert metrics_1["node_count"] == 1
    assert metrics_1["edge_count"] == 0
    assert metrics_1["density"] == 0.0
    assert metrics_1["max_degree"] == 0
    assert metrics_1["central_node_id"] == "Single"
    assert metrics_1["persona_hop_distance"] == 0  # Same persona hop distance is 0
    assert single_node["Single"]["data"]["degree_centrality"] == 0.0


def test_graph_hop_distance_disconnected():
    """
    Verifies that disconnected personas produce persona_hop_distance = None.
    """
    nodes = {
        "A": {"data": {"id": "A", "type": "Persona"}},
        "B": {"data": {"id": "B", "type": "Persona"}}
    }
    metrics = _compute_and_attach_graph_metrics(nodes, {}, persona_a="A", persona_b="B")
    assert metrics["persona_hop_distance"] is None


# =====================================================================
# 5. Transparent Fallback & Production Fail-Closed
# =====================================================================

def test_graph_transparent_fallback_source(auth_headers):
    """
    Verifies that when Neo4j is unavailable, graph_source is truthfully reported as LOCAL_FALLBACK.
    """
    with patch.object(GraphEngine, "_get_neo4j_driver", return_value=None):
        bench_resp = client.post("/api/v1/ingestion/benchmark/1", headers=auth_headers)
        inv_id = bench_resp.json()["investigation_id"]

        graph_resp = client.get(f"/api/v1/graph/{inv_id}", headers=auth_headers)
        assert graph_resp.status_code == 200
        graph = graph_resp.json()["graph"]
        assert graph["graph_source"] == "LOCAL_FALLBACK"
        assert graph["fallback_reason"] == "NEO4J_UNAVAILABLE"


def test_graph_production_fail_closed():
    """
    Verifies that in production mode (ENVIRONMENT=production), GraphEngine raises
    HTTP 503 rather than silently masquerading fallback as a live property graph.
    """
    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch.object(GraphEngine, "_get_neo4j_driver", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                GraphEngine.generate_cytoscape_graph(
                    investigation_id="INV-PROD-TEST",
                    persona_a="PersonaA",
                    persona_b="PersonaB",
                    artifacts=[],
                    attribution_state="INCONCLUSIVE",
                    hard_gate_triggered=False
                )
            assert exc_info.value.status_code == 503
            assert "unavailable in production mode" in exc_info.value.detail


# =====================================================================
# 6. Endpoints RBAC & Investigation Authorization
# =====================================================================

def test_graph_endpoints_rbac_and_authorization(auth_headers, lead_auditor_headers):
    """
    Verifies 401 unauthenticated and 403 unauthorized enforcement on graph endpoints.
    """
    # 1. Unauthenticated request -> 401
    unauth_resp = client.get("/api/v1/graph/INV-SIH-001")
    assert unauth_resp.status_code == 401

    unauth_metrics = client.get("/api/v1/graph/INV-SIH-001/metrics")
    assert unauth_metrics.status_code == 401

    # 2. Query as assigned analyst -> 200
    auth_resp = client.get("/api/v1/graph/INV-SIH-001", headers=auth_headers)
    assert auth_resp.status_code == 200

    metrics_resp = client.get("/api/v1/graph/INV-SIH-001/metrics", headers=auth_headers)
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert "metrics" in metrics_data
    assert "node_count" in metrics_data["metrics"]

    # 3. Create restricted investigation assigned to another analyst
    db = SessionLocal()
    other_inv = InvestigationModel(
        id="INV-RESTRICTED-OTHER",
        title="Restricted Case",
        target_persona_a="Target1",
        target_persona_b="Target2",
        assigned_analyst_id="ANALYST-999"  # Not current user ANALYST-001
    )
    db.merge(other_inv)
    db.commit()
    db.close()

    # 4. Analyst accessing other analyst's investigation -> 403 Forbidden
    forbidden_resp = client.get("/api/v1/graph/INV-RESTRICTED-OTHER", headers=auth_headers)
    assert forbidden_resp.status_code == 403

    forbidden_metrics = client.get("/api/v1/graph/INV-RESTRICTED-OTHER/metrics", headers=auth_headers)
    assert forbidden_metrics.status_code == 403

    # 5. Lead auditor accessing other analyst's investigation -> 200 OK (Auditor oversight)
    auditor_resp = client.get("/api/v1/graph/INV-RESTRICTED-OTHER", headers=lead_auditor_headers)
    assert auditor_resp.status_code == 200
