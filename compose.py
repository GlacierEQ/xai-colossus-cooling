"""Explicit Cooling–Servers–Security asynchronous composition host.

``compose`` is a bounded evidence assembly entry point.  It mounts the two
published sibling package contracts by explicit checkout path, creates the
Cooling runtime under an already-running event loop, and returns a rich receipt
for a declared synthetic or integration scenario.  It does not discover
infrastructure, execute external mitigations, or infer security incidents.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


class CompositionInputError(ValueError):
    """Raised when a versioned composition request is incomplete or ambiguous."""


def _ensure_local_import_paths() -> None:
    for path in (ROOT, SRC):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _mount_sibling_package(checkout: str | Path, package_name: str) -> Path:
    root = Path(checkout).resolve()
    package_root = root / package_name
    init_file = package_root / "__init__.py"
    if not init_file.is_file():
        raise CompositionInputError(
            f"{package_name} package is not present in checkout: {root}"
        )

    loaded = sys.modules.get(package_name)
    if loaded is not None:
        loaded_file = getattr(loaded, "__file__", None)
        if loaded_file and package_root not in Path(loaded_file).resolve().parents:
            raise CompositionInputError(
                f"{package_name} is already loaded from a different checkout"
            )
    else:
        value = str(root)
        if value not in sys.path:
            sys.path.insert(0, value)
        importlib.import_module(package_name)
    return root


def _validate_revisions(revisions: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(revisions, Mapping):
        raise CompositionInputError("component_revisions must be a mapping")
    required = ("cooling", "servers", "security")
    normalized: dict[str, str] = {}
    for component in required:
        revision = revisions.get(component)
        if not isinstance(revision, str) or not revision.strip():
            raise CompositionInputError(
                f"component_revisions[{component!r}] must be a non-empty string"
            )
        normalized[component] = revision
    return normalized


def _validate_composition_id(composition_id: str) -> str:
    if not isinstance(composition_id, str) or not composition_id.strip():
        raise CompositionInputError("composition_id must be a non-empty string")
    return composition_id


async def compose(
    *,
    composition_id: str,
    component_revisions: Mapping[str, str],
    servers_checkout: str | Path,
    security_checkout: str | Path,
    manifest: Mapping[str, Any],
    zones: Sequence[Any],
    traffic_patterns: Sequence[Mapping[str, Any]] = (),
    router_requests: Sequence[Mapping[str, Any]] = (),
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Assemble one versioned Cooling–Servers–Security evidence scenario.

    The coroutine requires an active event loop.  Its returned receipt binds a
    caller-provided composition id and component revisions to thermal tick,
    deterministic declared-capacity placement, receipt-gated security analysis,
    router responses, and asynchronously flushed audit events.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError as exc:
        raise RuntimeError(
            "compose() must be awaited from a running event loop"
        ) from exc

    normalized_id = _validate_composition_id(composition_id)
    revisions = _validate_revisions(component_revisions)
    if not isinstance(manifest, Mapping):
        raise CompositionInputError("manifest must be a mapping")
    if isinstance(zones, (str, bytes)) or not isinstance(zones, Sequence):
        raise CompositionInputError("zones must be a sequence")
    if isinstance(traffic_patterns, (str, bytes)) or not isinstance(
        traffic_patterns, Sequence
    ):
        raise CompositionInputError("traffic_patterns must be a sequence")
    if isinstance(router_requests, (str, bytes)) or not isinstance(
        router_requests, Sequence
    ):
        raise CompositionInputError("router_requests must be a sequence")

    _ensure_local_import_paths()
    server_root = _mount_sibling_package(servers_checkout, "xai_colossus_servers")
    security_root = _mount_sibling_package(security_checkout, "xai_colossus_security")

    from apex_core.thermal_orchestrator import APEXThermalOrchestrator, CoolingMode
    from connectors.mcp_router import MCPRouterConnector
    from memory.aspen_grove_logger import AspenGroveLogger
    from xai_colossus_servers import Node

    orchestrator = APEXThermalOrchestrator(
        mode=CoolingMode.COLOSSUS,
        manifest=dict(manifest),
    )
    if orchestrator._fabric is None or orchestrator._hydra is None:
        raise RuntimeError(
            "phase four adapters were not assembled; verify the sibling package paths"
        )

    original_logger = orchestrator.aspen_logger
    await original_logger.shutdown()
    audit_path = Path(
        audit_log_path or ROOT / "audit_logs" / "composition_audit.ndjson"
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_logger = AspenGroveLogger(log_path=str(audit_path))
    audit_logger.start()
    router = MCPRouterConnector(logger=audit_logger)
    orchestrator.aspen_logger = audit_logger
    orchestrator._mcp_router = router

    for zone in zones:
        orchestrator.register_zone(zone)

    placement_nodes = [
        Node(
            id=node.node_id,
            kw=float(node.power_watts) / 1_000.0,
            rack_pref=node.rack_id,
        )
        for node in orchestrator.all_nodes
    ]
    placement = orchestrator._fabric.plan_placement(placement_nodes)
    thermal_tick = await orchestrator.tick_cycle()
    security_analysis = await orchestrator._hydra.analyze_traffic_patterns(
        traffic_patterns,
        tick_num=orchestrator.tick,
    )

    for request in router_requests:
        if not isinstance(request, Mapping):
            raise CompositionInputError("router_requests entries must be mappings")
        router.queue_request(dict(request))
    router_responses = await router.process_tick(orchestrator)

    await audit_logger.log_event_async(
        {
            "event": "COMPOSITION_COMPLETED",
            "composition_id": normalized_id,
            "component_revisions": revisions,
            "thermal_tick": thermal_tick["tick"],
            "placement_ok": placement["ok"],
            "security_threat_level": security_analysis["threat_level"],
            "router_response_count": len(router_responses),
        }
    )
    await audit_logger.shutdown()

    audit_events = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    diagnostic = (
        orchestrator._last_fabric_diagnostic
        or await orchestrator._fabric.run_nccl_diagnostic("Main-Backbone")
    )
    return {
        "composition_id": normalized_id,
        "component_revisions": revisions,
        "component_checkouts": {
            "cooling": str(ROOT),
            "servers": str(server_root),
            "security": str(security_root),
        },
        "thermal": {
            "tick": thermal_tick,
            "registered_zones": [zone.zone_id for zone in orchestrator.zones],
            "registered_nodes": len(orchestrator.all_nodes),
        },
        "servers": {
            "placement": placement,
            "diagnostic": diagnostic,
        },
        "security": security_analysis,
        "router": {
            "responses": router_responses,
            "response_count": len(router_responses),
        },
        "audit": {
            "path": str(audit_path),
            "events": audit_events,
            "overflow_count": audit_logger.overflow_count,
        },
        "limits": {
            "external_actions_executed": security_analysis["external_actions_executed"],
            "security_incidents_inferred_from_entropy": 0,
            "live_infrastructure_discovery": False,
        },
    }
