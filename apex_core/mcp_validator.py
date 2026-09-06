#!/usr/bin/env python3
"""Canonical domain-envelope validation for APEX MCP swarm requests.

Every domain request must satisfy ``schemas/mcp_request.json`` before dispatch.
Validation is a correctness boundary, not an optional enhancement: if the schema
engine or schema itself is unavailable, the request is refused.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("APEX-MCP-VALIDATOR")
_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "mcp_request.json"
_SCHEMA: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    global _SCHEMA
    if _SCHEMA is None:
        try:
            with open(_SCHEMA_PATH, "r", encoding="utf-8") as handle:
                value = json.load(handle)
        except Exception as exc:
            raise ValidationError(f"schema unavailable: {exc}") from exc
        if not isinstance(value, dict) or not value:
            raise ValidationError("schema unavailable: empty or invalid schema")
        _SCHEMA = value
    return _SCHEMA


class ValidationError(ValueError):
    """Raised when an MCP domain request cannot be proven valid."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def validate_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a canonical domain request and return the original dict."""
    if not isinstance(request, dict):
        raise ValidationError("[<root>] request must be a JSON object")

    try:
        import jsonschema
    except ImportError as exc:
        raise ValidationError("jsonschema dependency unavailable") from exc

    schema = _load_schema()
    validator = jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(request), key=lambda error: list(error.path))
    if errors:
        primary = errors[0]
        path = " -> ".join(str(part) for part in primary.absolute_path) or "<root>"
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
    """Return a structured error receipt instead of propagating validation failure."""
    try:
        return validate_mcp_request(request)
    except ValidationError as exc:
        return {
            "status": "ERROR",
            "reason": exc.reason,
            "request_id": request.get("request_id")
            if isinstance(request, dict)
            else None,
        }
    except Exception as exc:
        logger.exception("Unexpected error during MCP validation")
        return {
            "status": "ERROR",
            "reason": f"Internal validation error: {exc}",
            "request_id": request.get("request_id")
            if isinstance(request, dict)
            else None,
        }
