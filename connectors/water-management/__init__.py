"""
Water Management System — xAI Colossus Phase 2
Triple-redundancy: Municipal main + Emergency cistern + RO plant + AWG
AI Grok pre-cooling integration for predictive thermal load management.
"""

from .controller import WaterManagementController
from .cistern_monitor import CisternMonitor
from .ro_plant import ROPlantController
from .grok_precooling import GrokPreCoolingEngine

__version__ = "0.1.0"
__all__ = [
    "WaterManagementController",
    "CisternMonitor",
    "ROPlantController",
    "GrokPreCoolingEngine",
]
