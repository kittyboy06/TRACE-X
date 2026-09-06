import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
from fastapi import HTTPException

from app.models.schemas import DimensionSignal, SignalStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


def _compute_and_attach_graph_metrics(
    nodes_dict: Dict[str, Any],
    edges_dict: Dict[str, Any],
    persona_a: Optional[str] = None,
    persona_b: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes deterministic, purely topological metrics:
    - Undirected connectivity topology: degree, degree_centrality, density, persona_hop_distance.
    - Directional degree metrics: in_degree (incoming), out_degree (outgoing).
    - Robust handling for empty (|V| = 0) and single-node (|V| = 1) graphs with zero division errors.
    - GraphEngine does NOT inject hidden or arbitrary threat scores; threat/attribution
      scoring is owned strictly by the fusion/attribution layer.
    """
    total_nodes = len(nodes_dict)
    total_edges = len(edges_dict)

    degrees = {nid: 0 for nid in nodes_dict}
    in_degrees = {nid: 0 for nid in nodes_dict}
    out_degrees = {nid: 0 for nid in nodes_dict}
    adj_undirected: Dict[str, set] = {nid: set() for nid in nodes_dict}
    unique_undirected_edges = set()

    for edge in edges_dict.values():
        src = edge["data"]["source"]
        tgt = edge["data"]["target"]

        if src in out_degrees:
            out_degrees[src] += 1
        if tgt in in_degrees:
            in_degrees[tgt] += 1

        if src in adj_undirected and tgt in adj_undirected and src != tgt:
            adj_undirected[src].add(tgt)
            adj_undirected[tgt].add(src)
            edge_key = tuple(sorted([src, tgt]))
            unique_undirected_edges.add(edge_key)

    # Total undirected connectivity = number of distinct adjacent neighbors in undirected projection
    for nid in nodes_dict:
        degrees[nid] = len(adj_undirected[nid])

    denom = max(total_nodes - 1, 1)

    max_deg = 0
    central_node_id = None
    isolated_count = 0

    for nid, node in nodes_dict.items():
        deg = degrees[nid]
        centrality = round(deg / denom, 4) if total_nodes > 1 else 0.0
        node["data"]["degree"] = deg
        node["data"]["in_degree"] = in_degrees.get(nid, 0)
        node["data"]["out_degree"] = out_degrees.get(nid, 0)
        node["data"]["degree_centrality"] = centrality
        node["data"]["centrality"] = centrality  # Backward-compatible alias

        if deg == 0:
            isolated_count += 1
        if deg > max_deg or central_node_id is None:
            max_deg = deg
            central_node_id = nid

    # Undirected density: 2 * |E_undirected| / (|V| * (|V| - 1))
    if total_nodes > 1:
        possible_edges = (total_nodes * (total_nodes - 1)) / 2.0
        density = round(len(unique_undirected_edges) / possible_edges, 4)
    else:
        density = 0.0

    # Shortest path hop distance between target personas (BFS on undirected projection)
    persona_hop_distance = None
    if persona_a and persona_b:
        if persona_a == persona_b:
            persona_hop_distance = 0
        elif persona_a in adj_undirected and persona_b in adj_undirected:
            visited = {persona_a}
            queue = deque([(persona_a, 0)])
            found = False
            while queue:
                curr, dist = queue.popleft()
                if curr == persona_b:
                    persona_hop_distance = dist
                    found = True
                    break
                for neighbor in sorted(list(adj_undirected.get(curr, set()))):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))
            if not found:
                persona_hop_distance = None

    metrics = {
        "node_count": total_nodes,
        "edge_count": total_edges,
        "unique_undirected_edges": len(unique_undirected_edges),
        "density": density,
        "max_degree": max_deg,
        "central_node_id": central_node_id if total_nodes > 0 else None,
        "isolated_nodes_count": isolated_count,
        "persona_hop_distance": persona_hop_distance
    }

    return metrics


def _add_or_merge_edge(
    edges_dict: Dict[str, Any],
    edge_id: str,
    source: str,
    target: str,
    label: str,
    association: str,
    evidence_strength: str,
    assessment_id: str,
    evidence_ids: List[str],
    extra_fields: Optional[Dict[str, Any]] = None
):
    """
    Helper to add an edge or merge evidence_ids into an existing edge.
    guarantees evidence_ids: List[str] is the sole canonical provenance field.
    """
    clean_eids = [str(e) for e in evidence_ids if e]
    if edge_id in edges_dict:
        existing = edges_dict[edge_id]["data"]["evidence_ids"]
        for eid in clean_eids:
            if eid not in existing:
                existing.append(eid)
    else:
        edge_data = {
            "id": edge_id,
            "source": source,
            "target": target,
            "label": label,
            "association": association,
            "evidence_strength": evidence_strength,
            "assessment_id": assessment_id,
            "evidence_ids": clean_eids
        }
        if extra_fields:
            edge_data.update(extra_fields)
        edges_dict[edge_id] = {"data": edge_data}


class GraphEngine:
    _neo4j_driver = None
    _last_connection_attempt = 0.0
    RETRY_INTERVAL = 30.0

    @classmethod
    def _get_neo4j_driver(cls):
        import time
        now = time.time()
        if cls._neo4j_driver is not None:
            try:
                cls._neo4j_driver.verify_connectivity()
                return cls._neo4j_driver
            except Exception:
                cls._neo4j_driver = None

        if (now - cls._last_connection_attempt) < cls.RETRY_INTERVAL:
            return None

        cls._last_connection_attempt = now
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            driver.verify_connectivity()
            cls._neo4j_driver = driver
            logger.info("Successfully established connection to Neo4j Property Graph.")
            return cls._neo4j_driver
        except Exception as e:
            logger.info(f"Neo4j instance offline ({str(e)}). Utilizing deterministic local graph engine.")
            cls._neo4j_driver = None
            return None

    @classmethod
    def analyze_cryptographic_and_infra(
        cls,
        pgp_artifacts: List[Dict[str, Any]],
        infra_artifacts: List[Dict[str, Any]],
        weight_crypto: float = 0.30,
        weight_infra: float = 0.15,
        reliability_crypto: float = 1.0,
        reliability_infra: float = 1.0
    ) -> Tuple[DimensionSignal, DimensionSignal]:
        """
        Extracts Cryptographic (PGP reuse) and Infrastructure reuse signals
        delegating to canonical CryptographicEngine and InfrastructureEngine.
        """
        from app.services.engines.cryptographic_engine import CryptographicEngine
        from app.services.engines.infrastructure_engine import InfrastructureEngine

        contract_crypto = CryptographicEngine.analyze(
            artifacts=pgp_artifacts,
            reliability_context=reliability_crypto
        )
        contract_infra = InfrastructureEngine.analyze(
            artifacts=infra_artifacts,
            reliability_context=reliability_infra
        )

        status_crypto = SignalStatus(contract_crypto.status.value)
        status_infra = SignalStatus(contract_infra.status.value)

        crypto_signal = DimensionSignal(
            dimension_name="cryptographic",
            status=status_crypto,
            raw_score=contract_crypto.raw_score,
            reliability_factor=contract_crypto.reliability_factor,
            adjusted_score=contract_crypto.adjusted_score,
            configured_weight=weight_crypto,
            contribution=round(weight_crypto * contract_crypto.adjusted_score, 4),
            evidence_ids=contract_crypto.evidence_ids,
            supporting_details={
                "findings": contract_crypto.findings,
                "rationale": contract_crypto.findings[0].get("observation", "") if contract_crypto.findings else ""
            }
        )

        infra_signal = DimensionSignal(
            dimension_name="infrastructure",
            status=status_infra,
            raw_score=contract_infra.raw_score,
            reliability_factor=contract_infra.reliability_factor,
            adjusted_score=contract_infra.adjusted_score,
            configured_weight=weight_infra,
            contribution=round(weight_infra * contract_infra.adjusted_score, 4),
            evidence_ids=contract_infra.evidence_ids,
            supporting_details={
                "findings": contract_infra.findings,
                "rationale": contract_infra.findings[0].get("observation", "") if contract_infra.findings else ""
            }
        )

        return crypto_signal, infra_signal

    @classmethod
    def sync_to_neo4j(
        cls,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        artifacts: List[Dict[str, Any]],
        attribution_state: str,
        hard_gate_triggered: bool,
        assessment_id: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Persists CTI property graph into Neo4j via Cypher with strict investigation scoping:
        - Every node carries investigation_id: $inv.
        - Every relationship carries investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids.
        - Cross-case shared identifiers are partitioned by investigation_id to prevent bridge traversal.
        """
        driver = cls._get_neo4j_driver()
        if not driver:
            return False

        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

        try:
            with driver.session() as session:
                # Merge target personas
                p1_nid = f"{investigation_id}_{persona_a}"
                p2_nid = f"{investigation_id}_{persona_b}"
                session.run(
                    "MERGE (p1:Persona {id: $p1_nid, label: $p1, raw_id: $p1, investigation_id: $inv}) "
                    "MERGE (p2:Persona {id: $p2_nid, label: $p2, raw_id: $p2, investigation_id: $inv})",
                    p1_nid=p1_nid, p2_nid=p2_nid, p1=persona_a, p2=persona_b, inv=investigation_id
                )

                for art in artifacts:
                    art_type = art.get("artifact_type")
                    raw = art.get("raw_payload", {})
                    eid = art.get("evidence_id", "EV-UNKNOWN")
                    art_eids = [eid]

                    if art_type == "PGP_KEY":
                        key_id = raw.get("key_id", "UNKNOWN")
                        persona = raw.get("persona", persona_a)
                        p_nid = f"{investigation_id}_{persona}"
                        k_nid = f"{investigation_id}_PGP_{key_id}"
                        session.run(
                            "MERGE (k:PGP_Key {id: $k_nid, label: $key_lbl, raw_id: $key_id, fingerprint: $fp, type: 'PGP_Key', investigation_id: $inv}) "
                            "MERGE (p:Persona {id: $p_nid, label: $persona, raw_id: $persona, investigation_id: $inv}) "
                            "MERGE (p)-[:USED {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, evidence_strength: 'VERY_HIGH', association: 'VERIFIED_CRYPTOGRAPHIC_KEY'}]->(k)",
                            k_nid=k_nid, key_lbl=f"PGP: {key_id}", key_id=key_id, fp=raw.get("key_fingerprint", ""),
                            p_nid=p_nid, persona=persona, inv=investigation_id, aid=actual_aid, eids=art_eids
                        )
                    elif art_type == "FORUM_POST":
                        forum = raw.get("forum", "Darknet_Forum")
                        persona = raw.get("persona", persona_a)
                        p_nid = f"{investigation_id}_{persona}"
                        f_nid = f"{investigation_id}_FORUM_{forum}"
                        post_nid = f"{investigation_id}_POST_{eid}"
                        session.run(
                            "MERGE (f:Forum {id: $f_nid, label: $forum, raw_id: $forum, type: 'Forum', investigation_id: $inv}) "
                            "MERGE (post:Forum_Post {id: $post_nid, label: $post_lbl, raw_id: $eid, type: 'Forum_Post', word_count: $wc, investigation_id: $inv}) "
                            "MERGE (p:Persona {id: $p_nid, label: $persona, raw_id: $persona, investigation_id: $inv}) "
                            "MERGE (p)-[:AUTHORED {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'VERIFIED_AUTHOR', evidence_strength: 'HIGH'}]->(post) "
                            "MERGE (post)-[:POSTED_ON {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'POSTED_LOCATION', evidence_strength: 'HIGH'}]->(f)",
                            f_nid=f_nid, forum=forum, post_nid=post_nid, post_lbl=f"Post ({forum})",
                            wc=raw.get("word_count", 0), p_nid=p_nid, persona=persona, eid=eid,
                            inv=investigation_id, aid=actual_aid, eids=art_eids
                        )
                    elif art_type == "BTC_TRANSACTION":
                        cluster_id = raw.get("cluster_id", "BTC_CLUSTER")
                        w_nid = f"{investigation_id}_{cluster_id}"
                        session.run(
                            "MERGE (w:Wallet {id: $w_nid, label: $wlbl, raw_id: $cluster_id, type: 'Wallet', method: $method, investigation_id: $inv})",
                            w_nid=w_nid, wlbl=f"Wallet: {cluster_id}", cluster_id=cluster_id,
                            method=raw.get("clustering_method", "CIOH"), inv=investigation_id
                        )
                        inputs = raw.get("inputs", [])
                        p1_nid = f"{investigation_id}_{persona_a}"
                        if any(persona_a.lower() in str(inp).lower() for inp in inputs) or raw.get("persona") == persona_a:
                            session.run(
                                "MERGE (p:Persona {id: $p1_nid, label: $pa, raw_id: $pa, investigation_id: $inv}) "
                                "MERGE (w:Wallet {id: $w_nid, investigation_id: $inv}) "
                                "MERGE (p)-[:FUNDED_FROM {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'VERIFIED_OWNERSHIP', evidence_strength: 'HIGH'}]->(w)",
                                p1_nid=p1_nid, pa=persona_a, w_nid=w_nid, inv=investigation_id, aid=actual_aid, eids=art_eids
                            )
                        else:
                            session.run(
                                "MERGE (p:Persona {id: $p1_nid, label: $pa, raw_id: $pa, investigation_id: $inv}) "
                                "MERGE (w:Wallet {id: $w_nid, investigation_id: $inv}) "
                                "MERGE (p)-[:ASSOCIATED_WITH {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'INFERRED_ASSOCIATION', evidence_strength: 'MEDIUM_HEURISTIC'}]->(w)",
                                p1_nid=p1_nid, pa=persona_a, w_nid=w_nid, inv=investigation_id, aid=actual_aid, eids=art_eids
                            )

                        outputs = raw.get("outputs", [])
                        p2_nid = f"{investigation_id}_{persona_b}"
                        if any(persona_b.lower() in str(out).lower() for out in outputs) or raw.get("recipient_persona") == persona_b:
                            session.run(
                                "MERGE (p:Persona {id: $p2_nid, label: $pb, raw_id: $pb, investigation_id: $inv}) "
                                "MERGE (w:Wallet {id: $w_nid, investigation_id: $inv}) "
                                "MERGE (w)-[:TRANSFERRED_TO {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'VERIFIED_RECIPIENT', evidence_strength: 'HIGH'}]->(p)",
                                p2_nid=p2_nid, pb=persona_b, w_nid=w_nid, inv=investigation_id, aid=actual_aid, eids=art_eids
                            )

                        for hop in raw.get("hops_to_vasp", []):
                            vasp = hop.get("vasp_entity")
                            if vasp:
                                vasp_raw_id = f"VASP_{vasp.replace(' ', '_')}"
                                v_nid = f"{investigation_id}_{vasp_raw_id}"
                                session.run(
                                    "MERGE (v:VASP {id: $v_nid, label: $vlbl, raw_id: $vasp_raw_id, type: 'VASP', investigation_id: $inv}) "
                                    "MERGE (w:Wallet {id: $w_nid, investigation_id: $inv}) "
                                    "MERGE (w)-[:TOUCHES_VASP {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: 'VASP_EXIT_POINT', evidence_strength: 'HIGH', amount_btc: $amt}]->(v)",
                                    v_nid=v_nid, vlbl=vasp, vasp_raw_id=vasp_raw_id, w_nid=w_nid,
                                    amt=hop.get("amount_btc", 0.0), inv=investigation_id, aid=actual_aid, eids=art_eids
                                )
                    elif art_type == "INFRASTRUCTURE_HEADER":
                        infra_raw_id = f"INFRA_{eid}"
                        i_nid = f"{investigation_id}_{infra_raw_id}"
                        rare_match = raw.get("rare_fingerprint_match", False)
                        banner = raw.get('persona_a_infra', {}).get('ssh_banner', 'SSH-Daemon')[:16]
                        session.run(
                            "MERGE (i:Infrastructure {id: $i_nid, label: $ilbl, raw_id: $infra_raw_id, type: 'Infrastructure', investigation_id: $inv})",
                            i_nid=i_nid, ilbl=f"Infra: {banner}", infra_raw_id=infra_raw_id, inv=investigation_id
                        )
                        p1_nid = f"{investigation_id}_{persona_a}"
                        if "persona_a_infra" in raw or raw.get("persona") == persona_a:
                            session.run(
                                "MERGE (p1:Persona {id: $p1_nid, label: $pa, raw_id: $pa, investigation_id: $inv}) "
                                "MERGE (i:Infrastructure {id: $i_nid, investigation_id: $inv}) "
                                "MERGE (p1)-[:RUNS_ON {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: $assoc, evidence_strength: $str}]->(i)",
                                p1_nid=p1_nid, pa=persona_a, i_nid=i_nid, inv=investigation_id, aid=actual_aid,
                                eids=[f"{eid}-A"],
                                assoc="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                                str="HIGH" if rare_match else "MEDIUM"
                            )
                        p2_nid = f"{investigation_id}_{persona_b}"
                        if "persona_b_infra" in raw or raw.get("persona") == persona_b:
                            session.run(
                                "MERGE (p2:Persona {id: $p2_nid, label: $pb, raw_id: $pb, investigation_id: $inv}) "
                                "MERGE (i:Infrastructure {id: $i_nid, investigation_id: $inv}) "
                                "MERGE (p2)-[:RUNS_ON {investigation_id: $inv, assessment_id: $aid, evidence_ids: $eids, association: $assoc, evidence_strength: $str}]->(i)",
                                p2_nid=p2_nid, pb=persona_b, i_nid=i_nid, inv=investigation_id, aid=actual_aid,
                                eids=[f"{eid}-B"],
                                assoc="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                                str="HIGH" if rare_match else "MEDIUM"
                            )

                # Merge correlation / conflict relationship with real assessment provenance
                p1_nid = f"{investigation_id}_{persona_a}"
                p2_nid = f"{investigation_id}_{persona_b}"
                if hard_gate_triggered:
                    session.run(
                        "MERGE (p1:Persona {id: $p1_nid, investigation_id: $inv}) "
                        "MERGE (p2:Persona {id: $p2_nid, investigation_id: $inv}) "
                        "MERGE (p1)-[:CONFLICTS_WITH {investigation_id: $inv, reason: 'TEMPORAL_CONCURRENCY', association: 'TEMPORAL_CONCURRENCY', evidence_strength: 'CONTRADICTORY', assessment_id: $aid, evidence_ids: $eids}]->(p2)",
                        p1_nid=p1_nid, p2_nid=p2_nid, inv=investigation_id, aid=actual_aid, eids=actual_eids
                    )
                else:
                    session.run(
                        "MERGE (p1:Persona {id: $p1_nid, investigation_id: $inv}) "
                        "MERGE (p2:Persona {id: $p2_nid, investigation_id: $inv}) "
                        "MERGE (p1)-[:LIKELY_SAME_AS {investigation_id: $inv, state: $state, association: 'ATTRIBUTION_HYPOTHESIS', assessment_id: $aid, evidence_ids: $eids, evidence_strength: 'HIGH'}]->(p2)",
                        p1_nid=p1_nid, p2_nid=p2_nid, inv=investigation_id, state=attribution_state, aid=actual_aid, eids=actual_eids
                    )
            return True
        except Exception as e:
            logger.warning(f"Neo4j sync execution failed ({str(e)})")
            return False

    @classmethod
    def query_neo4j_subgraph(
        cls,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        attribution_state: str = "INCONCLUSIVE",
        hard_gate_triggered: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Executes Cypher MATCH queries against Neo4j strictly scoped by investigation_id:
        p.investigation_id = $inv AND r.investigation_id = $inv AND n.investigation_id = $inv.
        """
        driver = cls._get_neo4j_driver()
        if not driver:
            return None

        p1_nid = f"{investigation_id}_{persona_a}"
        p2_nid = f"{investigation_id}_{persona_b}"

        try:
            with driver.session() as session:
                cypher = """
                MATCH (p:Persona {investigation_id: $inv})
                WHERE p.id IN [$p1_nid, $p2_nid]
                OPTIONAL MATCH (p)-[r {investigation_id: $inv}]-(n {investigation_id: $inv})
                RETURN p, r, n
                """
                results = session.run(cypher, p1_nid=p1_nid, p2_nid=p2_nid, inv=investigation_id)

                nodes_dict = {}
                edges_dict = {}

                for record in results:
                    p = record.get("p")
                    r = record.get("r")
                    n = record.get("n")

                    if p:
                        raw_id = p.get("raw_id") or p.get("id")
                        if raw_id not in nodes_dict:
                            nodes_dict[raw_id] = {
                                "data": {
                                    "id": raw_id,
                                    "label": p.get("label", raw_id),
                                    "type": "Persona",
                                    "investigation_id": investigation_id
                                }
                            }

                    if n:
                        raw_nid = n.get("raw_id") or n.get("id")
                        ntype = list(n.labels)[0] if hasattr(n, 'labels') and n.labels else n.get("type", "Node")
                        if raw_nid not in nodes_dict:
                            node_data = {
                                "id": raw_nid,
                                "label": n.get("label", raw_nid),
                                "type": ntype,
                                "investigation_id": investigation_id
                            }
                            if n.get("fingerprint"):
                                node_data["fingerprint"] = n.get("fingerprint")
                            nodes_dict[raw_nid] = {"data": node_data}

                    if r:
                        src_raw = r.start_node.get("raw_id") or r.start_node.get("id")
                        tgt_raw = r.end_node.get("raw_id") or r.end_node.get("id")
                        r_id = f"e_{src_raw}_{tgt_raw}_{r.type}"
                        eids = r.get("evidence_ids")
                        if not isinstance(eids, list):
                            eids = [str(eids)] if eids else []

                        _add_or_merge_edge(
                            edges_dict=edges_dict,
                            edge_id=r_id,
                            source=src_raw,
                            target=tgt_raw,
                            label=r.type,
                            association=r.get("association", "OBSERVED"),
                            evidence_strength=r.get("evidence_strength", "HIGH"),
                            assessment_id=r.get("assessment_id", f"ASSESS-{investigation_id}"),
                            evidence_ids=eids,
                            extra_fields={"state": r.get("state")} if r.get("state") else None
                        )

                if nodes_dict:
                    metrics = _compute_and_attach_graph_metrics(
                        nodes_dict, edges_dict, persona_a=persona_a, persona_b=persona_b
                    )
                    return {
                        "graph_source": "NEO4J_PROPERTY_GRAPH",
                        "metrics": metrics,
                        "nodes": list(nodes_dict.values()),
                        "edges": list(edges_dict.values())
                    }
        except Exception as e:
            logger.warning(f"Neo4j Cypher query failed ({str(e)}). Falling back to local graph builder.")

        return None

    @classmethod
    def _build_local_cytoscape_graph(
        cls,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        artifacts: List[Dict[str, Any]],
        attribution_state: str,
        hard_gate_triggered: bool,
        assessment_id: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, local property graph constructor with honest evidence semantics,
        investigation scoping, and pure topology metrics.
        """
        nodes_dict = {}
        edges_dict = {}

        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

        nodes_dict[persona_a] = {
            "data": {
                "id": persona_a,
                "label": persona_a,
                "type": "Persona",
                "investigation_id": investigation_id
            }
        }
        nodes_dict[persona_b] = {
            "data": {
                "id": persona_b,
                "label": persona_b,
                "type": "Persona",
                "investigation_id": investigation_id
            }
        }

        for art in artifacts:
            art_type = art.get("artifact_type")
            raw = art.get("raw_payload", {})
            eid = art.get("evidence_id")
            art_eids = [eid] if eid else []

            if art_type == "PGP_KEY":
                key_id = raw.get("key_id", "PGP_UNKNOWN")
                key_node_id = f"PGP_{key_id}"
                if key_node_id not in nodes_dict:
                    nodes_dict[key_node_id] = {
                        "data": {
                            "id": key_node_id,
                            "label": f"PGP: {key_id}",
                            "type": "PGP_Key",
                            "fingerprint": raw.get("key_fingerprint"),
                            "investigation_id": investigation_id
                        }
                    }
                persona = raw.get("persona", persona_a)
                e_id = f"e_{persona}_{key_node_id}"
                _add_or_merge_edge(
                    edges_dict, e_id, persona, key_node_id,
                    label="USED",
                    association="VERIFIED_CRYPTOGRAPHIC_KEY",
                    evidence_strength="VERY_HIGH",
                    assessment_id=actual_aid,
                    evidence_ids=art_eids
                )

            elif art_type == "FORUM_POST":
                forum = raw.get("forum", "Darknet_Forum")
                forum_node_id = f"FORUM_{forum}"
                if forum_node_id not in nodes_dict:
                    nodes_dict[forum_node_id] = {
                        "data": {
                            "id": forum_node_id,
                            "label": forum,
                            "type": "Forum",
                            "investigation_id": investigation_id
                        }
                    }
                post_node_id = f"POST_{eid}"
                nodes_dict[post_node_id] = {
                    "data": {
                        "id": post_node_id,
                        "label": f"Post ({forum})",
                        "type": "Forum_Post",
                        "words": raw.get("word_count"),
                        "investigation_id": investigation_id
                    }
                }
                persona = raw.get("persona", persona_a)
                e_auth = f"e_{persona}_{post_node_id}"
                _add_or_merge_edge(
                    edges_dict, e_auth, persona, post_node_id,
                    label="AUTHORED",
                    association="VERIFIED_AUTHOR",
                    evidence_strength="HIGH",
                    assessment_id=actual_aid,
                    evidence_ids=art_eids
                )
                e_post = f"e_{post_node_id}_{forum_node_id}"
                _add_or_merge_edge(
                    edges_dict, e_post, post_node_id, forum_node_id,
                    label="POSTED_ON",
                    association="POSTED_LOCATION",
                    evidence_strength="HIGH",
                    assessment_id=actual_aid,
                    evidence_ids=art_eids
                )

            elif art_type == "BTC_TRANSACTION":
                cluster_id = raw.get("cluster_id", "BTC_CLUSTER")
                if cluster_id not in nodes_dict:
                    nodes_dict[cluster_id] = {
                        "data": {
                            "id": cluster_id,
                            "label": f"Wallet: {cluster_id}",
                            "type": "Wallet",
                            "method": raw.get("clustering_method"),
                            "investigation_id": investigation_id
                        }
                    }

                inputs = raw.get("inputs", [])
                outputs = raw.get("outputs", [])

                if any(persona_a.lower() in str(inp).lower() for inp in inputs) or raw.get("persona") == persona_a:
                    e_fund = f"e_{persona_a}_{cluster_id}"
                    _add_or_merge_edge(
                        edges_dict, e_fund, persona_a, cluster_id,
                        label="FUNDED_FROM",
                        association="VERIFIED_OWNERSHIP",
                        evidence_strength="HIGH",
                        assessment_id=actual_aid,
                        evidence_ids=art_eids
                    )
                else:
                    e_assoc = f"e_{persona_a}_{cluster_id}"
                    _add_or_merge_edge(
                        edges_dict, e_assoc, persona_a, cluster_id,
                        label="ASSOCIATED_WITH",
                        association="INFERRED_ASSOCIATION",
                        evidence_strength="MEDIUM_HEURISTIC",
                        assessment_id=actual_aid,
                        evidence_ids=art_eids
                    )

                if any(persona_b.lower() in str(out).lower() for out in outputs) or raw.get("recipient_persona") == persona_b:
                    e_tx = f"e_{cluster_id}_{persona_b}"
                    _add_or_merge_edge(
                        edges_dict, e_tx, cluster_id, persona_b,
                        label="TRANSFERRED_TO",
                        association="VERIFIED_RECIPIENT",
                        evidence_strength="HIGH",
                        assessment_id=actual_aid,
                        evidence_ids=art_eids
                    )

                for hop in raw.get("hops_to_vasp", []):
                    vasp = hop.get("vasp_entity")
                    if vasp:
                        vasp_id = f"VASP_{vasp.replace(' ', '_')}"
                        if vasp_id not in nodes_dict:
                            nodes_dict[vasp_id] = {
                                "data": {
                                    "id": vasp_id,
                                    "label": vasp,
                                    "type": "VASP",
                                    "investigation_id": investigation_id
                                }
                            }
                        e_vasp = f"e_{cluster_id}_{vasp_id}"
                        _add_or_merge_edge(
                            edges_dict, e_vasp, cluster_id, vasp_id,
                            label="TOUCHES_VASP",
                            association="VASP_EXIT_POINT",
                            evidence_strength="HIGH",
                            assessment_id=actual_aid,
                            evidence_ids=art_eids,
                            extra_fields={"amount_btc": hop.get("amount_btc")}
                        )

            elif art_type == "INFRASTRUCTURE_HEADER":
                infra_id = f"INFRA_{eid}"
                rare_match = raw.get("rare_fingerprint_match", False)
                if infra_id not in nodes_dict:
                    nodes_dict[infra_id] = {
                        "data": {
                            "id": infra_id,
                            "label": f"Infra: {raw.get('persona_a_infra', {}).get('ssh_banner', 'SSH-Daemon')[:16]}",
                            "type": "Infrastructure",
                            "investigation_id": investigation_id
                        }
                    }

                # Attach to Persona A only if telemetry present
                if "persona_a_infra" in raw or raw.get("persona") == persona_a:
                    e_infra_a = f"e_{persona_a}_{infra_id}"
                    _add_or_merge_edge(
                        edges_dict, e_infra_a, persona_a, infra_id,
                        label="RUNS_ON",
                        association="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                        evidence_strength="HIGH" if rare_match else "MEDIUM",
                        assessment_id=actual_aid,
                        evidence_ids=[f"{eid}-A"] if eid else []
                    )
                # Attach to Persona B only if telemetry present
                if "persona_b_infra" in raw or raw.get("persona") == persona_b:
                    e_infra_b = f"e_{persona_b}_{infra_id}"
                    _add_or_merge_edge(
                        edges_dict, e_infra_b, persona_b, infra_id,
                        label="RUNS_ON",
                        association="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                        evidence_strength="HIGH" if rare_match else "MEDIUM",
                        assessment_id=actual_aid,
                        evidence_ids=[f"{eid}-B"] if eid else []
                    )

        if hard_gate_triggered:
            e_corr = f"e_{persona_a}_{persona_b}_conflict"
            _add_or_merge_edge(
                edges_dict, e_corr, persona_a, persona_b,
                label="CONFLICTS_WITH",
                association="TEMPORAL_CONCURRENCY",
                evidence_strength="CONTRADICTORY",
                assessment_id=actual_aid,
                evidence_ids=actual_eids,
                extra_fields={"reason": "TEMPORAL_CONCURRENCY"}
            )
        else:
            e_corr = f"e_{persona_a}_{persona_b}_inferred"
            _add_or_merge_edge(
                edges_dict, e_corr, persona_a, persona_b,
                label="LIKELY_SAME_AS",
                association="ATTRIBUTION_HYPOTHESIS",
                evidence_strength="HIGH",
                assessment_id=actual_aid,
                evidence_ids=actual_eids,
                extra_fields={"state": attribution_state}
            )

        # Calculate genuine degree centrality across nodes
        metrics = _compute_and_attach_graph_metrics(
            nodes_dict, edges_dict, persona_a=persona_a, persona_b=persona_b
        )

        return {
            "graph_source": "LOCAL_FALLBACK",
            "fallback_reason": "NEO4J_UNAVAILABLE",
            "metrics": metrics,
            "nodes": list(nodes_dict.values()),
            "edges": list(edges_dict.values())
        }

    @classmethod
    def generate_cytoscape_graph(
        cls,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        artifacts: List[Dict[str, Any]],
        attribution_state: str,
        hard_gate_triggered: bool,
        assessment_id: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Syncs artifacts to Neo4j and queries the live graph via Cypher with real degree centrality metrics.
        Falls back to local property graph generation if Neo4j is offline in development mode.
        In production mode, fails closed with HTTP 503 if Neo4j is unavailable.
        """
        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

        driver = cls._get_neo4j_driver()
        if not driver:
            if settings.ENVIRONMENT.lower() == "production":
                raise HTTPException(
                    status_code=503,
                    detail="Neo4j Property Graph service unavailable in production mode"
                )
            return cls._build_local_cytoscape_graph(
                investigation_id, persona_a, persona_b, artifacts, attribution_state, hard_gate_triggered,
                assessment_id=actual_aid, evidence_ids=actual_eids
            )

        cls.sync_to_neo4j(
            investigation_id, persona_a, persona_b, artifacts, attribution_state, hard_gate_triggered,
            assessment_id=actual_aid, evidence_ids=actual_eids
        )

        # Query Neo4j directly via Cypher
        neo4j_graph = cls.query_neo4j_subgraph(
            investigation_id, persona_a, persona_b,
            attribution_state=attribution_state, hard_gate_triggered=hard_gate_triggered
        )
        if neo4j_graph:
            return neo4j_graph

        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="Neo4j Cypher query returned no data in production mode"
            )

        # Fallback
        return cls._build_local_cytoscape_graph(
            investigation_id, persona_a, persona_b, artifacts, attribution_state, hard_gate_triggered,
            assessment_id=actual_aid, evidence_ids=actual_eids
        )
