#!/usr/bin/env python3
"""
apex_core/aspen_logger.py
=========================
Issue #18 — Aspen Grove Async Flush: Non-Blocking Audit Writes

Replaces the previous synchronous _log_event file I/O pattern with an
asyncio.Queue + background writer task. Target overhead: < 5 ms per
dispatch event.

Key guarantees:
  - No dispatch tick is blocked waiting for disk I/O.
  - Queue depth is monitored; a WARNING is emitted when depth > 1000.
  - flush_and_close() drains the queue fully before shutdown — no events
    are lost on clean exit.
  - If the background task has not been started, log_event() falls back to
    synchronous write so the module is safe to use in non-async contexts
    (e.g., unit tests that do not run an event loop).

Usage (within an async context):
    from apex_core.aspen_logger import AspenLogger

    logger = AspenLogger(log_path="audit_logs/aspen_events.jsonl")
    await logger.start()            # launches background writer
    await logger.log_event(event)   # non-blocking, < 5 ms
    # ... at shutdown:
    await logger.flush_and_close()  # drains queue then stops writer
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("APEX-ASPEN-LOGGER")

_QUEUE_WARN_DEPTH = 1000
_DEFAULT_LOG_PATH = "audit_logs/aspen_events.jsonl"


class AspenLogger:
    """
    Async-first structured event logger for the Aspen Grove audit trail.

    All writes go through an asyncio.Queue consumed by a single background
    coroutine, keeping the hot dispatch path allocation-free after the first
    put_nowait call.
    """

    def __init__(self, log_path: str = _DEFAULT_LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._written = 0
        self._dropped = 0  # only incremented on unexpected errors

    # ----------------------------------------------------------------------- #
    # Lifecycle                                                                 #
    # ----------------------------------------------------------------------- #

    async def start(self) -> None:
        """Start the background writer task. Idempotent."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._writer_loop(), name="aspen-logger-writer"
        )
        log.info("AspenLogger started | path=%s", self.log_path)

    async def flush_and_close(self) -> None:
        """
        Drain the queue completely, then stop the background writer.
        Call this during graceful shutdown to ensure zero event loss.
        """
        if not self._running:
            return
        # Sentinel value signals the writer to stop after draining
        await self._queue.put(None)
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                log.error(
                    "AspenLogger flush timed out after 10 s — %d events may be lost",
                    self._queue.qsize(),
                )
        self._running = False
        log.info(
            "AspenLogger closed | written=%d dropped=%d", self._written, self._dropped
        )

    # ----------------------------------------------------------------------- #
    # Hot path                                                                  #
    # ----------------------------------------------------------------------- #

    async def log_event(self, event: Dict[str, Any]) -> None:
        """
        Enqueue an audit event for async write. Returns immediately.
        Falls back to synchronous write if the background task is not running.
        """
        enriched = {
            "_logged_at": time.time(),
            **event,
        }

        if not self._running:
            # Safe fallback for non-async / test contexts
            self._sync_write(enriched)
            return

        depth = self._queue.qsize()
        if depth >= _QUEUE_WARN_DEPTH:
            log.warning(
                "AspenLogger queue depth %d >= %d — possible write stall",
                depth,
                _QUEUE_WARN_DEPTH,
            )

        self._queue.put_nowait(enriched)

    # ----------------------------------------------------------------------- #
    # Background writer loop                                                    #
    # ----------------------------------------------------------------------- #

    async def _writer_loop(self) -> None:
        """Consume the queue and write JSONL lines to disk."""
        with open(self.log_path, "a", encoding="utf-8", buffering=1) as fh:
            while True:
                try:
                    item = await self._queue.get()
                    if item is None:  # shutdown sentinel
                        # Drain any remaining items before exiting
                        while not self._queue.empty():
                            remaining = self._queue.get_nowait()
                            if remaining is not None:
                                self._write_line(fh, remaining)
                        break
                    self._write_line(fh, item)
                    self._queue.task_done()
                except Exception as exc:
                    log.exception("AspenLogger writer error: %s", exc)
                    self._dropped += 1

    def _write_line(self, fh: Any, event: Dict[str, Any]) -> None:
        try:
            fh.write(json.dumps(event, default=str) + "\n")
            self._written += 1
        except Exception as exc:
            log.error("AspenLogger failed to write event: %s", exc)
            self._dropped += 1

    def _sync_write(self, event: Dict[str, Any]) -> None:
        """Synchronous fallback write (non-async contexts only)."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
            self._written += 1
        except Exception as exc:
            log.error("AspenLogger sync fallback write failed: %s", exc)
            self._dropped += 1

    # ----------------------------------------------------------------------- #
    # Diagnostics                                                               #
    # ----------------------------------------------------------------------- #

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "written": self._written,
            "dropped": self._dropped,
            "queue_depth": self._queue.qsize(),
            "running": self._running,
            "log_path": str(self.log_path),
        }


# --------------------------------------------------------------------------- #
# Module-level singleton convenience (optional — use class directly if you     #
# need multiple loggers or custom paths)                                        #
# --------------------------------------------------------------------------- #
_default_logger: Optional[AspenLogger] = None


def get_default_logger(log_path: str = _DEFAULT_LOG_PATH) -> AspenLogger:
    global _default_logger
    if _default_logger is None:
        _default_logger = AspenLogger(log_path=log_path)
    return _default_logger
