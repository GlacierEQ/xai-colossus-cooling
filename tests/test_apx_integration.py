import unittest
import asyncio
import os
import json
import time
import shutil
import sys

# Append parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from memory.aspen_grove_logger import AspenGroveLogger
from schemas.mcp_request_validator import MCPRequestValidator

class TestAspenGroveLogger(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_log_dir = os.path.join(os.path.dirname(__file__), "tmp_logs")
        self.test_log_path = os.path.join(self.test_log_dir, "test_audit.log")
        os.makedirs(self.test_log_dir, exist_ok=True)
        self.logger = AspenGroveLogger(log_path=self.test_log_path)

    def tearDown(self):
        # Clean up temporary logs
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir)

    async def test_async_log_latency_and_writing(self):
        """Verify that queuing a log is non-blocking, under 5ms, and writes asynchronously."""
        self.logger.start()
        
        test_event = {"event": "TEST_AUDIT", "details": "Verifying async queue performance"}
        
        # Measure queuing latency
        latency_ms = await self.logger.log_event_async(test_event)
        
        print(f"⏱️ [TEST] Async Log Dispatch Latency: {latency_ms:.4f} ms")
        self.assertLess(latency_ms, 5.0, "Dispatch latency exceeded 5ms SLA limit!")
        
        # Gracefully shutdown (drains the queue to disk)
        await self.logger.shutdown()
        
        # Verify file write occurred
        self.assertTrue(os.path.exists(self.test_log_path), "Log file was not created on disk!")
        
        # Verify written content matches
        with open(self.test_log_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            saved_event = json.loads(lines[0])
            self.assertEqual(saved_event["event"], "TEST_AUDIT")

    async def test_sync_safe_wrapper(self):
        """Verify the synchronous wrapper correctly inserts into queue with low latency."""
        self.logger.start()
        
        test_event = {"event": "SYNC_TEST", "details": "Testing synchronous safety wrapper"}
        latency_ms = self.logger.log_event(test_event)
        
        print(f"⏱️ [TEST] Sync Wrapper Dispatch Latency: {latency_ms:.4f} ms")
        self.assertLess(latency_ms, 5.0, "Sync wrapper exceeded 5ms limit!")
        
        # Yield control back to allow scheduled queue task to execute
        await asyncio.sleep(0.1)
        await self.logger.shutdown()
        
        self.assertTrue(os.path.exists(self.test_log_path))
        with open(self.test_log_path, "r") as f:
            saved_event = json.loads(f.readline())
            self.assertEqual(saved_event["event"], "SYNC_TEST")

class TestMCPRequestValidator(unittest.TestCase):
    def setUp(self):
        self.validator = MCPRequestValidator()

    def test_valid_mcp_request(self):
        """Verify standard compliant MCP requests pass validation."""
        valid_payload = {
            "request_type": "request_zone_snapshot",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-06-24T00:00:00Z",
            "source_agent": "test-agent",
            "severity": "INFO",
            "zone_id": "ZONE-A"
        }
        is_valid, msg = self.validator.validate(valid_payload)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "VALIDATED")

    def test_invalid_request_type(self):
        """Verify invalid request types are rejected."""
        invalid_payload = {
            "request_type": "invalid_type",
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-06-24T00:00:00Z",
            "source_agent": "test-agent",
            "severity": "INFO"
        }
        is_valid, msg = self.validator.validate(invalid_payload)
        self.assertFalse(is_valid)

    def test_missing_required_fields(self):
        """Verify payloads missing required keys are rejected."""
        missing_payload = {
            "jsonrpc": "2.0",
            "method": "tools/list"
            # Missing 'id'
        }
        is_valid, msg = self.validator.validate(missing_payload)
        self.assertFalse(is_valid)
        self.assertTrue(any(x in msg.lower() for x in ["id", "required", "expected"]))


    def test_invalid_payload_types(self):
        """Verify incorrect parameter types are rejected."""
        invalid_type_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": "request_id_001",
            "params": {
                "name": 12345,  # Should be string
                "arguments": ["not", "an", "object"]  # Should be dict
            }
        }
        is_valid, msg = self.validator.validate(invalid_type_payload)
        self.assertFalse(is_valid)

class TestMCPRouterIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_router_tick_dispatch(self):
        """Verify MCP requests are queued, validated, and executed during tick cycles."""
        from apex_core.thermal_orchestrator import APEXThermalOrchestrator, CoolingZone, ThermalNode
        
        # 1. Initialize orchestrator and clean existing log
        orch = APEXThermalOrchestrator()
        if os.path.exists(orch.aspen_logger.log_path):
            os.remove(orch.aspen_logger.log_path)
            
        # Register a synthetic zone with warm nodes
        zone = CoolingZone(zone_id="ZONE-T1", zone_name="Test Zone")
        node = ThermalNode(
            node_id="NODE-001", rack_id="RACK-001", zone_id="ZONE-T1",
            temp_celsius=75.0, gpu_utilization=0.8, power_watts=700
        )
        zone.nodes.append(node)
        orch.register_zone(zone)
        
        # 2. Queue a valid tool request
        valid_request = {
            "request_type": "emergency_broadcast",
            "request_id": "550e8400-e29b-41d4-a716-446655440999",
            "timestamp": "2026-06-24T00:00:00Z",
            "source_agent": "test-agent",
            "severity": "CRITICAL",
            "zone_id": "ZONE-A"
        }
        orch._mcp_router.queue_request(valid_request)
        
        # 3. Queue an invalid request (to verify rejection)
        invalid_request = {
            "request_type": "invalid_type",
            "request_id": "550e8400-e29b-41d4-a716-446655440888",
            "timestamp": "2026-06-24T00:00:00Z",
            "source_agent": "test-agent"
        }
        orch._mcp_router.queue_request(invalid_request)
        
        # 4. Trigger one tick cycle
        tick_result = await orch.tick_cycle()
        
        # 5. Verify results
        self.assertEqual(tick_result["tick"], 1)
        
        # Verify the logger successfully wrote the audit events asynchronously
        await orch.aspen_logger.shutdown()
        
        log_path = orch.aspen_logger.log_path
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r") as f:
            lines = f.readlines()
            events = [json.loads(line) for line in lines]
            mcp_events = [e for e in events if e.get("event") == "MCP_DISPATCH"]
            
            self.assertEqual(len(mcp_events), 2)
            
            # First request (999) must be EXECUTED
            req_999 = next(e for e in mcp_events if e["request_id"] == 999)
            self.assertEqual(req_999["status"], "EXECUTED")
            self.assertEqual(req_999["method"], "tools/call")
            
            # Second request (888) must be REJECTED
            req_888 = next(e for e in mcp_events if e["request_id"] == 888)
            self.assertEqual(req_888["status"], "REJECTED")
            self.assertIsNotNone(req_888["error_message"])

if __name__ == "__main__":
    unittest.main()

