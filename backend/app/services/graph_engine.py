import logging
from typing import List, Dict, Any, Tuple, Optional
from app.models.schemas import DimensionSignal, SignalStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


def _compute_and_attach_graph_metrics(
    nodes_dict: Dict[str, Any],
    edges_dict: Dict[str, Any],
    attribution_state: str,
    hard_gate_triggered: bool
):
    """
    Computes genuine degree centrality, directional degree metrics, and threat risk levels
    based on the actual topology of the graph.
    """
    degrees = {nid: 0 for nid in nodes_dict}
    in_degrees = {nid: 0 for nid in nodes_dict}
    out_degrees = {nid: 0 for nid in nodes_dict}

    for edge in edges_dict.values():
        src = edge["data"]["source"]
        tgt = edge["data"]["target"]
        if src in degrees:
            degrees[src] += 1
            out_degrees[src] += 1
        if tgt in degrees:
            degrees[tgt] += 1
            in_degrees[tgt] += 1

    total_nodes = len(nodes_dict)
    denom = max(total_nodes - 1, 1)

    for nid, node in nodes_dict.items():
        deg = degrees.get(nid, 0)
        centrality = round(deg / denom, 3)
        node["data"]["degree_centrality"] = centrality
        node["data"]["centrality"] = centrality  # For backward-compatible UI widgets
        node["data"]["in_degree"] = in_degrees.get(nid, 0)
        node["data"]["out_degree"] = out_degrees.get(nid, 0)
        node["data"]["degree"] = deg

        # Dynamic risk score based on connectivity and node type
        ntype = node["data"].get("type", "Node")
        if ntype == "Persona":
            if attribution_state == "CONFIRMED_LINK":
                node["data"]["risk"] = "CRITICAL"
                node["data"]["threat_score"] = round(min(0.85 + centrality * 0.15, 1.0), 2)
            elif hard_gate_triggered:
                node["data"]["risk"] = "CONTRADICTORY"
                node["data"]["threat_score"] = 0.20
            else:
                node["data"]["risk"] = "HIGH" if centrality >= 0.25 else "EVALUATING"
                node["data"]["threat_score"] = round(min(0.50 + centrality * 0.40, 0.95), 2)
        elif ntype == "PGP_Key":
            node["data"]["risk"] = "CRITICAL" if deg >= 2 else "HIGH"
        elif ntype == "Wallet":
            node["data"]["risk"] = "HIGH" if deg >= 2 else "MEDIUM"
        elif ntype == "Infrastructure":
            node["data"]["risk"] = "HIGH" if deg >= 2 else "MEDIUM"
        elif ntype == "VASP":
            node["data"]["risk"] = "IDENTIFIED_ENTITY"
        else:
            node["data"]["risk"] = "INFORMATIONAL"


class GraphEngine:
    _neo4j_driver = None
    _neo4j_checked = False

    @classmethod
    def _get_neo4j_driver(cls):
        if cls._neo4j_checked:
            return cls._neo4j_driver
        cls._neo4j_checked = True
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
        weight_infra: float = 0.15
    ) -> Tuple[DimensionSignal, DimensionSignal]:
        """
        Extracts Cryptographic (PGP reuse) and Infrastructure reuse signals.
        """
        # 1. Cryptographic Analysis
        if len(pgp_artifacts) >= 2:
            keys = [a.get("raw_payload", {}).get("key_id") for a in pgp_artifacts]
            fingerprints = [a.get("raw_payload", {}).get("key_fingerprint") for a in pgp_artifacts]
            
            if len(set(keys)) == 1 and keys[0] is not None:
                raw_crypto = 0.95
                details_crypto = {
                    "matched_key_id": keys[0],
                    "matched_fingerprint": fingerprints[0] if fingerprints else "UNKNOWN",
                    "evidence_strength": "VERY_HIGH",
                    "rationale": f"Direct PGP Key reuse ({keys[0]}) observed across disparate forum profiles."
                }
            else:
                raw_crypto = 0.10
                details_crypto = {
                    "evidence_strength": "CONTRADICTORY",
                    "rationale": "Distinct, non-overlapping PGP keys deployed with independent cryptographic algorithms."
                }
            status_crypto = SignalStatus.VALID
        elif len(pgp_artifacts) == 1:
            raw_crypto = 0.50
            status_crypto = SignalStatus.VALID
            details_crypto = {"rationale": "Single PGP key identified; awaiting counter-profile verification."}
        else:
            raw_crypto = 0.0
            status_crypto = SignalStatus.NOT_ENOUGH_EVIDENCE
            details_crypto = {"rationale": "No cryptographic keys located in evidence package."}

        crypto_signal = DimensionSignal(
            dimension_name="cryptographic",
            status=status_crypto,
            raw_score=raw_crypto,
            reliability_factor=1.0,
            adjusted_score=raw_crypto,
            configured_weight=weight_crypto,
            contribution=round(weight_crypto * raw_crypto, 4),
            evidence_ids=[a.get("evidence_id", "") for a in pgp_artifacts if "evidence_id" in a],
            supporting_details=details_crypto
        )

        # 2. Infrastructure Analysis
        if infra_artifacts:
            raw_payload = infra_artifacts[0].get("raw_payload", {})
            rare_match = raw_payload.get("rare_fingerprint_match", False)
            
            if rare_match:
                raw_infra = 0.65
                details_infra = {
                    "shared_tls_cert": raw_payload.get("persona_a_infra", {}).get("tls_cert_serial"),
                    "shared_ssh_banner": raw_payload.get("persona_a_infra", {}).get("ssh_banner"),
                    "rare_fingerprint_match": True,
                    "rationale": "Shared TLS certificate serial and identical SSH server daemon fingerprint."
                }
            else:
                raw_infra = 0.20
                details_infra = {"rationale": "Generic CDN / hosting infrastructure; inconclusive fingerprint."}
            status_infra = SignalStatus.VALID
        else:
            raw_infra = 0.0
            status_infra = SignalStatus.NOT_ENOUGH_EVIDENCE
            details_infra = {"rationale": "No server or network infrastructure telemetry available."}

        infra_signal = DimensionSignal(
            dimension_name="infrastructure",
            status=status_infra,
            raw_score=raw_infra,
            reliability_factor=1.0,
            adjusted_score=raw_infra,
            configured_weight=weight_infra,
            contribution=round(weight_infra * raw_infra, 4),
            evidence_ids=[a.get("evidence_id", "") for a in infra_artifacts if "evidence_id" in a],
            supporting_details=details_infra
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
        Persists CTI property graph into Neo4j via Cypher with precise evidentiary associations.
        """
        driver = cls._get_neo4j_driver()
        if not driver:
            return False

        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

        try:
            with driver.session() as session:
                # Merge target personas
                session.run(
                    "MERGE (p1:Persona {id: $p1, label: $p1, investigation_id: $inv}) "
                    "MERGE (p2:Persona {id: $p2, label: $p2, investigation_id: $inv})",
                    p1=persona_a, p2=persona_b, inv=investigation_id
                )

                for art in artifacts:
                    art_type = art.get("artifact_type")
                    raw = art.get("raw_payload", {})
                    eid = art.get("evidence_id", "EV-UNKNOWN")
                    
                    if art_type == "PGP_KEY":
                        key_id = raw.get("key_id", "UNKNOWN")
                        persona = raw.get("persona", persona_a)
                        session.run(
                            "MERGE (k:PGP_Key {id: $key_id, label: $key_lbl, fingerprint: $fp, type: 'PGP_Key'}) "
                            "MERGE (p:Persona {id: $persona}) "
                            "MERGE (p)-[:USED {evidence_id: $eid, strength: 'VERY_HIGH', association: 'VERIFIED_CRYPTOGRAPHIC_KEY'}]->(k)",
                            key_id=f"PGP_{key_id}", key_lbl=f"PGP: {key_id}", fp=raw.get("key_fingerprint", ""), persona=persona, eid=eid
                        )
                    elif art_type == "FORUM_POST":
                        forum = raw.get("forum", "Darknet_Forum")
                        persona = raw.get("persona", persona_a)
                        session.run(
                            "MERGE (f:Forum {id: $forum, label: $forum, type: 'Forum'}) "
                            "MERGE (post:Forum_Post {id: $post_id, label: $post_lbl, type: 'Forum_Post', word_count: $wc}) "
                            "MERGE (p:Persona {id: $persona}) "
                            "MERGE (p)-[:AUTHORED {evidence_id: $eid, association: 'VERIFIED_AUTHOR'}]->(post) "
                            "MERGE (post)-[:POSTED_ON]->(f)",
                            forum=f"FORUM_{forum}", post_id=f"POST_{eid}", post_lbl=f"Post ({forum})", wc=raw.get("word_count", 0), persona=persona, eid=eid
                        )
                    elif art_type == "BTC_TRANSACTION":
                        cluster_id = raw.get("cluster_id", "BTC_CLUSTER")
                        session.run(
                            "MERGE (w:Wallet {id: $wid, label: $wlbl, type: 'Wallet', method: $method})",
                            wid=cluster_id, wlbl=f"Wallet: {cluster_id}", method=raw.get("clustering_method", "CIOH")
                        )
                        # Differentiate verified funder from inferred association
                        inputs = raw.get("inputs", [])
                        if any(persona_a.lower() in str(inp).lower() for inp in inputs) or raw.get("persona") == persona_a:
                            session.run(
                                "MERGE (p:Persona {id: $pa}) MERGE (w:Wallet {id: $wid}) "
                                "MERGE (p)-[:FUNDED_FROM {evidence_id: $eid, association: 'VERIFIED_OWNERSHIP', evidence_strength: 'HIGH'}]->(w)",
                                pa=persona_a, wid=cluster_id, eid=eid
                            )
                        else:
                            session.run(
                                "MERGE (p:Persona {id: $pa}) MERGE (w:Wallet {id: $wid}) "
                                "MERGE (p)-[:ASSOCIATED_WITH {evidence_id: $eid, association: 'INFERRED_ASSOCIATION', evidence_strength: 'MEDIUM_HEURISTIC'}]->(w)",
                                pa=persona_a, wid=cluster_id, eid=eid
                            )

                        outputs = raw.get("outputs", [])
                        if any(persona_b.lower() in str(out).lower() for out in outputs) or raw.get("recipient_persona") == persona_b:
                            session.run(
                                "MERGE (p:Persona {id: $pb}) MERGE (w:Wallet {id: $wid}) "
                                "MERGE (w)-[:TRANSFERRED_TO {evidence_id: $eid, association: 'VERIFIED_RECIPIENT', evidence_strength: 'HIGH'}]->(p)",
                                pb=persona_b, wid=cluster_id, eid=eid
                            )

                        for hop in raw.get("hops_to_vasp", []):
                            vasp = hop.get("vasp_entity")
                            if vasp:
                                vasp_id = f"VASP_{vasp.replace(' ', '_')}"
                                session.run(
                                    "MERGE (v:VASP {id: $vid, label: $vlbl, type: 'VASP'}) "
                                    "MERGE (w:Wallet {id: $wid}) "
                                    "MERGE (w)-[:TOUCHES_VASP {amount_btc: $amt}]->(v)",
                                    vid=vasp_id, vlbl=vasp, wid=cluster_id, amt=hop.get("amount_btc", 0.0)
                                )
                    elif art_type == "INFRASTRUCTURE_HEADER":
                        infra_id = f"INFRA_{eid}"
                        rare_match = raw.get("rare_fingerprint_match", False)
                        session.run(
                            "MERGE (i:Infrastructure {id: $iid, label: $ilbl, type: 'Infrastructure'})",
                            iid=infra_id, ilbl=f"Infra: {raw.get('persona_a_infra', {}).get('ssh_banner', 'SSH-Daemon')[:16]}"
                        )
                        # Connect Persona A with distinct evidence context
                        if "persona_a_infra" in raw or raw.get("persona") == persona_a:
                            session.run(
                                "MERGE (p1:Persona {id: $pa}) MERGE (i:Infrastructure {id: $iid}) "
                                "MERGE (p1)-[:RUNS_ON {evidence_id: $eid, association: $assoc, evidence_strength: $str}]->(i)",
                                pa=persona_a, iid=infra_id, eid=f"{eid}-A",
                                assoc="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                                str="HIGH" if rare_match else "MEDIUM"
                            )
                        # Connect Persona B with distinct evidence context
                        if "persona_b_infra" in raw or raw.get("persona") == persona_b:
                            session.run(
                                "MERGE (p2:Persona {id: $pb}) MERGE (i:Infrastructure {id: $iid}) "
                                "MERGE (p2)-[:RUNS_ON {evidence_id: $eid, association: $assoc, evidence_strength: $str}]->(i)",
                                pb=persona_b, iid=infra_id, eid=f"{eid}-B",
                                assoc="VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                                str="HIGH" if rare_match else "MEDIUM"
                            )

                # Merge correlation / conflict relationship with real assessment provenance
                if hard_gate_triggered:
                    session.run(
                        "MERGE (p1:Persona {id: $p1}) MERGE (p2:Persona {id: $p2}) "
                        "MERGE (p1)-[:CONFLICTS_WITH {reason: 'TEMPORAL_CONCURRENCY', evidence_strength: 'CONTRADICTORY', assessment_id: $aid, evidence_ids: $eids}]->(p2)",
                        p1=persona_a, p2=persona_b, aid=actual_aid, eids=actual_eids
                    )
                else:
                    session.run(
                        "MERGE (p1:Persona {id: $p1}) MERGE (p2:Persona {id: $p2}) "
                        "MERGE (p1)-[:LIKELY_SAME_AS {state: $state, assessment_id: $aid, evidence_ids: $eids, evidence_strength: 'HIGH'}]->(p2)",
                        p1=persona_a, p2=persona_b, state=attribution_state, aid=actual_aid, eids=actual_eids
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
        Executes Cypher MATCH queries against Neo4j and computes degree centrality across the returned topology.
        """
        driver = cls._get_neo4j_driver()
        if not driver:
            return None

        try:
            with driver.session() as session:
                cypher = """
                MATCH (p:Persona)
                WHERE p.id IN [$pa, $pb] OR p.investigation_id = $inv
                OPTIONAL MATCH (p)-[r]-(n)
                RETURN p, r, n
                """
                results = session.run(cypher, pa=persona_a, pb=persona_b, inv=investigation_id)
                
                nodes_dict = {}
                edges_dict = {}

                for record in results:
                    p = record.get("p")
                    r = record.get("r")
                    n = record.get("n")

                    if p:
                        pid = p.get("id", str(p.element_id if hasattr(p, 'element_id') else p.id))
                        if pid not in nodes_dict:
                            nodes_dict[pid] = {
                                "data": {
                                    "id": pid,
                                    "label": p.get("label", pid),
                                    "type": "Persona"
                                }
                            }

                    if n:
                        nid = n.get("id", str(n.element_id if hasattr(n, 'element_id') else n.id))
                        ntype = list(n.labels)[0] if hasattr(n, 'labels') and n.labels else n.get("type", "Node")
                        if nid not in nodes_dict:
                            nodes_dict[nid] = {
                                "data": {
                                    "id": nid,
                                    "label": n.get("label", nid),
                                    "type": ntype,
                                    "fingerprint": n.get("fingerprint")
                                }
                            }

                    if r:
                        r_id = f"e_{r.start_node['id'] if 'id' in r.start_node else r.id}_{r.end_node['id'] if 'id' in r.end_node else r.id}_{r.type}"
                        if r_id not in edges_dict:
                            source_id = r.start_node.get("id", str(r.start_node.id))
                            target_id = r.end_node.get("id", str(r.end_node.id))
                            edges_dict[r_id] = {
                                "data": {
                                    "id": r_id,
                                    "source": source_id,
                                    "target": target_id,
                                    "label": r.type,
                                    "evidence_id": r.get("evidence_id"),
                                    "evidence_strength": r.get("evidence_strength", "HIGH"),
                                    "association": r.get("association"),
                                    "state": r.get("state"),
                                    "assessment_id": r.get("assessment_id"),
                                    "evidence_ids": r.get("evidence_ids")
                                }
                            }

                if nodes_dict:
                    _compute_and_attach_graph_metrics(nodes_dict, edges_dict, attribution_state, hard_gate_triggered)
                    return {
                        "graph_source": "NEO4J_PROPERTY_GRAPH",
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
        Deterministic, local property graph constructor with honest evidence semantics and real degree centrality metrics.
        """
        nodes_dict = {}
        edges_dict = {}

        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

        nodes_dict[persona_a] = {
            "data": {
                "id": persona_a,
                "label": persona_a,
                "type": "Persona"
            }
        }
        nodes_dict[persona_b] = {
            "data": {
                "id": persona_b,
                "label": persona_b,
                "type": "Persona"
            }
        }

        for art in artifacts:
            art_type = art.get("artifact_type")
            raw = art.get("raw_payload", {})
            eid = art.get("evidence_id")

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
                            "evidence_id": eid
                        }
                    }
                persona = raw.get("persona", persona_a)
                e_id = f"e_{persona}_{key_node_id}"
                edges_dict[e_id] = {
                    "data": {
                        "id": e_id,
                        "source": persona,
                        "target": key_node_id,
                        "label": "USED",
                        "association": "VERIFIED_CRYPTOGRAPHIC_KEY",
                        "evidence_strength": "VERY_HIGH",
                        "evidence_id": eid
                    }
                }

            elif art_type == "FORUM_POST":
                forum = raw.get("forum", "Darknet_Forum")
                forum_node_id = f"FORUM_{forum}"
                if forum_node_id not in nodes_dict:
                    nodes_dict[forum_node_id] = {
                        "data": {"id": forum_node_id, "label": forum, "type": "Forum"}
                    }
                post_node_id = f"POST_{eid}"
                nodes_dict[post_node_id] = {
                    "data": {
                        "id": post_node_id,
                        "label": f"Post ({forum})",
                        "type": "Forum_Post",
                        "words": raw.get("word_count"),
                        "evidence_id": eid
                    }
                }
                persona = raw.get("persona", persona_a)
                e_auth = f"e_{persona}_{post_node_id}"
                edges_dict[e_auth] = {
                    "data": {"id": e_auth, "source": persona, "target": post_node_id, "label": "AUTHORED", "association": "VERIFIED_AUTHOR", "evidence_id": eid}
                }
                e_post = f"e_{post_node_id}_{forum_node_id}"
                edges_dict[e_post] = {
                    "data": {"id": e_post, "source": post_node_id, "target": forum_node_id, "label": "POSTED_ON"}
                }

            elif art_type == "BTC_TRANSACTION":
                cluster_id = raw.get("cluster_id", "BTC_CLUSTER")
                if cluster_id not in nodes_dict:
                    nodes_dict[cluster_id] = {
                        "data": {"id": cluster_id, "label": f"Wallet: {cluster_id}", "type": "Wallet", "method": raw.get("clustering_method"), "evidence_id": eid}
                    }
                
                inputs = raw.get("inputs", [])
                outputs = raw.get("outputs", [])
                
                if any(persona_a.lower() in str(inp).lower() for inp in inputs) or raw.get("persona") == persona_a:
                    e_fund = f"e_{persona_a}_{cluster_id}"
                    edges_dict[e_fund] = {
                        "data": {
                            "id": e_fund,
                            "source": persona_a,
                            "target": cluster_id,
                            "label": "FUNDED_FROM",
                            "association": "VERIFIED_OWNERSHIP",
                            "evidence_strength": "HIGH",
                            "evidence_id": eid
                        }
                    }
                else:
                    e_assoc = f"e_{persona_a}_{cluster_id}"
                    edges_dict[e_assoc] = {
                        "data": {
                            "id": e_assoc,
                            "source": persona_a,
                            "target": cluster_id,
                            "label": "ASSOCIATED_WITH",
                            "association": "INFERRED_ASSOCIATION",
                            "evidence_strength": "MEDIUM_HEURISTIC",
                            "evidence_id": eid
                        }
                    }

                if any(persona_b.lower() in str(out).lower() for out in outputs) or raw.get("recipient_persona") == persona_b:
                    e_tx = f"e_{cluster_id}_{persona_b}"
                    edges_dict[e_tx] = {
                        "data": {
                            "id": e_tx,
                            "source": cluster_id,
                            "target": persona_b,
                            "label": "TRANSFERRED_TO",
                            "association": "VERIFIED_RECIPIENT",
                            "evidence_strength": "HIGH",
                            "evidence_id": eid
                        }
                    }

                for hop in raw.get("hops_to_vasp", []):
                    vasp = hop.get("vasp_entity")
                    if vasp:
                        vasp_id = f"VASP_{vasp.replace(' ', '_')}"
                        if vasp_id not in nodes_dict:
                            nodes_dict[vasp_id] = {"data": {"id": vasp_id, "label": vasp, "type": "VASP"}}
                        e_vasp = f"e_{cluster_id}_{vasp_id}"
                        edges_dict[e_vasp] = {
                            "data": {"id": e_vasp, "source": cluster_id, "target": vasp_id, "label": "TOUCHES_VASP", "amount_btc": hop.get("amount_btc")}
                        }

            elif art_type == "INFRASTRUCTURE_HEADER":
                infra_id = f"INFRA_{eid}"
                rare_match = raw.get("rare_fingerprint_match", False)
                if infra_id not in nodes_dict:
                    nodes_dict[infra_id] = {
                        "data": {"id": infra_id, "label": f"Infra: {raw.get('persona_a_infra', {}).get('ssh_banner', 'SSH-Daemon')[:16]}", "type": "Infrastructure", "evidence_id": eid}
                    }
                
                # Attach to Persona A only if telemetry present
                if "persona_a_infra" in raw or raw.get("persona") == persona_a:
                    e_infra_a = f"e_{persona_a}_{infra_id}"
                    edges_dict[e_infra_a] = {
                        "data": {
                            "id": e_infra_a,
                            "source": persona_a,
                            "target": infra_id,
                            "label": "RUNS_ON",
                            "association": "VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                            "evidence_strength": "HIGH" if rare_match else "MEDIUM",
                            "evidence_id": f"{eid}-A"
                        }
                    }
                # Attach to Persona B only if telemetry present
                if "persona_b_infra" in raw or raw.get("persona") == persona_b:
                    e_infra_b = f"e_{persona_b}_{infra_id}"
                    edges_dict[e_infra_b] = {
                        "data": {
                            "id": e_infra_b,
                            "source": persona_b,
                            "target": infra_id,
                            "label": "RUNS_ON",
                            "association": "VERIFIED_INFRASTRUCTURE" if rare_match else "INFERRED_INFRASTRUCTURE",
                            "evidence_strength": "HIGH" if rare_match else "MEDIUM",
                            "evidence_id": f"{eid}-B"
                        }
                    }

        if hard_gate_triggered:
            e_corr = f"e_{persona_a}_{persona_b}_conflict"
            edges_dict[e_corr] = {
                "data": {
                    "id": e_corr,
                    "source": persona_a,
                    "target": persona_b,
                    "label": "CONFLICTS_WITH",
                    "evidence_strength": "CONTRADICTORY",
                    "reason": "TEMPORAL_CONCURRENCY",
                    "assessment_id": actual_aid,
                    "evidence_ids": actual_eids
                }
            }
        else:
            e_corr = f"e_{persona_a}_{persona_b}_inferred"
            edges_dict[e_corr] = {
                "data": {
                    "id": e_corr,
                    "source": persona_a,
                    "target": persona_b,
                    "label": "LIKELY_SAME_AS",
                    "evidence_strength": "HIGH",
                    "state": attribution_state,
                    "assessment_id": actual_aid,
                    "evidence_ids": actual_eids
                }
            }

        # Calculate genuine degree centrality across nodes
        _compute_and_attach_graph_metrics(nodes_dict, edges_dict, attribution_state, hard_gate_triggered)

        return {
            "graph_source": "LOCAL_FALLBACK",
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
        Falls back to local property graph generation if Neo4j is offline.
        """
        actual_aid = assessment_id or f"ASSESS-{investigation_id}"
        actual_eids = evidence_ids or [a.get("evidence_id", "") for a in artifacts if a.get("evidence_id")]

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

        # Fallback
        return cls._build_local_cytoscape_graph(
            investigation_id, persona_a, persona_b, artifacts, attribution_state, hard_gate_triggered,
            assessment_id=actual_aid, evidence_ids=actual_eids
        )
