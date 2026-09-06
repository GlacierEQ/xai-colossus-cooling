"""
SensorMap — full rack-to-zone-to-CDU topology
14 zones x 142 sensors = 1,988 total hardware sensors.
Sensor breakdown per zone:
  thermal 48 | flow 24 | pressure 24 | humidity 18 | power 16 | vibration 12
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SensorEntry:
    sensor_id: str
    zone_id: str
    rack_id: str
    cdu_id: str
    sensor_type: str
    location: str
    gpu_id: Optional[str] = None
    calibration_offset: float = 0.0
    accuracy_pct: float = 0.1
    sample_rate_hz: int = 4
    hardware_model: str = "PT100-DIN"
    commissioned: str = ""


@dataclass
class ZoneTopology:
    zone_id: str
    cdu_ids: List[str]
    rack_ids: List[str]
    sensor_count: int
    thermal_load_mw_design: float
    coolant_type: str = "deionised_water"
    supply_temp_c: float = 18.0
    return_temp_max_c: float = 45.0
    flow_rate_lpm: float = 800.0


class SensorMap:
    ZONES = [f"zone-{i:02d}" for i in range(1, 15)]
    RACKS_PER_ZONE = 24
    CDU_PER_ZONE = 6
    SENSOR_TYPES = [
        ("thermal", 48, "PT100-DIN", 0.001, "degC", 4),
        ("flow", 24, "MAG-EM-600", 0.005, "L/min", 2),
        ("pressure", 24, "PIEZO-BAR-6", 0.002, "bar", 2),
        ("humidity", 18, "CAPACITIVE-RH", 0.015, "%RH", 1),
        ("power", 16, "HALL-CT-3PH", 0.001, "kW", 4),
        ("vibration", 12, "MEMS-ACCEL-3X", 0.005, "mm/s", 8),
    ]

    def __init__(self):
        self._sensors: Dict[str, SensorEntry] = {}
        self._zones: Dict[str, ZoneTopology] = {}
        self._zone_index: Dict[str, List[str]] = {}
        self._build()

    def _build(self):
        for zone_id in self.ZONES:
            racks = [
                f"{zone_id}-rack-{r:02d}" for r in range(1, self.RACKS_PER_ZONE + 1)
            ]
            cdus = [f"{zone_id}-cdu-{c:02d}" for c in range(1, self.CDU_PER_ZONE + 1)]
            self._zones[zone_id] = ZoneTopology(
                zone_id=zone_id,
                cdu_ids=cdus,
                rack_ids=racks,
                sensor_count=142,
                thermal_load_mw_design=50.0,
            )
            ids = []
            for stype, count, model, acc, unit, hz in self.SENSOR_TYPES:
                for i in range(count):
                    sid = f"{zone_id}-{stype}-{i:03d}"
                    self._sensors[sid] = SensorEntry(
                        sensor_id=sid,
                        zone_id=zone_id,
                        rack_id=racks[i % len(racks)],
                        cdu_id=cdus[i % len(cdus)],
                        sensor_type=stype,
                        location="inlet" if i % 2 == 0 else "outlet",
                        accuracy_pct=acc,
                        sample_rate_hz=hz,
                        hardware_model=model,
                        commissioned="2026-01-15",
                    )
                    ids.append(sid)
            self._zone_index[zone_id] = ids

    def zone_sensors(self, zone_id: str) -> List[SensorEntry]:
        return [self._sensors[s] for s in self._zone_index.get(zone_id, [])]

    def get(self, sensor_id: str) -> Optional[SensorEntry]:
        return self._sensors.get(sensor_id)

    def all_zones(self) -> List[str]:
        return list(self._zones.keys())

    def zone_topology(self, zone_id: str) -> Optional[ZoneTopology]:
        return self._zones.get(zone_id)

    def total_sensor_count(self) -> int:
        return len(self._sensors)

    def summary(self) -> dict:
        return {
            "zones": len(self._zones),
            "total_sensors": len(self._sensors),
            "by_type": {
                st: sum(1 for s in self._sensors.values() if s.sensor_type == st)
                for st, *_ in self.SENSOR_TYPES
            },
        }
