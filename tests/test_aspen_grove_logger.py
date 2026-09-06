"""tests/test_aspen_grove_logger.py

Issue #18 acceptance criteria + audit gap coverage:
  - async write completes without blocking caller (overhead < 5 ms)
  - queue depth warning fires when > QUEUE_DEPTH_WARN items pending
  - no events dropped under normal load
  - graceful flush on shutdown (all events written before return)
  - overflow_count increments when queue is full (not raised)
  - double start() is idempotent — only one worker task (audit gap #3)
  - log_event() before start() does not raise (audit gap #4)
"""

import asyncio
import logging
import os
import pytest

import sys

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from memory.aspen_grove_logger import AspenGroveLogger, QUEUE_DEPTH_WARN, QUEUE_MAX_SIZE


# ── Overhead / non-blocking ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_event_overhead_under_5ms(tmp_path):
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    log.start()
    try:
        overhead = log.log_event({"event": "TEST"})
        assert overhead < 5.0, f"Overhead too high: {overhead:.2f} ms"
    finally:
        await log.shutdown()


@pytest.mark.asyncio
async def test_log_event_async_overhead_under_5ms(tmp_path):
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    log.start()
    try:
        overhead = await log.log_event_async({"event": "ASYNC_TEST"})
        assert overhead < 5.0, f"Async overhead too high: {overhead:.2f} ms"
    finally:
        await log.shutdown()


# ── Correctness under load ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_events_dropped_normal_load(tmp_path):
    log_path = str(tmp_path / "audit.log")
    log = AspenGroveLogger(log_path=log_path)
    log.start()
    N = 100
    for i in range(N):
        log.log_event({"event": f"EV-{i}"})
    await log.shutdown()
    assert log.overflow_count == 0
    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) == N


@pytest.mark.asyncio
async def test_graceful_shutdown_flushes_all(tmp_path):
    log_path = str(tmp_path / "audit.log")
    log = AspenGroveLogger(log_path=log_path)
    log.start()
    N = 50
    for i in range(N):
        log.log_event({"event": f"FLUSH-{i}"})
    await log.shutdown()
    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) == N


# ── Queue depth warning ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_queue_depth_warning_fires(tmp_path, caplog):
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    with caplog.at_level(logging.WARNING, logger="ASPEN-GROVE"):
        for i in range(QUEUE_DEPTH_WARN + 10):
            log._enqueue_nowait({"event": f"EV-{i}"})
    assert any(
        "queue depth" in r.message.lower() or "warn" in r.message.lower()
        for r in caplog.records
    )
    while not log._queue.empty():
        log._queue.get_nowait()
        log._queue.task_done()


# ── Overflow protection ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overflow_count_increments_when_full(tmp_path):
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    for i in range(QUEUE_MAX_SIZE):
        log._queue.put_nowait({"event": f"EV-{i}"})
    log._enqueue_nowait({"event": "OVERFLOW"})
    assert log.overflow_count == 1
    while not log._queue.empty():
        log._queue.get_nowait()
        log._queue.task_done()


# ── Lifecycle edge cases ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_shutdown_idempotent_with_no_events(tmp_path):
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    log.start()
    await asyncio.wait_for(log.shutdown(), timeout=3.0)
    assert log._worker_task is None


@pytest.mark.asyncio
async def test_double_start_is_idempotent(tmp_path):
    """Audit gap #3: calling start() twice must not create two worker tasks."""
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    log.start()
    first_task = log._worker_task
    log.start()  # second call — must be a no-op
    assert log._worker_task is first_task, "start() created a second worker task"
    await log.shutdown()


@pytest.mark.asyncio
async def test_log_event_before_start_does_not_raise(tmp_path):
    """Audit gap #4: log_event() before start() must not raise.

    Events are queued; they will be flushed once start() + shutdown() are called.
    """
    log = AspenGroveLogger(log_path=str(tmp_path / "audit.log"))
    # No start() called yet
    overhead = log.log_event({"event": "PRE-START"})
    assert overhead >= 0  # did not raise
    assert log.queue_depth == 1
    # Now start and drain to verify the event wasn't lost
    log.start()
    await log.shutdown()
    with open(str(tmp_path / "audit.log")) as f:
        lines = f.readlines()
    assert len(lines) == 1
