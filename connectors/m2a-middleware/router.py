"""
RelevanceRouter — 4-condition eligibility filter for M2A broadcasts.
Conditions (all must pass): pillar scope, capabilities, domains, latency class.
"""
import logging
from typing import List, Dict, Any
from .registry import NodeRegistry, NodeEntry

logger = logging.getLogger(__name__)
LATENCY_ORDER = {"realtime": 0, "near_realtime": 1, "batch": 2}


class RelevanceRouter:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    def evaluate(self, request: Dict[str, Any]) -> List[NodeEntry]:
        tf = request.get("target_filter", {})
        pillar = tf.get("pillar_scope") or request.get("issuer", {}).get("pillar", "all")
        req_caps = set(tf.get("required_capabilities", []))
        req_domains = set(tf.get("required_domains", []))
        req_latency = tf.get("latency_class")

        candidates = self.registry.by_pillar(pillar)
        eligible = []
        for node in candidates:
            if req_caps and not req_caps.issubset(set(node.capabilities)):
                continue
            if req_domains and not req_domains.intersection(set(node.domains)):
                continue
            if req_latency:
                if LATENCY_ORDER.get(node.latency_class, 99) > LATENCY_ORDER.get(req_latency, 99):
                    continue
            eligible.append(node)

        eligible.sort(key=lambda n: (-n.priority, n.effective_load()))
        logger.info(f"[Router] {request.get('request_type')} pillar={pillar} eligible={len(eligible)}/{len(candidates)}")
        return eligible
