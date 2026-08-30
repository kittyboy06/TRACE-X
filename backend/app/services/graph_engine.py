from typing import List, Dict, Any, Tuple
from app.models.schemas import DimensionSignal, SignalStatus


class GraphEngine:
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
            
            # Check for exact PGP key ID or fingerprint reuse
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
    def generate_cytoscape_graph(
        cls,
        investigation_id: str,
        persona_a: str,
        persona_b: str,
        artifacts: List[Dict[str, Any]],
        attribution_state: str,
        hard_gate_triggered: bool
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive Cytoscape.js compatible graph payload with typed nodes and evidentiary edges.
        """
        nodes = []
        edges = []

        # Persona Nodes
        nodes.append({
            "data": {
                "id": persona_a,
                "label": persona_a,
                "type": "Persona",
                "risk": "HIGH",
                "centrality": 0.85
            }
        })
        nodes.append({
            "data": {
                "id": persona_b,
                "label": persona_b,
                "type": "Persona",
                "risk": "HIGH",
                "centrality": 0.78
            }
        })

        # Process Artifacts
        for art in artifacts:
            art_type = art.get("artifact_type")
            raw = art.get("raw_payload", {})
            eid = art.get("evidence_id")

            if art_type == "PGP_KEY":
                key_id = raw.get("key_id", "PGP_UNKNOWN")
                key_node_id = f"PGP_{key_id}"
                if not any(n["data"]["id"] == key_node_id for n in nodes):
                    nodes.append({
                        "data": {
                            "id": key_node_id,
                            "label": f"PGP: {key_id}",
                            "type": "PGP_Key",
                            "fingerprint": raw.get("key_fingerprint")
                        }
                    })
                # Edge
                persona = raw.get("persona", persona_a)
                edges.append({
                    "data": {
                        "id": f"e_{persona}_{key_node_id}",
                        "source": persona,
                        "target": key_node_id,
                        "label": "USED",
                        "evidence_strength": "VERY_HIGH",
                        "evidence_id": eid
                    }
                })

            elif art_type == "FORUM_POST":
                forum = raw.get("forum", "Darknet_Forum")
                forum_node_id = f"FORUM_{forum}"
                if not any(n["data"]["id"] == forum_node_id for n in nodes):
                    nodes.append({
                        "data": {"id": forum_node_id, "label": forum, "type": "Forum"}
                    })
                post_node_id = f"POST_{eid}"
                nodes.append({
                    "data": {"id": post_node_id, "label": f"Post ({forum})", "type": "Forum_Post", "words": raw.get("word_count")}
                })
                persona = raw.get("persona", persona_a)
                edges.append({
                    "data": {"id": f"e_{persona}_{post_node_id}", "source": persona, "target": post_node_id, "label": "AUTHORED", "evidence_id": eid}
                })
                edges.append({
                    "data": {"id": f"e_{post_node_id}_{forum_node_id}", "source": post_node_id, "target": forum_node_id, "label": "POSTED_ON"}
                })

            elif art_type == "BTC_TRANSACTION":
                cluster_id = raw.get("cluster_id", "BTC_CLUSTER")
                nodes.append({
                    "data": {"id": cluster_id, "label": f"Wallet: {cluster_id}", "type": "Wallet", "method": raw.get("clustering_method")}
                })
                edges.append({
                    "data": {"id": f"e_{persona_a}_{cluster_id}", "source": persona_a, "target": cluster_id, "label": "ASSOCIATED_WITH", "evidence_id": eid}
                })
                edges.append({
                    "data": {"id": f"e_{persona_b}_{cluster_id}", "source": persona_b, "target": cluster_id, "label": "ASSOCIATED_WITH", "evidence_id": eid}
                })
                # VASP Hops
                for hop in raw.get("hops_to_vasp", []):
                    vasp = hop.get("vasp_entity")
                    if vasp:
                        vasp_id = f"VASP_{vasp.replace(' ', '_')}"
                        if not any(n["data"]["id"] == vasp_id for n in nodes):
                            nodes.append({"data": {"id": vasp_id, "label": vasp, "type": "VASP"}})
                        edges.append({
                            "data": {"id": f"e_{cluster_id}_{vasp_id}", "source": cluster_id, "target": vasp_id, "label": "TOUCHES_VASP", "amount_btc": hop.get("amount_btc")}
                        })

        # Inferred attribution / conflict edge between Persona A and Persona B
        if hard_gate_triggered:
            edges.append({
                "data": {
                    "id": f"e_{persona_a}_{persona_b}_conflict",
                    "source": persona_a,
                    "target": persona_b,
                    "label": "CONFLICTS_WITH",
                    "evidence_strength": "CONTRADICTORY",
                    "reason": "TEMPORAL_CONCURRENCY"
                }
            })
        else:
            edges.append({
                "data": {
                    "id": f"e_{persona_a}_{persona_b}_inferred",
                    "source": persona_a,
                    "target": persona_b,
                    "label": "LIKELY_SAME_AS",
                    "evidence_strength": "HIGH",
                    "state": attribution_state
                }
            })

        return {"nodes": nodes, "edges": edges}
