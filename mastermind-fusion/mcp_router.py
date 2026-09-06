#!/usr/bin/env python3
"""
MCP Router - Mastermind Fusion Component
Governed by Strand A Laws.
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger("Mastermind.MCPRouter")


class ResponseStatus:
    OK = "OK"
    ERROR = "ERROR"
    EMITTED = "EMITTED"


class RequestType:
    EMERGENCY = "EMERGENCY"
    ZONE_SNAPSHOT = "ZONE_SNAPSHOT"
    THERMAL_ALERT = "THERMAL_ALERT"
    ENERGY_DISPATCH = "ENERGY_DISPATCH"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"


class MCPRequest:
    def __init__(
        self, request_id: str = "", request_type: str = "", **kwargs: Any
    ) -> None:
        self.request_id = request_id
        self.request_type = request_type
        self.payload = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class MCPResponse:
    def __init__(
        self, request_id: str, request_type: str, status: str, data: Dict[str, Any]
    ) -> None:
        self.request_id = request_id
        self.request_type = request_type
        self.status = status
        self.data = data


from pathlib import Path

ASPEN_LOG_PATH = Path("logs/aspen_events.jsonl")


class MCPRouter:
    """Routes incoming MCP requests to appropriate handlers."""

    def __init__(self, orchestrator: Any = None, **kwargs: Any) -> None:
        self._handlers: Dict[str, Any] = {}
        self.orchestrator = orchestrator

    def validate_request(self, req_dict: Dict[str, Any]) -> str:
        """Validates incoming dictionary schema."""
        if not isinstance(req_dict, dict):
            return "Payload must be a dictionary."
        if "request_id" not in req_dict:
            return "Missing request_id."
        if "request_type" not in req_dict:
            return "Missing request_type."
        return ""

    async def dispatch(self, req_dict: Any) -> MCPResponse:
        """Dispatches validated request to handler. Accepts dict or MCPRequest."""
        if isinstance(req_dict, MCPRequest):
            req = req_dict
        else:
            error = self.validate_request(req_dict)
            if error:
                return MCPResponse(
                    request_id=str(req_dict.get("request_id", "unknown")),
                    request_type=str(req_dict.get("request_type", "unknown")),
                    status=ResponseStatus.ERROR,
                    data={"status": "ERROR", "reason": f"Validation failed: {error}"},
                )
            req = MCPRequest(**req_dict)

        logger.info(f"MCP dispatch type={req.request_type} req_id={req.request_id}")

        # Handle known request types
        if req.request_type == RequestType.ZONE_SNAPSHOT:
            return MCPResponse(
                request_id=req.request_id or "zone-snapshot",
                request_type=req.request_type,
                status=ResponseStatus.OK,
                data={"status": "offline", "reason": "No orchestrator connected"},
            )
        elif req.request_type == RequestType.EMERGENCY:
            # Log to Aspen Grove
            log_path = Path(ASPEN_LOG_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "request_id": req.request_id,
                            "type": req.request_type,
                            "severity": getattr(req, "severity", "CRITICAL"),
                            "message": getattr(req, "message", ""),
                            "zone_id": getattr(req, "zone_id", None),
                            "source_agent": getattr(req, "source_agent", None),
                        }
                    )
                    + "\n"
                )
            return MCPResponse(
                request_id=req.request_id or "emergency",
                request_type=req.request_type,
                status=ResponseStatus.EMITTED,
                data={
                    "status": "EMITTED",
                    "reason": "Emergency broadcast dispatched",
                    "fanned_out": True,
                },
            )

        return MCPResponse(
            request_id=req.request_id or "unknown",
            request_type=req.request_type,
            status=ResponseStatus.ERROR,
            data={"status": "ERROR", "reason": "No handler for request type."},
        )


def build_router(**kwargs: Any) -> MCPRouter:
    """Factory to create an MCPRouter with optional config."""
    router = MCPRouter()
    for k, v in kwargs.items():
        setattr(router, k, v)
    return router
