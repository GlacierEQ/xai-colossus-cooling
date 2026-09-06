#!/usr/bin/env python3
"""
memory/aspen_grove_async_flush.py
==================================
P1 SWARM — Aspen Grove Async Flush: Non-Blocking Audit Writes

Replaces synchronous file I/O on every dispatch with an asyncio.Queue +
background writer task. Target overhead: < 5 ms per dispatch event.

Key guarantees:
  - No dispatch tick is blocked waiting for disk I/O.
  - Batch writes: configurable batch_size reduces syscalls.
  - Configurable flush_interval: background writer drains on interval or batch full.
  - Queue depth monitoring with WARNING at configurable threshold.
  - flush_and_close() drains the queue fully before shutdown — zero event loss.
  - Sync fallback for non-async contexts (unit tests, scripts).

Usage:
    from memory.aspen_grove_async_flush import AsyncFlushLogger

    logger = AsyncFlushLogger(log_path="audit_logs/async_flush.jsonl")
    await logger.start()
    await logger.log_event({"type": "thermal_dispatch", "zone": "Z-A"})
    await logger.flush_and_close()
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("ASPEN-ASYNC-FLUSH")

_DEFAULT_LOG_PATH = "audit_logs/aspen_async_flush.jsonl"
_DEFAULT_BATCH_SIZE = 50
_DEFAULT_FLUSH_INTERVAL_S = 2.0
_DEFAULT_QUEUE_WARN_DEPTH = 1000
_SHUTDOWN_SENTINEL = None


class AsyncFlushLogger:
    """Async-first structured event logger with batched writes and configurable flush interval.

    All writes go through an asyncio.Queue consumed by a single background
    coroutine. Events are batched up to `batch_size` before a single disk
    write, reducing syscall overhead under high dispatch rates.

    Attributes:
        stats: dict with written, dropped, queue_depth, running, batch_count.
    """

    def __init__(
        self,
        log_path: str = _DEFAULT_LOG_PATH,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        flush_interval_s: float = _DEFAULT_FLUSH_INTERVAL_S,
        queue_warn_depth: int = _DEFAULT_QUEUE_WARN_DEPTH,
    ):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._batch_size = max(batch_size, 1)
        self._flush_interval_s = max(flush_interval_s, 0.1)
        self._queue_warn_depth = queue_warn_depth
        self._queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._written = 0
        self._dropped = 0
        self._batch_count = 0

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start the background writer task. Idempotent."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._writer_loop(), name="async-flush-writer")
        log.info(
            "AsyncFlushLogger started | path=%s batch_size=%d flush_interval=%.1fs",
            self.log_path,
            self._batch_size,
            self._flush_interval_s,
        )

    async def flush_and_close(self) -> None:
        """Drain the queue completely, then stop the background writer.

        Call this during graceful shutdown to ensure zero event loss.
        """
        if not self._running:
            return
        await self._queue.put(_SHUTDOWN_SENTINEL)
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                log.error(
                    "AsyncFlushLogger flush timed out — %d events may be lost",
                    self._queue.qsize(),
                )
        self._running = False
        log.info(
            "AsyncFlushLogger closed | written=%d dropped=%d batches=%d",
            self._written,
            self._dropped,
            self._batch_count,
        )

    # ------------------------------------------------------------------ #
    # Hot path                                                             #
    # ------------------------------------------------------------------ #

    async def log_event(self, event: Dict[str, Any]) -> None:
        """Enqueue an audit event for async write. Returns immediately.

        Falls back to synchronous write if the background task is not running.
        """
        enriched = {"_logged_at": time.time(), **event}

        if not self._running:
            self._sync_write(enriched)
            return

        depth = self._queue.qsize()
        if depth >= self._queue_warn_depth:
            log.warning(
                "AsyncFlushLogger queue depth %d >= %d — possible write stall",
                depth,
                self._queue_warn_depth,
            )

        self._queue.put_nowait(enriched)

    # ------------------------------------------------------------------ #
    # Background writer loop                                               #
    # ------------------------------------------------------------------ #

    async def _writer_loop(self) -> None:
        """Consume the queue in batches and write JSONL lines to disk."""
        with open(self.log_path, "a", encoding="utf-8", buffering=1) as fh:
            while True:
                batch: list[Dict[str, Any]] = []
                try:
                    first_item = await asyncio.wait_for(
                        self._queue.get(), timeout=self._flush_interval_s
                    )
                    if first_item is _SHUTDOWN_SENTINEL:
                        self._drain_remaining(fh)
                        break
                    batch.append(first_item)
                    self._queue.task_done()

                    while len(batch) < self._batch_size:
                        try:
                            item = self._queue.get_nowait()
                            if item is _SHUTDOWN_SENTINEL:
                                self._flush_batch(fh, batch)
                                self._drain_remaining(fh)
                                return
                            batch.append(item)
                            self._queue.task_done()
                        except asyncio.QueueEmpty:
                            break

                    self._flush_batch(fh, batch)

                except asyncio.TimeoutError:
                    if not self._running:
                        self._drain_remaining(fh)
                        break
                    continue
                except Exception as exc:
                    log.exception("AsyncFlushLogger writer error: %s", exc)
                    self._dropped += len(batch)

    def _flush_batch(self, fh: Any, batch: list[Dict[str, Any]]) -> None:
        """Write a batch of events as JSONL lines."""
        if not batch:
            return
        lines = []
        for event in batch:
            try:
                lines.append(json.dumps(event, default=str))
            except Exception as exc:
                log.error("AsyncFlushLogger serialization error: %s", exc)
                self._dropped += 1
        if lines:
            try:
                fh.write("\n".join(lines) + "\n")
                self._written += len(lines)
                self._batch_count += 1
            except Exception as exc:
                log.error("AsyncFlushLogger batch write failed: %s", exc)
                self._dropped += len(lines)

    def _drain_remaining(self, fh: Any) -> None:
        """Drain any remaining items from the queue after shutdown sentinel."""
        remaining: list[Dict[str, Any]] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                if item is not _SHUTDOWN_SENTINEL and item is not None:
                    remaining.append(item)
            except asyncio.QueueEmpty:
                break
        if remaining:
            self._flush_batch(fh, remaining)

    def _sync_write(self, event: Dict[str, Any]) -> None:
        """Synchronous fallback write for non-async contexts."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
            self._written += 1
        except Exception as exc:
            log.error("AsyncFlushLogger sync fallback write failed: %s", exc)
            self._dropped += 1

    # ------------------------------------------------------------------ #
    # Diagnostics                                                          #
    # ------------------------------------------------------------------ #

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "written": self._written,
            "dropped": self._dropped,
            "queue_depth": self._queue.qsize(),
            "running": self._running,
            "batch_count": self._batch_count,
            "log_path": str(self.log_path),
        }
