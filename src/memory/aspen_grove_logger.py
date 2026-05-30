import asyncio
import json
import os
import time
from typing import Dict, Any

class AspenGroveLogger:
    """
    Aspen Grove Asynchronous Logging Module
    Optimized to eliminate synchronous file I/O overhead on critical telemetry ticks.
    """
    def __init__(self, log_path: str = None):
        self.log_path = log_path or os.path.expandvars("$HOME/logs/aspen_grove_audit.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        self.queue = asyncio.Queue()
        self.worker_task = None
        self.running = False

    def start(self):
        """Start the background worker task to process logs asynchronously."""
        if not self.running:
            self.running = True
            self.worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        """Continuous background loop processing log events from the queue."""
        while self.running or not self.queue.empty():
            try:
                # Wait for an item in the queue with a timeout to allow graceful shutdowns
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._write_to_disk(event)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"⚠️ [Aspen Logger] Worker Error: {e}")

    async def _write_to_disk(self, event: Dict[str, Any]):
        """Non-blocking disk write using asyncio.to_thread to offload file I/O."""
        def sync_write():
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        
        # Offload blocking write to a worker thread
        await asyncio.to_thread(sync_write)

    async def log_event_async(self, event: Dict[str, Any]):
        """
        Asynchronously queue a logging event.
        Guarantees <5ms dispatch time by bypassing blocking disk writes.
        """
        start_time = time.perf_counter()
        
        event["timestamp"] = event.get("timestamp") or time.time()
        await self.queue.put(event)
        
        overhead_ms = (time.perf_counter() - start_time) * 1000.0
        return overhead_ms

    def log_event(self, event: Dict[str, Any]):
        """
        Synchronous-safe wrapper to queue an event without blocking.
        Enables seamless integration with synchronous loops.
        """
        start_time = time.perf_counter()
        event["timestamp"] = event.get("timestamp") or time.time()
        
        # Insert into queue immediately and synchronously
        self.queue.put_nowait(event)
            
        overhead_ms = (time.perf_counter() - start_time) * 1000.0
        return overhead_ms

    async def shutdown(self):
        """Gracefully drain the queue and stop the background worker."""
        self.running = False
        if self.worker_task:
            await self.queue.join()  # Wait for all current queue items to be written
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
