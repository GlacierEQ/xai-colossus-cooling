"""tests/test_aspen_grove_logger.py

Issue #18 acceptance criteria:
  - async write completes without blocking caller (overhead < 5 ms)
  - queue depth warning fires when > QUEUE_DEPTH_WARN items pending
  - no events dropped under normal load
  - graceful flush on shutdown (all events written before return)
  - overflow_count increments when queue is full (not raised)
"""

import asyncio
import os
import tempfile
import time
import pytest
from unittest.mock import patch

import sys
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from memory.aspen_grove_logger import AspenGroveLogger, QUEUE_DEPTH_WARN, QUEUE_MAX_SIZE


@pytest.fixture
def tmp_log(tmp_path):
    return str(tmp_path / "test_audit.log")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_event_overhead_under_5ms(tmp_log):
    """log_event() (sync) must return in < 5 ms."""
    log = AspenGroveLogger(log_path=tmp_log)
    log.start()
    try:
        overhead = log.log_event({"event": "TEST", "data": "hello"})
        assert overhead < 5.0, f"Overhead too high: {overhead:.2f} ms"
    finally:
        await log.shutdown()


@pytest.mark.asyncio
async def test_log_event_async_overhead_under_5ms(tmp_log):
    """log_event_async() must return in < 5 ms (queue put only, not disk write)."""
    log = AspenGroveLogger(log_path=tmp_log)
    log.start()
    try:
        overhead = await log.log_event_async({"event": "ASYNC_TEST"})
        assert overhead < 5.0, f"Async overhead too high: {overhead:.2f} ms"
    finally:
        await log.shutdown()


@pytest.mark.asyncio
async def test_no_events_dropped_normal_load(tmp_log):
    """100 events under normal load: all written, none dropped."""
    log = AspenGroveLogger(log_path=tmp_log)
    log.start()
    N = 100
    for i in range(N):
        log.log_event({"event": f"EV-{i}"})
    await log.shutdown()
    assert log.overflow_count == 0
    with open(tmp_log) as f:
        lines = f.readlines()
    assert len(lines) == N, f"Expected {N} lines, got {len(lines)}"


@pytest.mark.asyncio
async def test_queue_depth_warning_fires(tmp_log, caplog):
    """A warning must be emitted when queue depth exceeds QUEUE_DEPTH_WARN."""
    import logging
    log = AspenGroveLogger(log_path=tmp_log)
    # Do NOT start the worker — so items accumulate without being consumed
    with caplog.at_level(logging.WARNING, logger="ASPEN-GROVE"):
        for i in range(QUEUE_DEPTH_WARN + 10):
            log._enqueue_nowait({"event": f"EV-{i}"})
    assert any("queue depth" in r.message.lower() or "warn" in r.message.lower()
               for r in caplog.records), "Expected queue depth warning"
    # Cleanup: drain without starting worker
    while not log._queue.empty():
        log._queue.get_nowait()
        log._queue.task_done()


@pytest.mark.asyncio
async def test_graceful_shutdown_flushes_all(tmp_log):
    """shutdown() must wait for all queued events to be written."""
    log = AspenGroveLogger(log_path=tmp_log)
    log.start()
    N = 50
    for i in range(N):
        log.log_event({"event": f"FLUSH-{i}"})
    await log.shutdown()
    with open(tmp_log) as f:
        lines = f.readlines()
    assert len(lines) == N


@pytest.mark.asyncio
async def test_overflow_count_increments_when_full(tmp_log):
    """When queue is full, events are dropped and overflow_count increments."""
    log = AspenGroveLogger(log_path=tmp_log)
    # Fill the queue to capacity without starting worker
    for i in range(QUEUE_MAX_SIZE):
        log._queue.put_nowait({"event": f"EV-{i}"})
    # One more should overflow
    log._enqueue_nowait({"event": "OVERFLOW"})
    assert log.overflow_count == 1
    # Cleanup
    while not log._queue.empty():
        log._queue.get_nowait()
        log._queue.task_done()


@pytest.mark.asyncio
async def test_shutdown_idempotent_with_no_events(tmp_log):
    """shutdown() on an empty queue must return without hanging."""
    log = AspenGroveLogger(log_path=tmp_log)
    log.start()
    await asyncio.wait_for(log.shutdown(), timeout=3.0)
    assert log._worker_task is None
