#!/usr/bin/env python3
"""
Redfish / IPMI Sensor Stub — xAI Colossus Cooling
GlacierEQ APEX Architecture
Author: Casey Barton

Abstraction layer for real hardware telemetry ingestion.
Supports:
  - DMTF Redfish REST API (industry standard BMC interface)
  - IPMI over LAN (legacy OOB management)
  - Mock/simulation mode for dev and CI

In production, point REDFISH_ENDPOINT + REDFISH_USER + REDFISH_PASS
at a real BMC (e.g., Dell iDRAC, HPE iLO, Supermicro IPMI).
"""

import os
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger("SENSOR-REDFISH")


class RedfishSensorReading:
    """Normalized sensor reading from a BMC endpoint."""

    def __init__(
        self,
        node_id: str,
        rack_id: str,
        zone_id: str,
        inlet_temp_c: float,
        exhaust_temp_c: float,
        gpu_temps_c: List[float],
        power_watts: float,
        fan_rpm: int,
        source: str = "redfish",
    ):
        self.node_id = node_id
        self.rack_id = rack_id
        self.zone_id = zone_id
        self.inlet_temp_c = inlet_temp_c
        self.exhaust_temp_c = exhaust_temp_c
        self.gpu_temps_c = gpu_temps_c
        self.power_watts = power_watts
        self.fan_rpm = fan_rpm
        self.source = source
        self.timestamp = datetime.utcnow().isoformat()

    @property
    def max_gpu_temp(self) -> float:
        return max(self.gpu_temps_c) if self.gpu_temps_c else self.exhaust_temp_c

    def to_thermal_node_dict(self) -> dict:
        """Convert to dict compatible with ThermalNode constructor."""
        return {
            "node_id": self.node_id,
            "rack_id": self.rack_id,
            "zone_id": self.zone_id,
            "temp_celsius": self.max_gpu_temp,
            "gpu_utilization": 0.0,  # Populated separately via DCGM/NVML
            "power_watts": self.power_watts,
        }


class RedfishSensorInterface:
    """
    Hardware sensor interface for Colossus-class compute nodes.

    Modes:
      - MOCK: synthetic data (CI, dev, demo)
      - REDFISH: live Redfish REST BMC polling
      - IPMI: fallback IPMI-over-LAN
    """

    MODE_MOCK = "MOCK"
    MODE_REDFISH = "REDFISH"
    MODE_IPMI = "IPMI"

    def __init__(self, mode: str = None):
        self.mode = mode or os.getenv("SENSOR_MODE", self.MODE_MOCK)
        self.endpoint = os.getenv("REDFISH_ENDPOINT", "")
        self.user = os.getenv("REDFISH_USER", "admin")
        self.password = os.getenv("REDFISH_PASS", "")
        self._session = None
        logger.info(f"RedfishSensorInterface initialized | mode={self.mode}")

    def connect(self):
        if self.mode == self.MODE_MOCK:
            logger.info("Sensor interface: MOCK mode active")
            return
        if self.mode == self.MODE_REDFISH:
            try:
                import requests

                self._session = requests.Session()
                self._session.auth = (self.user, self.password)
                self._session.verify = False  # Dev: skip TLS; prod: use cert bundle
                logger.info(f"Redfish session established: {self.endpoint}")
            except ImportError:
                logger.warning("requests not installed; falling back to MOCK")
                self.mode = self.MODE_MOCK
        if self.mode == self.MODE_IPMI:
            logger.info("IPMI mode: use pyipmi or ipmitool subprocess wrapper")

    def poll_node(
        self, node_id: str, rack_id: str, zone_id: str, base_temp: float = 65.0
    ) -> RedfishSensorReading:
        """Poll a single node. Returns a normalized reading."""
        if self.mode == self.MODE_MOCK:
            return self._mock_reading(node_id, rack_id, zone_id, base_temp)
        if self.mode == self.MODE_REDFISH:
            return self._redfish_reading(node_id, rack_id, zone_id)
        return self._mock_reading(node_id, rack_id, zone_id, base_temp)

    def _mock_reading(
        self, node_id: str, rack_id: str, zone_id: str, base_temp: float = 65.0
    ) -> RedfishSensorReading:
        """Realistic mock data with configurable heat curves."""
        jitter = random.gauss(0, 1.5)
        inlet = base_temp * 0.34 + jitter * 0.3  # ~22C inlet at 65C base
        exhaust = base_temp * 0.54 + jitter * 0.5  # ~35C exhaust at 65C base
        gpu_temps = [base_temp + random.gauss(0, 2) for _ in range(8)]
        return RedfishSensorReading(
            node_id=node_id,
            rack_id=rack_id,
            zone_id=zone_id,
            inlet_temp_c=round(inlet, 1),
            exhaust_temp_c=round(exhaust, 1),
            gpu_temps_c=[round(t, 1) for t in gpu_temps],
            power_watts=round(random.uniform(600, 750), 0),
            fan_rpm=random.randint(8000, 12000),
            source="mock",
        )

    def _redfish_reading(
        self, node_id: str, rack_id: str, zone_id: str
    ) -> Optional[RedfishSensorReading]:
        """Fetch thermal data from Redfish Thermal endpoint."""
        if not self._session or not self.endpoint:
            logger.error("Redfish session not established")
            return self._mock_reading(node_id, rack_id, zone_id)
        try:
            url = f"{self.endpoint}/redfish/v1/Chassis/{node_id}/Thermal"
            resp = self._session.get(url, timeout=2)
            resp.raise_for_status()
            data = resp.json()
            temps = [
                t.get("ReadingCelsius", 65.0) for t in data.get("Temperatures", [])
            ]
            fans = [f.get("Reading", 10000) for f in data.get("Fans", [])]
            return RedfishSensorReading(
                node_id=node_id,
                rack_id=rack_id,
                zone_id=zone_id,
                inlet_temp_c=temps[0] if temps else 22.0,
                exhaust_temp_c=temps[-1] if temps else 35.0,
                gpu_temps_c=temps,
                power_watts=700.0,
                fan_rpm=fans[0] if fans else 10000,
                source="redfish",
            )
        except Exception as e:
            logger.error(f"Redfish poll failed for {node_id}: {e}")
            return self._mock_reading(node_id, rack_id, zone_id)

    def poll_cluster(self, node_map: List[Dict]) -> List[RedfishSensorReading]:
        """
        Poll all nodes in the cluster.
        node_map: list of {node_id, rack_id, zone_id, base_temp}
        """
        readings = []
        for n in node_map:
            readings.append(
                self.poll_node(
                    n["node_id"],
                    n["rack_id"],
                    n["zone_id"],
                    base_temp=n.get("base_temp", 65.0),
                )
            )
        return readings
