"""
mastermind-fusion/__init__.py
xai-colossus-cooling | APEX Swarm Operations Layer

Public surface of the mastermind-fusion package.
All MCP swarm calls enter through MCPRouter.
No thermal logic lives here — that is apex_core's domain.

Quick start:
    from mastermind_fusion.mcp_router import build_router, MCPRequest, RequestType
    router = build_router(orchestrator=my_orchestrator)
    resp = await router.dispatch(MCPRequest(
        request_type=RequestType.ZONE_SNAPSHOT,
        source_agent='my-agent',
    ))
"""

from mastermind_fusion.mcp_router import (
    MCPRouter,
    MCPRequest,
    MCPResponse,
    RequestType,
    ResponseStatus,
    build_router,
)

__all__ = [
    "MCPRouter",
    "MCPRequest",
    "MCPResponse",
    "RequestType",
    "ResponseStatus",
    "build_router",
]

__version__ = "1.0.0"
