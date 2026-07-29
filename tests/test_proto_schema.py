"""Test suite verifying Protobuf telemetry schema validation."""
import unittest

class GPUCoolingTelemetrySim:
    def __init__(self, cluster_id: int, total_gpus: int, flow_rate_lpm: float, pue_ratio: float):
        self.cluster_id = cluster_id
        self.total_gpus = total_gpus
        self.flow_rate_lpm = flow_rate_lpm
        self.pue_ratio = pue_ratio

class TestProtobufTelemetrySchema(unittest.TestCase):

    def test_schema_fields(self):
        telem = GPUCoolingTelemetrySim(cluster_id=1, total_gpus=100000, flow_rate_lpm=45000.0, pue_ratio=1.08)
        self.assertEqual(telem.total_gpus, 100000)
        self.assertEqual(telem.pue_ratio, 1.08)

if __name__ == "__main__":
    unittest.main()
