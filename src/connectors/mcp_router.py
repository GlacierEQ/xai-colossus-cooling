import asyncio
import json
import os
import time
from typing import Dict, Any, List

from schemas.mcp_request_validator import MCPRequestValidator
from memory.aspen_grove_logger import AspenGroveLogger

class MCPRouterConnector:
    """
    APEX Model Context Protocol (MCP) Router
    Bridges Vercel, Supabase, and Notion MCP integrations into the 100ms APEX tick loop.
    Validates requests using schemas and dispatches execution targets.
    """
    def __init__(self, logger: AspenGroveLogger = None):
        self.validator = MCPRequestValidator()
        self.logger = logger or AspenGroveLogger()
        self.pending_requests: List[Dict[str, Any]] = []
        self.dispatch_log_path = os.path.expandvars("$HOME/logs/mcp_dispatch_audit.log")
        os.makedirs(os.path.dirname(self.dispatch_log_path), exist_ok=True)

    def queue_request(self, payload: Dict[str, Any]):
        """Inject a request into the router queue (mocking network push / webhook)."""
        self.pending_requests.append(payload)

    async def process_tick(self, orchestrator) -> List[Dict[str, Any]]:
        """
        Executed on every APEX tick cycle.
        Processes, validates, and dispatches all queued MCP requests.
        """
        if not self.pending_requests:
            return []

        active_batch = list(self.pending_requests)
        self.pending_requests.clear()
        results = []

        for req in active_batch:
            start_time = time.perf_counter()
            is_valid, msg = self.validator.validate(req)
            
            req_id = req.get("id", "unknown")
            method = req.get("method", "unknown")
            
            if not is_valid:
                # 1. Reject invalid requests with structured schemas
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32600,
                        "message": f"Invalid Request: {msg}"
                    }
                }
                status = "REJECTED"
            else:
                # 2. Dispatch valid tool calls directly to APEX Orchestrator
                response = await self._dispatch_tool(req, orchestrator)
                status = "EXECUTED"
            
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            
            # 3. Log audit event asynchronously to Aspen Grove logger
            audit_event = {
                "event": "MCP_DISPATCH",
                "request_id": req_id,
                "method": method,
                "status": status,
                "duration_ms": round(duration_ms, 3),
                "error_message": msg if not is_valid else None
            }
            self.logger.log_event(audit_event)
            results.append(response)

        return results

    async def _dispatch_tool(self, req: Dict[str, Any], orchestrator) -> Dict[str, Any]:
        """Translate valid MCP requests into active orchestrator thermal commands."""
        method = req.get("method")
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        result_payload = {"status": "SUCCESS", "details": ""}
        
        # Method mapping: maps tools directly to APEX Orchestrator cooling actions
        if method == "tools/call":
            if tool_name == "emergency_blast":
                # Force-trigger SUPERNOVA emergency cooling
                target_nodes = [n for n in orchestrator.all_nodes if n.temp_celsius > 70.0]
                if target_nodes:
                    sn_result = await orchestrator.pistons["SUPERNOVA"].activate({
                        "critical_nodes": target_nodes,
                        "trigger": "MCP_EMERGENCY_BLAST"
                    })
                    result_payload["details"] = f"SUPERNOVA emergency blast triggered for {len(target_nodes)} warm nodes."
                else:
                    result_payload["details"] = "No hot/warm nodes requiring blast cooling."
            
            elif tool_name == "predictive_sweep":
                # Trigger a MICROWAVE thermal sweep cycle
                mw_result = await orchestrator.pistons["MICROWAVE"].activate({
                    "zones": orchestrator.zones,
                    "trigger": "MCP_PREDICTIVE_SWEEP"
                })
                result_payload["details"] = f"MICROWAVE predictive sweep executed across {len(orchestrator.zones)} zones."
                
            else:
                result_payload["status"] = "ERROR"
                result_payload["details"] = f"Tool '{tool_name}' not implemented in APEX cooling core."
        else:
            result_payload["status"] = "ERROR"
            result_payload["details"] = f"Method '{method}' not supported by thermal dispatcher."

        return {
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "result": result_payload
        }
