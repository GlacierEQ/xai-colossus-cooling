#!/usr/bin/env python3
"""
tests/test_aspen_logger.py
==========================
Unit tests for Issue #18 — Aspen Grove Async Flush.

Measures that log_event overhead is < 5 ms and verifies async drain
behaviour on flush_and_close().
"""

import asyncio
import json
import time
import tempfile
from pathlib import Path

import pytest
from apex_core.aspen_logger import AspenLogger


@pytest.mark.asyncio
async def test_log_event_overhead_under_5ms():
    """Enqueuing a single event must take < 5 ms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AspenLogger(log_path=f"{tmpdir}/test.jsonl")
        await logger.start()

        event = {"type": "test", "value": 42}
        t0 = time.perf_counter()
        await logger.log_event(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        await logger.flush_and_close()

        assert elapsed_ms < 5.0, f"log_event took {elapsed_ms:.2f} ms — exceeds 5 ms target"


@pytest.mark.asyncio
async def test_all_events_written_on_flush():
    """All enqueued events must appear in the log after flush_and_close()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "events.jsonl"
        logger = AspenLogger(log_path=str(log_path))
        await logger.start()

        n = 100
        for i in range(n):
            await logger.log_event({"seq": i, "agent": "MICROWAVE"})

        await logger.flush_and_close()

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == n, f"Expected {n} lines, got {len(lines)}"
        parsed = [json.loads(l) for l in lines]
        seqs = [p["seq"] for p in parsed]
        assert sorted(seqs) == list(range(n))


@pytest.mark.asyncio
async def test_queue_depth_warning(caplog):
    """A warning must be emitted when queue depth >= 1000."""
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AspenLogger(log_path=f"{tmpdir}/warn.jsonl")
        # Don't start the background writer — queue accumulates
        logger._running = True  # trick: mark running so log_event uses async path

        with caplog.at_level(logging.WARNING, logger="APEX-ASPEN-LOGGER"):
            for i in range(1001):
                logger._queue.put_nowait({"seq": i})
            # Manually trigger one more log_event to hit the depth check
            await logger.log_event({"seq": 1001})

        assert any("queue depth" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_stats_reflect_writes():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AspenLogger(log_path=f"{tmpdir}/stats.jsonl")
        await logger.start()
        await logger.log_event({"type": "ping"})
        await logger.flush_and_close()

        assert logger.stats["written"] == 1
        assert logger.stats["dropped"] == 0
        assert logger.stats["running"] is False


def test_sync_fallback_write():
    """Synchronous fallback (non-async context) must write without error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "sync.jsonl"
        logger = AspenLogger(log_path=str(log_path))
        # _running is False — log_event in sync context
        asyncio.run(logger.log_event({"type": "sync_test"}))

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["type"] == "sync_test"
