"""
SuppressionEngine — load cutoff + max_responders cap.
Drops nodes above 90% load; enforces responder ceiling; penalises degraded nodes.
"""
import logging
from typing import List, Tuple, Dict, Any
from .registry import NodeEntry

logger = logging.getLogger(__name__)
LOAD_CUTOFF = 90.0
DEGRADED_PENALTY = 20


class SuppressionEngine:
    def __init__(self, load_cutoff: float = LOAD_CUTOFF):
        self.load_cutoff = load_cutoff

    def apply(self, eligible: List[NodeEntry], request: Dict[str, Any]) -> Tuple[List[NodeEntry], int]:
        max_r = request.get("target_filter", {}).get("max_responders", 10)
        pre = len(eligible)
        nodes = [n for n in eligible if n.effective_load() <= self.load_cutoff]
        overload_dropped = pre - len(nodes)

        nodes.sort(key=lambda n: -(n.priority - (DEGRADED_PENALTY if n.status == "degraded" else 0) - n.effective_load() * 0.1))
        selected = nodes[:max_r]
        suppressed = len(nodes) - len(selected) + overload_dropped
        logger.info(f"[Suppression] selected={len(selected)} suppressed={suppressed} cap={max_r}")
        return selected, suppressed
