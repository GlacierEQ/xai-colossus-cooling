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
        """Verify standard compliant JSON-RPC 2.0 requests pass validation."""
        valid_payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 123,
            "params": {
                "name": "vault_sync",
                "arguments": {"dry_run": False}
            }
        }
        is_valid, msg = self.validator.validate(valid_payload)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "VALIDATED")

    def test_invalid_rpc_version(self):
        """Verify non-2.0 JSON-RPC versions are rejected."""
        invalid_payload = {
            "jsonrpc": "1.0",
            "method": "tools/list",
            "id": 1
        }
        is_valid, msg = self.validator.validate(invalid_payload)
        self.assertFalse(is_valid)
        self.assertTrue(any(x in msg.lower() for x in ["jsonrpc", "expected", "2.0"]))

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

if __name__ == "__main__":
    unittest.main()
