from __future__ import annotations
import asyncio
import datetime
import json
import logging
import uuid
import jsonschema # Assuming jsonschema is available
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any

# APEX Integration
from apex_core.aspen_logger import get_default_logger

logger = logging.getLogger('MCP-ROUTER')
aspen_logger = get_default_logger()

# MCP Request Schema (Placeholder for Issue #17)
MCP_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "request_type": {"type": "string"},
        "zone_id": {"type": "string"},
        "piston_name": {"type": "string"},
    },
    "required": ["request_type"]
}

class RequestType(str, Enum):
    FORECAST       = 'request_forecast'
    ZONE_SNAPSHOT  = 'request_zone_snapshot'
    PISTON_STATUS  = 'request_piston_status'
    EMERGENCY      = 'emergency_broadcast'

class ResponseStatus(str, Enum):
    OK      = 'ok'
    PARTIAL = 'partial'
    ERROR   = 'error'
    EMITTED = 'emitted'

@dataclass
class MCPRequest:
    request_type: RequestType
    zone_id: Optional[str] = None
    piston_name: Optional[str] = None
    horizon_ticks: int = 12
    severity: str = 'INFO'
    message: Optional[str] = None
    payload: dict = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    source_agent: str = 'unknown'

@dataclass
class MCPResponse:
    request_id: str
    request_type: str
    status: ResponseStatus
    data: dict = field(default_factory=dict)
    agent_scores: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    routed_by: str = 'mcp_router'

# Handlers ... (Handlers remain mostly same, EmergencyBroadcastHandler _write_aspen_log updated)

class EmergencyBroadcastHandler:
    async def handle(self, req: MCPRequest) -> dict:
        event = {
            'event': 'EMERGENCY_BROADCAST',
            'severity': req.severity,
            'message': req.message,
            'zone_id': req.zone_id,
            'payload': req.payload,
            'timestamp': req.timestamp,
            'request_id': req.request_id,
        }
        await aspen_logger.log_event(event) # Async write
        logger.warning('EMERGENCY BROADCAST [%s]: %s | zone=%s', req.severity, req.message, req.zone_id)
        return {'fanned_out': True, 'severity': req.severity}

class MCPRouter:
    def __init__(self, orchestrator=None):
        self._orchestrator = orchestrator
        self._handlers = {
            RequestType.FORECAST:      ThermalForecastHandler(orchestrator),
            RequestType.ZONE_SNAPSHOT: ZoneSnapshotHandler(orchestrator),
            RequestType.PISTON_STATUS: PistonStatusHandler(orchestrator),
            RequestType.EMERGENCY:     EmergencyBroadcastHandler(),
        }

    def validate_request(self, req: Dict[str, Any]) -> Optional[str]:
        try:
            # Need to map MCPRequest object back to dict for validation
            jsonschema.validate(instance=req, schema=MCP_REQUEST_SCHEMA)
            return None
        except jsonschema.ValidationError as e:
            return str(e)

    async def dispatch(self, req_dict: Dict[str, Any]) -> MCPResponse:
        # 1. Schema Validation (Issue #17)
        error = self.validate_request(req_dict)
        if error:
            return MCPResponse(
                request_id=req_dict.get('request_id', 'unknown'),
                request_type=req_dict.get('request_type', 'unknown'),
                status=ResponseStatus.ERROR,
                data={'status': 'ERROR', 'reason': f'Validation failed: {error}'}
            )
            
        req = MCPRequest(**req_dict)
        logger.info('MCP dispatch [%s] req_id=%s', req.request_type, req.request_id)
        handler = self._handlers.get(req.request_type)
        if not handler:
            return MCPResponse(
                request_id=req.request_id,
                request_type=req.request_type,
                status=ResponseStatus.ERROR,
                data={'reason': f'No handler for {req.request_type}'},
            )
        try:
            data = await handler.handle(req)
            status = ResponseStatus.EMITTED if req.request_type == RequestType.EMERGENCY else ResponseStatus.OK
        except Exception as e:
            data = {'error': str(e)}
            status = ResponseStatus.ERROR
        resp = MCPResponse(
            request_id=req.request_id,
            request_type=req.request_type,
            status=status,
            data=data,
        )
        # 2. Async Logging (Issue #18)
        await aspen_logger.log_event(resp.__dict__)
        return resp
