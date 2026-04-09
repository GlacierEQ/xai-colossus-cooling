#!/usr/bin/env python3
"""
Rack Cell — Individual Rack Unit (Bio-Inspired)
GlacierEQ APEX Architecture

Each physical rack in the Colossus cluster is modeled as a biological cell:
  - Nucleus = Management controller
  - Mitochondria = Power/thermal agents
  - Cell membrane = Physical rack boundary
  - Receptors = Sensors (temp, power, airflow)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, UTC


@dataclass
class RackSensor:
    sensor_id: str
    sensor_type: str  # 'inlet_temp', 'exhaust_temp', 'airflow_cfm', 'power_kw'
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class RackCell:
    """
    Biological cell abstraction for a single server rack.
    Racks are the fundamental unit of thermal management.
    """
    rack_id: str
    zone_id: str
    row: int
    position: int
    
    # Thermal state
    inlet_temp_c: float = 22.0
    exhaust_temp_c: float = 35.0
    delta_t: float = 0.0
    
    # Power state  
    power_draw_kw: float = 0.0
    power_cap_kw: float = 80.0
    utilization_pct: float = 0.0
    
    # Cooling state
    cooling_mode: str = 'STEADY_STATE'
    crac_assignment: Optional[str] = None
    liquid_cooling: bool = False
    liquid_flow_lpm: float = 0.0
    
    # Sensors
    sensors: List[RackSensor] = field(default_factory=list)
    
    # Metadata
    gpu_count: int = 8
    gpu_model: str = 'H100'
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def __post_init__(self):
        self.delta_t = self.exhaust_temp_c - self.inlet_temp_c
        self.utilization_pct = (self.power_draw_kw / self.power_cap_kw) * 100 if self.power_cap_kw > 0 else 0
    
    def update_thermals(self, inlet: float, exhaust: float, power_kw: float):
        self.inlet_temp_c = inlet
        self.exhaust_temp_c = exhaust
        self.delta_t = exhaust - inlet
        self.power_draw_kw = power_kw
        self.utilization_pct = (power_kw / self.power_cap_kw) * 100
    
    def needs_cooling_intervention(self) -> bool:
        return self.exhaust_temp_c > 40 or self.inlet_temp_c > 27 or self.power_draw_kw > self.power_cap_kw * 0.9
    
    def to_dict(self) -> Dict:
        return {
            'rack_id': self.rack_id,
            'zone_id': self.zone_id,
            'inlet_temp_c': self.inlet_temp_c,
            'exhaust_temp_c': self.exhaust_temp_c,
            'delta_t': self.delta_t,
            'power_draw_kw': self.power_draw_kw,
            'utilization_pct': round(self.utilization_pct, 1),
            'cooling_mode': self.cooling_mode,
            'liquid_cooling': self.liquid_cooling,
            'needs_intervention': self.needs_cooling_intervention()
        }
