"""
Power Systems — xAI Colossus Phase 6
Dual 500MW substations + 8 on-site gas turbines + UPS + transfer switching.
Total capacity: 1.4 GW continuous / 1.6 GW peak.
"""
from .substation import SubstationController
from .turbine_array import GasTurbineArrayController
from .ups_manager import UPSManager
from .transfer_switch import AutomaticTransferSwitch
from .power_orchestrator import PowerOrchestrator

__version__ = "0.1.0"
__all__ = ["SubstationController", "GasTurbineArrayController",
           "UPSManager", "AutomaticTransferSwitch", "PowerOrchestrator"]
