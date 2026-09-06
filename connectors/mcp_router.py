# Re-export — canonical implementation in src/
# Keeps apex_core/thermal_orchestrator.py import path valid
import importlib.util
import os

_src_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "src",
    "connectors",
    "mcp_router.py",
)
_spec = importlib.util.spec_from_file_location("_real_mcp_router", _src_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MCPRouterConnector = _mod.MCPRouterConnector

__all__ = ["MCPRouterConnector"]
