import logging
from datetime import datetime, UTC
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('APEX-MODELS')

class CoolingMode(Enum):
    STEADY_STATE   = "SHADOW"          # Silent 24/7 monitoring
    PREDICTIVE     = "MICROWAVE"       # Pre-emptive thermal management
    EMERGENCY      = "SUPERNOVA"       # Maximum force response
    GHOST_OPS      = "GHOST_MICROWAVE" # Invisible optimization
    COLOSSUS       = "COLOSSUS"        # Full 100k node scale


@dataclass
class ThermalNode:
    node_id: str
    rack_id: str
    zone_id: str
    temp_celsius: float
    gpu_utilization: float
    power_watts: float
    cooling_active: bool = False
    alert_level: int = 0  # 0=normal, 1=warm, 2=hot, 3=critical
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def classify_alert(self):
        if self.temp_celsius >= 85:
            self.alert_level = 3
        elif self.temp_celsius >= 78:
            self.alert_level = 2
        elif self.temp_celsius >= 70:
            self.alert_level = 1
        else:
            self.alert_level = 0
        return self.alert_level


@dataclass
class CoolingZone:
    zone_id: str
    zone_name: str
    nodes: List[ThermalNode] = field(default_factory=list)
    active_mode: CoolingMode = CoolingMode.STEADY_STATE
    avg_temp: float = 0.0
    peak_temp: float = 0.0
    crac_units_active: int = 0
    liquid_cooling_flow_lpm: float = 0.0

    def compute_thermals(self):
        """Re-calculate zone average and peak temperatures from current node telemetry."""
        if not self.nodes:
            self.avg_temp = 0.0
            self.peak_temp = 0.0
            return

        valid_temps = [n.temp_celsius for n in self.nodes if -50 <= n.temp_celsius <= 150]

        if not valid_temps:
            logger.warning(f"Zone {self.zone_id} has {len(self.nodes)} nodes but no valid temperature readings.")
            self.avg_temp = 0.0
            self.peak_temp = 0.0
            return

        self.avg_temp = sum(valid_temps) / len(valid_temps)
        self.peak_temp = max(valid_temps)

        for node in self.nodes:
            node.classify_alert()
