import logging
from datetime import datetime, UTC
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('APEX-MODELS')

class CoolingMode(Enum):
    STEADY_STATE   = "SHADOW"
    PREDICTIVE     = "MICROWAVE"
    EMERGENCY      = "SUPERNOVA"
    GHOST_OPS      = "GHOST_MICROWAVE"
    COLOSSUS       = "COLOSSUS"


@dataclass
class RackSensor:
    """Modeled after biological receptors."""
    sensor_id: str
    sensor_type: str  # 'inlet_temp', 'exhaust_temp', 'airflow_cfm', 'power_kw'
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ThermalNode:
    """Individual GPU/Compute unit within a cell."""
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
class RackCell:
    """Biological cell abstraction for a single server rack."""
    rack_id: str
    zone_id: str
    nodes: List[ThermalNode] = field(default_factory=list)
    sensors: List[RackSensor] = field(default_factory=list)

    # Thermal state
    inlet_temp_c: float = 22.0
    exhaust_temp_c: float = 35.0

    # Power state
    power_draw_kw: float = 0.0
    power_cap_kw: float = 80.0
    utilization_pct: float = 0.0

    def __post_init__(self):
        if self.power_cap_kw > 0:
            self.utilization_pct = (self.power_draw_kw / self.power_cap_kw) * 100

    def sync_nodes(self):
        """Sync aggregate data from internal nodes to cell-level telemetry."""
        if not self.nodes:
            return
        self.exhaust_temp_c = max(n.temp_celsius for n in self.nodes)
        self.power_draw_kw = sum(n.power_watts for n in self.nodes) / 1000.0
        if self.power_cap_kw > 0:
            self.utilization_pct = (self.power_draw_kw / self.power_cap_kw) * 100


@dataclass
class CoolingZone:
    """Biological tissue abstraction for a group of cells."""
    zone_id: str
    zone_name: str
    cells: List[RackCell] = field(default_factory=list)
    active_mode: CoolingMode = CoolingMode.STEADY_STATE
    avg_temp: float = 0.0
    peak_temp: float = 0.0
    crac_units_active: int = 0
    liquid_cooling_flow_lpm: float = 0.0

    @property
    def all_nodes(self) -> List[ThermalNode]:
        nodes = []
        for cell in self.cells:
            nodes.extend(cell.nodes)
        return nodes

    def compute_thermals(self):
        """Re-calculate zone average and peak temperatures from current cell/node telemetry."""
        nodes = self.all_nodes
        if not nodes:
            self.avg_temp = 0.0
            self.peak_temp = 0.0
            return

        valid_temps = [n.temp_celsius for n in nodes if -50 <= n.temp_celsius <= 150]

        if not valid_temps:
            logger.warning(f"Zone {self.zone_id} has {len(nodes)} nodes but no valid temperature readings.")
            self.avg_temp = 0.0
            self.peak_temp = 0.0
            return

        self.avg_temp = sum(valid_temps) / len(valid_temps)
        self.peak_temp = max(valid_temps)

        for node in nodes:
            node.classify_alert()

        # Sync cells
        for cell in self.cells:
            cell.sync_nodes()
