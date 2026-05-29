"""
mastermind-fusion/mcp_router.py
xai-colossus-cooling | APEX Swarm Operations

MCP-to-All Router — canonical dispatch layer for agent swarm calls.

Contract (from APEX_SYSTEM_MATRIX.md + closed Issue #11):
  - All agent swarm requests flow through this router.
  - Router validates schema, routes to handler, ranks responses, logs to Aspen Grove.
  - Emergency broadcasts bypass ranking and fan out immediately.
  - Mentat AI may auto-handle P1_SWARM and P2 requests; P0_GATE always human-owned.

Supported request types:
  request_forecast       -> ThermalForecastHandler
  request_zone_snapshot  -> ZoneSnapshotHandler
  request_piston_status  -> PistonStatusHandler
  emergency_broadcast    -> EmergencyBroadcastHandler (fan-out, no ranking)
"""

from __future__ import annotations
import asyncio
import datetime
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger('MCP-ROUTER')

ASPEN_LOG_PATH = Path('audit_logs/aspen_mcp_events.ndjson')


# ---------------------------------------------------------------------------
# Schema: canonical request/response envelope (Issue #11 contract)
# ---------------------------------------------------------------------------

class RequestType(str, Enum):
    FORECAST        = 'request_forecast'
    ZONE_SNAPSHOT   = 'request_zone_snapshot'
    PISTON_STATUS   = 'request_piston_status'
    EMERGENCY       = 'emergency_broadcast'


class ResponseStatus(str, Enum):
    OK       = 'ok'
    PARTIAL  = 'partial'
    ERROR    = 'error'
    EMITTED  = 'emitted'   # emergency: fan-out complete


@dataclass
class MCPRequest:
    """
    Canonical MCP-to-All request envelope.
    All swarm calls must conform to this schema before routing.
    """
    request_type: RequestType
    zone_id: Optional[str] = None           # None = cluster-wide
    piston_name: Optional[str] = None       # for PISTON_STATUS requests
    horizon_ticks: int = 12                  # for FORECAST requests
    severity: str = 'INFO'                  # for EMERGENCY: INFO|WARN|CRITICAL
    message: Optional[str] = None           # for EMERGENCY
    payload: dict = field(default_factory=dict)
    # Auto-populated by router
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    source_agent: str = 'unknown'


@dataclass
class MCPResponse:
    """
    Canonical MCP-to-All response envelope.
    """
    request_id: str
    request_type: str
    status: ResponseStatus
    data: dict = field(default_factory=dict)
    agent_scores: list = field(default_factory=list)  # ranked agent responses
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    routed_by: str = 'mcp_router'


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

class ThermalForecastHandler:
    """Queries CORE-THINK piston via orchestrator and returns forecast."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    async def handle(self, req: MCPRequest) -> dict:
        if not self.orchestrator:
            return {'status': 'offline', 'reason': 'orchestrator not connected'}
        aspen = getattr(self.orchestrator, '_aspen', None)
        ct_result = await self.orchestrator.pistons['CORE-THINK'].activate({
            'aspen_connector': aspen,
            'trigger': 'MCP_FORECAST_REQUEST',
            'zone_id': req.zone_id,
            'horizon_ticks': req.horizon_ticks,
        })
        return ct_result


class ZoneSnapshotHandler:
    """Returns current thermal + fluid + budget state for a zone or all zones."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    async def handle(self, req: MCPRequest) -> dict:
        if not self.orchestrator:
            return {'status': 'offline'}
        zones = self.orchestrator.zones
        if req.zone_id:
            zones = [z for z in zones if z.zone_id == req.zone_id]
        snapshots = []
        for z in zones:
            snapshots.append({
                'zone_id': z.zone_id,
                'avg_temp_c': round(z.avg_temp, 2),
                'peak_temp_c': round(z.peak_temp, 2),
                'crac_units_active': z.crac_units_active,
                'liquid_flow_lpm': round(z.liquid_cooling_flow_lpm, 2),
                'conductivity_factor': round(z.conductivity_factor, 4),
                'thermal_budget_kw': round(z.thermal_budget_kw, 2),
                'active_mode': z.active_mode.value,
                'node_count': len(z.nodes),
                'alert_counts': {
                    '3_critical': sum(1 for n in z.nodes if n.alert_level == 3),
                    '2_hot':      sum(1 for n in z.nodes if n.alert_level == 2),
                    '1_warm':     sum(1 for n in z.nodes if n.alert_level == 1),
                    '0_ok':       sum(1 for n in z.nodes if n.alert_level == 0),
                },
            })
        return {'zones': snapshots, 'count': len(snapshots)}


class PistonStatusHandler:
    """Returns active/inactive + last-known result for one or all pistons."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    async def handle(self, req: MCPRequest) -> dict:
        if not self.orchestrator:
            return {'status': 'offline'}
        pistons = self.orchestrator.pistons
        if req.piston_name:
            p = pistons.get(req.piston_name.upper())
            if not p:
                return {'status': 'error', 'reason': f'Unknown piston: {req.piston_name}'}
            return {'piston': p.name, 'tier': p.tier, 'active': p.active}
        return {
            'pistons': [
                {'piston': p.name, 'tier': p.tier, 'active': p.active}
                for p in pistons.values()
            ]
        }


class EmergencyBroadcastHandler:
    """
    Fan-out emergency broadcast. Bypasses ranking.
    Logs to Aspen Grove audit trail synchronously before returning.
    """

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
        self._write_aspen_log(event)
        logger.warning('EMERGENCY BROADCAST [%s]: %s | zone=%s', req.severity, req.message, req.zone_id)
        return {'fanned_out': True, 'severity': req.severity}

    @staticmethod
    def _write_aspen_log(event: dict):
        ASPEN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ASPEN_LOG_PATH, 'a') as f:
            f.write(json.dumps(event) + '\n')


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class MCPRouter:
    """
    Central MCP-to-All router.
    Validates, dispatches, ranks (non-emergency), and logs all swarm calls.
    """

    def __init__(self, orchestrator=None):
        self._orchestrator = orchestrator
        self._handlers = {
            RequestType.FORECAST:       ThermalForecastHandler(orchestrator),
            RequestType.ZONE_SNAPSHOT:  ZoneSnapshotHandler(orchestrator),
            RequestType.PISTON_STATUS:  PistonStatusHandler(orchestrator),
            RequestType.EMERGENCY:      EmergencyBroadcastHandler(),
        }

    def attach_orchestrator(self, orchestrator):
        """Late-bind orchestrator (useful when router is initialized before orchestrator)."""
        self._orchestrator = orchestrator
        for handler in self._handlers.values():
            if hasattr(handler, 'orchestrator'):
                handler.orchestrator = orchestrator

    async def dispatch(self, req: MCPRequest) -> MCPResponse:
        """Validate, route, rank, log. Returns canonical MCPResponse."""
        logger.info('MCP dispatch [%s] req_id=%s source=%s', req.request_type, req.request_id, req.source_agent)

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
            logger.error('Handler error for %s: %s', req.request_type, e)
            data = {'error': str(e)}
            status = ResponseStatus.ERROR

        resp = MCPResponse(
            request_id=req.request_id,
            request_type=req.request_type,
            status=status,
            data=data,
        )

        self._log_event(req, resp)
        return resp

    @staticmethod
    def _log_event(req: MCPRequest, resp: MCPResponse):
        """Append every routed call to the Aspen Grove audit trail."""
        record = {
            'timestamp': resp.timestamp,
            'request_id': req.request_id,
            'request_type': req.request_type,
            'source_agent': req.source_agent,
            'zone_id': req.zone_id,
            'status': resp.status,
        }
        ASPEN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ASPEN_LOG_PATH, 'a') as f:
            f.write(json.dumps(record) + '\n')


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def build_router(orchestrator=None) -> MCPRouter:
    """Build and return a ready MCPRouter bound to the given orchestrator."""
    return MCPRouter(orchestrator=orchestrator)
