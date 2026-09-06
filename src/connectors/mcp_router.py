"""APEX Model Context Protocol (MCP) Router

Bridges Vercel, Supabase, and Notion MCP integrations into the APEX tick loop.
Validates requests via MCPRequestValidator and dispatches to the live orchestrator.

v1.3.0 additions (issue #16):
  - dispatch() alias for process_tick() (tick_cycle calls dispatch)
  - asyncio.Queue support: queue_async() for non-blocking inbound push
  - zone_budget_override tool — override thermal budget for a zone live
  - fusion_dispatch tool — trigger named fusion mode from MCP
  - thermal_status tool — return current zone/node telemetry snapshot
"""

import asyncio
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

from schemas.mcp_request_validator import MCPRequestValidator
from memory.aspen_grove_logger import AspenGroveLogger


class MCPRouterConnector:
    """Route MCP tool-call requests into APEX Orchestrator cooling actions."""

    # MCP tools implemented by this router
    SUPPORTED_TOOLS = {
        "emergency_blast",
        "predictive_sweep",
        "zone_budget_override",
        "fusion_dispatch",
        "thermal_status",
    }

    def __init__(self, logger: Optional[AspenGroveLogger] = None):
        self.validator = MCPRequestValidator()
        self.logger = logger or AspenGroveLogger()
        # Synchronous deque — used by queue_request() / process_tick()
        self.pending_requests: deque = deque()
        # Async queue — used by queue_async() for non-blocking push from coroutines
        self._async_queue: asyncio.Queue = asyncio.Queue()
        self.dispatch_log_path = os.path.expandvars("$HOME/logs/mcp_dispatch_audit.log")
        os.makedirs(os.path.dirname(self.dispatch_log_path), exist_ok=True)

    # ------------------------------------------------------------------
    # Inbound queue helpers
    # ------------------------------------------------------------------

    # Domain request_type → JSON-RPC tools/call name
    DOMAIN_TOOL_MAP = {
        "emergency_broadcast": "emergency_blast",
        "emergency_blast": "emergency_blast",
        "request_zone_snapshot": "thermal_status",
        "thermal_status": "thermal_status",
        "predictive_sweep": "predictive_sweep",
        "zone_budget_override": "zone_budget_override",
        "fusion_dispatch": "fusion_dispatch",
        "EMERGENCY": "emergency_blast",
        "ZONE_SNAPSHOT": "thermal_status",
    }

    def queue_request(self, payload: Dict[str, Any]) -> None:
        """Inject a request synchronously (webhook / test helpers)."""
        self.pending_requests.append(payload)

    async def queue_async(self, payload: Dict[str, Any]) -> None:
        """Non-blocking async push — drains into pending_requests on next tick."""
        await self._async_queue.put(payload)

    def _drain_async_queue(self) -> None:
        """Move items from asyncio.Queue into pending_requests (non-blocking)."""
        while not self._async_queue.empty():
            try:
                self.pending_requests.append(self._async_queue.get_nowait())
                self._async_queue.task_done()
            except asyncio.QueueEmpty:
                break

    def _normalize_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Map domain swarm envelope to JSON-RPC tools/call for dispatch."""
        if not isinstance(req, dict):
            return req
        if "jsonrpc" in req:
            return req
        rtype = req.get("request_type")
        if not rtype:
            return req
        tool = self.DOMAIN_TOOL_MAP.get(str(rtype))
        if tool is None:
            # Leave domain shape; validator will reject unknown types.
            return req
        args = {
            k: v
            for k, v in req.items()
            if k
            not in {
                "request_type",
                "request_id",
                "id",
                "timestamp",
                "source_agent",
                "severity",
                "jsonrpc",
                "method",
                "params",
            }
        }
        return {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": req.get("id") or req.get("request_id") or "unknown",
            "params": {"name": tool, "arguments": args},
            # Preserve originals for audit correlation
            "_domain_request_type": rtype,
            "_domain_request_id": req.get("request_id") or req.get("id"),
        }

    # ------------------------------------------------------------------
    # Tick entry-point — called by APEXThermalOrchestrator.tick_cycle()
    # ------------------------------------------------------------------

    async def process_tick(self, orchestrator) -> List[Dict[str, Any]]:
        """Process all queued MCP requests in one tick. Alias: dispatch()."""
        self._drain_async_queue()

        if not self.pending_requests:
            return []

        active_batch = list(self.pending_requests)
        self.pending_requests.clear()
        results = []

        for raw in active_batch:
            start_time = time.perf_counter()
            # Validate original shape (domain or JSON-RPC); normalize only for dispatch.
            is_valid, msg = self.validator.validate(raw)
            audit_id = raw.get("request_id") or raw.get("id") or "unknown"
            method = raw.get("request_type") or raw.get("method") or "unknown"

            if not is_valid:
                response = {
                    "jsonrpc": "2.0",
                    "id": audit_id,
                    "error": {"code": -32600, "message": f"Invalid Request: {msg}"},
                }
                status = "REJECTED"
            else:
                req = self._normalize_request(raw)
                response = await self._dispatch_tool(req, orchestrator)
                status = "EXECUTED"

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            audit_event = {
                "event": "MCP_DISPATCH",
                "request_id": audit_id,
                "method": method,
                "status": status,
                "duration_ms": round(duration_ms, 3),
                "error_message": msg if not is_valid else None,
            }
            self.logger.log_event(audit_event)
            results.append(response)

        return results

    # dispatch() is the canonical name referenced in issue #16 AC
    dispatch = process_tick

    # ------------------------------------------------------------------
    # Tool dispatcher
    # ------------------------------------------------------------------

    async def _dispatch_tool(self, req: Dict[str, Any], orchestrator) -> Dict[str, Any]:
        """Translate validated MCP tool-call into live orchestrator commands."""
        method = req.get("method")
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        result_payload: Dict[str, Any] = {"status": "SUCCESS", "details": ""}

        if method != "tools/call":
            result_payload["status"] = "ERROR"
            result_payload["details"] = (
                f"Method '{method}' not supported by thermal dispatcher."
            )
            return self._wrap(req, result_payload)

        if tool_name not in self.SUPPORTED_TOOLS:
            result_payload["status"] = "ERROR"
            result_payload["details"] = (
                f"Tool '{tool_name}' not implemented. Supported: {sorted(self.SUPPORTED_TOOLS)}"
            )
            return self._wrap(req, result_payload)

        # ---- emergency_blast ------------------------------------------
        if tool_name == "emergency_blast":
            threshold_c = float(args.get("threshold_c", 70.0))
            target_nodes = [
                n for n in orchestrator.all_nodes if n.temp_celsius > threshold_c
            ]
            if target_nodes:
                sn_result = await orchestrator.pistons["SUPERNOVA"].activate(
                    {
                        "critical_nodes": target_nodes,
                        "trigger": "MCP_EMERGENCY_BLAST",
                    }
                )
                result_payload["details"] = (
                    f"SUPERNOVA triggered for {len(target_nodes)} nodes above {threshold_c}°C."
                )
                result_payload["nodes_affected"] = len(target_nodes)
            else:
                result_payload["details"] = (
                    f"No nodes above {threshold_c}°C — no blast required."
                )
                result_payload["nodes_affected"] = 0

        # ---- predictive_sweep -----------------------------------------
        elif tool_name == "predictive_sweep":
            mw_result = await orchestrator.pistons["MICROWAVE"].activate(
                {
                    "zones": orchestrator.zones,
                    "trigger": "MCP_PREDICTIVE_SWEEP",
                }
            )
            result_payload["details"] = (
                f"MICROWAVE sweep across {len(orchestrator.zones)} zones."
            )
            result_payload["zones_swept"] = mw_result.get("zones_swept", 0)

        # ---- zone_budget_override  ------------------------------------
        elif tool_name == "zone_budget_override":
            zone_id = args.get("zone_id")
            budget_kw = args.get("budget_kw")
            if zone_id is None or budget_kw is None:
                result_payload["status"] = "ERROR"
                result_payload["details"] = (
                    "zone_id and budget_kw are required arguments."
                )
            else:
                budget_kw = float(budget_kw)
                matched = [z for z in orchestrator.zones if z.zone_id == zone_id]
                if not matched:
                    result_payload["status"] = "ERROR"
                    result_payload["details"] = (
                        f"Zone '{zone_id}' not registered in orchestrator."
                    )
                else:
                    for zone in matched:
                        prev = zone.thermal_budget_kw
                        zone.thermal_budget_kw = budget_kw
                        self.logger.log_event(
                            {
                                "event": "ZONE_BUDGET_OVERRIDE",
                                "zone_id": zone_id,
                                "prev_kw": prev,
                                "new_kw": budget_kw,
                            }
                        )
                    result_payload["details"] = (
                        f"Zone {zone_id} thermal budget set to {budget_kw} kW (was {prev:.1f} kW)."
                    )
                    result_payload["zone_id"] = zone_id
                    result_payload["budget_kw"] = budget_kw

        # ---- fusion_dispatch  -----------------------------------------
        elif tool_name == "fusion_dispatch":
            fusion_name = args.get("fusion_name")
            if not fusion_name:
                result_payload["status"] = "ERROR"
                result_payload["details"] = "fusion_name argument is required."
            else:
                fusion_result = await orchestrator.run_fusion_mode(
                    fusion_name, context=args.get("context", {})
                )
                if fusion_result.get("status") == "UNKNOWN":
                    result_payload["status"] = "ERROR"
                    result_payload["details"] = (
                        f"Fusion mode '{fusion_name}' not defined in manifest."
                    )
                else:
                    result_payload["details"] = (
                        f"Fusion mode '{fusion_name}' dispatched: {fusion_result.get('status')}."
                    )
                    result_payload["fusion_result"] = fusion_result

        # ---- thermal_status  ------------------------------------------
        elif tool_name == "thermal_status":
            zone_filter = args.get("zone_id")
            zones_data = []
            for zone in orchestrator.zones:
                if zone_filter and zone.zone_id != zone_filter:
                    continue
                zones_data.append(
                    {
                        "zone_id": zone.zone_id,
                        "zone_name": zone.zone_name,
                        "avg_temp_c": round(zone.avg_temp, 2),
                        "peak_temp_c": round(zone.peak_temp, 2),
                        "active_mode": zone.active_mode.value,
                        "crac_units_active": zone.crac_units_active,
                        "liquid_flow_lpm": round(zone.liquid_cooling_flow_lpm, 2),
                        "thermal_budget_kw": round(zone.thermal_budget_kw, 2),
                        "conductivity_factor": round(zone.conductivity_factor, 4),
                        "node_count": len(zone.nodes),
                        "nodes_in_alert": sum(
                            1 for n in zone.nodes if n.alert_level > 0
                        ),
                    }
                )
            result_payload["details"] = (
                f"Thermal status snapshot — {len(zones_data)} zone(s)."
            )
            result_payload["zones"] = zones_data
            result_payload["total_nodes"] = len(orchestrator.all_nodes)
            result_payload["tick"] = orchestrator.tick

        return self._wrap(req, result_payload)

    @staticmethod
    def _wrap(req: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
