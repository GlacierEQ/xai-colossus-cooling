#!/usr/bin/env python3
"""
Redfish Sensor — Unit Test Suite
"""

import pytest
from sensors.redfish_stub import RedfishSensorReading

class TestRedfishSensorReading:
    def test_max_gpu_temp_with_temps(self):
        """Test max_gpu_temp returns the maximum value from gpu_temps_c."""
        reading = RedfishSensorReading(
            node_id='N1', rack_id='R1', zone_id='Z1',
            inlet_temp_c=22.0, exhaust_temp_c=35.0,
            gpu_temps_c=[60.0, 75.5, 68.0, 72.0],
            power_watts=700.0, fan_rpm=10000
        )
        assert reading.max_gpu_temp == 75.5

    def test_max_gpu_temp_empty_temps(self):
        """Test max_gpu_temp returns exhaust_temp_c when gpu_temps_c is empty."""
        reading = RedfishSensorReading(
            node_id='N1', rack_id='R1', zone_id='Z1',
            inlet_temp_c=22.0, exhaust_temp_c=35.0,
            gpu_temps_c=[],
            power_watts=700.0, fan_rpm=10000
        )
        assert reading.max_gpu_temp == 35.0

    def test_max_gpu_temp_none_temps(self):
        """Test max_gpu_temp returns exhaust_temp_c when gpu_temps_c is None."""
        reading = RedfishSensorReading(
            node_id='N1', rack_id='R1', zone_id='Z1',
            inlet_temp_c=22.0, exhaust_temp_c=35.0,
            gpu_temps_c=None,
            power_watts=700.0, fan_rpm=10000
        )
        assert reading.max_gpu_temp == 35.0

    def test_to_thermal_node_dict(self):
        """Test conversion to ThermalNode compatible dictionary."""
        reading = RedfishSensorReading(
            node_id='N1', rack_id='R1', zone_id='Z1',
            inlet_temp_c=22.0, exhaust_temp_c=35.0,
            gpu_temps_c=[75.0, 80.0],
            power_watts=700.0, fan_rpm=10000
        )
        d = reading.to_thermal_node_dict()
        assert d['node_id'] == 'N1'
        assert d['temp_celsius'] == 80.0
        assert d['power_watts'] == 700.0
