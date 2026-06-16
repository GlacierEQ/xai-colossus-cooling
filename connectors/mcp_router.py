# Re-export shim — keeps apex_core/thermal_orchestrator.py import path valid
# while canonical implementation lives in src/connectors/mcp_router.py
from src.connectors.mcp_router import MCPRouterConnector  # noqa: F401

__all__ = ["MCPRouterConnector"]
