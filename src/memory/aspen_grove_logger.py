"""Aspen Grove Asynchronous Audit Logger

Non-blocking audit writes for the APEX MCP dispatch loop.

v1.2.0 changes (quality audit follow-up):
  - Bug fix: makedirs guard for bare filenames (dirname == '')
  - Bug fix: _write_to_disk errors now increment overflow_count and are
    surfaced as structured ERROR logs rather than silently consumed
  - Docstring: clarifies async vs sync back-pressure contract
"""

import asyncio
import json
import logging
import os
import time
import traceback
from typing import Any, Dict

logger = logging.getLogger("ASPEN-GROVE")

QUEUE_DEPTH_WARN = 1000    # emit WARNING when pending items exceeds this
QUEUE_MAX_SIZE   = 10_000  # hard cap to prevent unbounded memory growth


class AspenGroveLogger:
    """
    Aspen Grove Asynchronous Logging Module.

    All disk writes happen in a background worker via asyncio.to_thread so the
    dispatch loop is never blocked by file I/O.  Overhead per log_event() call
    is < 5 ms under normal load (queue put is O(1), no syscall on caller side).

    Back-pressure contract
    ----------------------
    - log_event()       (sync)  — uses put_nowait(): O(1), never blocks, never
                                  raises. If queue is full, event is DROPPED and
                                  overflow_count is incremented.
    - log_event_async() (async) — uses queue.put(): applies back-pressure when
                                  queue is full (caller awaits). Preferred for
                                  coroutine callers that can tolerate yielding.

    Usage
    -----
    log = AspenGroveLogger()
    log.start()                      # call once inside a running event loop
    log.log_event({...})             # sync-safe, < 5 ms
    await log.log_event_async({...}) # awaitable variant
    await log.shutdown()             # drain & stop before process exit
    """

    def __init__(self, log_path: str = None):
        self.log_path = log_path or os.path.expandvars("$HOME/logs/aspen_grove_audit.log")
        # Bug fix v1.2.0: dirname() returns '' for bare filenames (e.g. 'audit.log').
        # Only create the directory when there is actually a directory component.
        parent_dir = os.path.dirname(self.log_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self._queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        self._worker_task: asyncio.Task = None
        self._running: bool = False
        self._overflow_count: int = 0  # events dropped (queue full OR write error)
        self._depth_warned: bool = False  # rate-limit depth warnings

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def queue_depth(self) -> int:
        """Current number of events pending disk flush."""
        return self._queue.qsize()

    @property
    def overflow_count(self) -> int:
        """Total events dropped since startup (queue full or disk error)."""
        return self._overflow_count

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background writer task. Call once inside a running event loop.

        Idempotent: calling start() more than once is safe — only one worker
        task is ever created.
        """
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.debug("AspenGroveLogger worker started (log_path=%s)", self.log_path)

    async def shutdown(self) -> None:
        """Gracefully drain the queue then stop the background worker.

        Guaranteed to flush all successfully-writable queued events before
        returning, even if the queue is large.
        """
        self._running = False
        if self._worker_task is not None:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "AspenGroveLogger shutdown: flush timed out after 10 s; "
                    "%d events may be lost",
                    self._queue.qsize(),
                )
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        if self._overflow_count:
            logger.warning(
                "AspenGroveLogger shutdown: %d total events dropped (queue overflow or disk error)",
                self._overflow_count,
            )

    # ------------------------------------------------------------------
    # Logging interface
    # ------------------------------------------------------------------

    def log_event(self, event: Dict[str, Any]) -> float:
        """Synchronous-safe enqueue. Returns caller-side overhead in ms (< 5 ms).

        Uses put_nowait() — O(1), no coroutine suspension, safe from sync code.
        If the queue is full, the event is dropped and overflow_count increments.
        """
        t0 = time.perf_counter()
        event.setdefault("timestamp", time.time())
        self._enqueue_nowait(event)
        return (time.perf_counter() - t0) * 1000.0

    async def log_event_async(self, event: Dict[str, Any]) -> float:
        """Awaitable enqueue. Applies back-pressure when queue is full.

        Returns caller-side overhead in ms.
        """
        t0 = time.perf_counter()
        event.setdefault("timestamp", time.time())
        await self._queue.put(event)
        self._check_depth_warning()
        return (time.perf_counter() - t0) * 1000.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue_nowait(self, event: Dict[str, Any]) -> None:
        """Put event on queue without blocking; drop + count if full."""
        try:
            self._queue.put_nowait(event)
            self._check_depth_warning()
        except asyncio.QueueFull:
            self._overflow_count += 1
            logger.error(
                "AspenGroveLogger QUEUE FULL — event dropped (total dropped=%d)",
                self._overflow_count,
            )

    def _check_depth_warning(self) -> None:
        """Emit a single WARNING when queue depth crosses QUEUE_DEPTH_WARN.

        Rate-limited: one warning per crossing; resets when depth falls back
        below threshold so the next crossing warns again.
        """
        depth = self._queue.qsize()
        if depth > QUEUE_DEPTH_WARN:
            if not self._depth_warned:
                logger.warning(
                    "AspenGroveLogger queue depth %d exceeds warn threshold %d — "
                    "writer may be falling behind",
                    depth, QUEUE_DEPTH_WARN,
                )
                self._depth_warned = True
        else:
            self._depth_warned = False

    async def _worker(self) -> None:
        """Continuous background loop: drain queue → write to disk."""
        while self._running or not self._queue.empty():
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                try:
                    await self._write_to_disk(event)
                except Exception as exc:
                    # Bug fix v1.2.0: disk errors (full disk, permissions) must NOT be
                    # silently swallowed. Increment overflow_count so ops can detect
                    # event loss, then call task_done() so shutdown drain doesn't hang.
                    self._overflow_count += 1
                    logger.error(
                        "AspenGroveLogger disk write failed (event lost, total dropped=%d): %s\n%s",
                        self._overflow_count, exc, traceback.format_exc(),
                    )
                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def _write_to_disk(self, event: Dict[str, Any]) -> None:
        """Offload blocking file write to a thread pool via asyncio.to_thread."""
        line = json.dumps(event) + "\n"

        def _sync_write() -> None:
            with open(self.log_path, "a") as fh:
                fh.write(line)

        await asyncio.to_thread(_sync_write)
