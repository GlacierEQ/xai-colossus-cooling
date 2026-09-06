"""
Zone Telemetry Agent — xAI Colossus Cooling
Real-time thermal, flow, pressure, humidity ingestion per cooling zone.
"""

from .agent import ZoneTelemetryAgent
from .sensor_map import SensorMap, SensorEntry, ZoneTopology
from .stream import KafkaStreamProducer

__version__ = "0.1.0"
__all__ = [
    "ZoneTelemetryAgent",
    "SensorMap",
    "SensorEntry",
    "ZoneTopology",
    "KafkaStreamProducer",
]
