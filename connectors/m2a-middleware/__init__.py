"""
M2A Middleware — MCP-to-All Selective Broadcast Fabric
xAI Colossus Cooling System | GlacierEQ APEX Architecture
"""
from .registry import NodeRegistry
from .router import RelevanceRouter
from .suppression import SuppressionEngine
from .aggregator import BundleAggregator
from .middleware import M2AMiddleware

__version__ = "0.1.0"
__all__ = ["NodeRegistry", "RelevanceRouter", "SuppressionEngine", "BundleAggregator", "M2AMiddleware"]
