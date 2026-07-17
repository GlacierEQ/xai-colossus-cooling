#!/usr/bin/env python3
"""
apex_core/mcp_validator.py
==========================
Issue #17 — MCP Schema JSON Validation on Inbound Requests

Every MCPRequest MUST pass validate_mcp_request() before the MCP router
dispatches it to any agent. Malformed requests return a structured ERROR
response and are never silently dropped.

Usage:
    from apex_core.mcp_validator import validate_mcp_request, ValidationError

    result = validate_mcp_request(raw_dict)
    if result.get("status") == "ERROR":
        return result  # already structured for the caller
    # else proceed with dispatch
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("APEX-MCP-VALIDATOR")

# --------------------------------------------------------------------------- #
# Schema loading — resolved relative to this file so it works regardless of   #
# the working directory.                                                        #
# --------------------------------------------------------------------------- #
_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "mcp_request.json"
_SCHEMA: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    global _SCHEMA
    if _SCHEMA is None:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _SCHEMA = json.load(f)
    return _SCHEMA


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

class ValidationError(ValueError):
    """Raised when an MCPRequest fails schema validation."""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def validate_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate *request* against schemas/mcp_request.json.

    Returns:
        The original request dict if valid (pass-through for chaining).

    Raises:
        ValidationError: with a human-readable reason string if invalid.
    """
    try:
        import jsonschema  # soft dependency — only needed at validation time
    except ImportError:
        logger.warning(
            "jsonschema not installed — MCP validation SKIPPED. "
            "Add 'jsonschema>=4.0' to requirements.txt."
        )
        return request

    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(request), key=lambda e: list(e.path))

    if errors:
        primary = errors[0]
        path = " -> ".join(str(p) for p in primary.absolute_path) or "<root>"
        reason = f"[{path}] {primary.message}"
        if len(errors) > 1:
            reason += f" (+ {len(errors) - 1} more error(s))"
        logger.warning("MCPRequest validation FAILED: %s", reason)
        raise ValidationError(reason)

    logger.debug(
        "MCPRequest validated OK: type=%s id=%s",
        request.get("request_type"),
        request.get("request_id"),
    )
    return request


def safe_validate(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Non-raising wrapper. Returns a structured error dict instead of raising.

    Callers that need to return a response to the agent (rather than propagate
    an exception) should use this variant.

    Returns:
        Original request dict on success.
        {"status": "ERROR", "reason": "...", "request_id": ...} on failure.
    """
    try:
        return validate_mcp_request(request)
    except ValidationError as exc:
        return {
            "status": "ERROR",
            "reason": exc.reason,
            "request_id": request.get("request_id") if isinstance(request, dict) else None,
        }
    except Exception as exc:  # schema load failure, etc.
        logger.exception("Unexpected error during MCP validation")
        return {
            "status": "ERROR",
            "reason": f"Internal validation error: {exc}",
            "request_id": request.get("request_id") if isinstance(request, dict) else None,
        }
