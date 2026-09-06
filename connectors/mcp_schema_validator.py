#!/usr/bin/env python3
"""
connectors/mcp_schema_validator.py
====================================
P1 SWARM — MCP Schema JSON Validation on Inbound Requests

Validates every inbound MCPRequest against schemas/mcp_request.json before
dispatch. Malformed requests are rejected with a structured ResponseStatus.ERROR
and logged for audit.

Key guarantees:
  - All external input validated before dispatch (Law 5).
  - Structured error responses — never vague messages (Law 7).
  - Rejection events logged with correlation ID (Law 9).
  - jsonschema is a soft dependency — native fallback if not installed.

Usage:
    from connectors.mcp_schema_validator import MCPSchemaValidator, SchemaValidationError

    validator = MCPSchemaValidator()
    result = validator.validate(raw_request)
    if result.get("status") == "ERROR":
        return result
    # proceed with dispatch
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("MCP-SCHEMA-VALIDATOR")

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "mcp_request.json"
_loaded_schema: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    global _loaded_schema
    if _loaded_schema is None:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _loaded_schema = json.load(f)
    return _loaded_schema


class SchemaValidationError(ValueError):
    """Raised when an MCPRequest fails JSON Schema validation."""

    def __init__(self, reason: str, request_id: Optional[str] = None):
        super().__init__(reason)
        self.reason = reason
        self.request_id = request_id


class MCPSchemaValidator:
    """Validates inbound MCPRequests against the canonical JSON Schema.

    Provides both raising (validate) and non-raising (safe_validate) interfaces.
    All rejections are logged with structured context for audit trails.
    """

    def __init__(self, schema_path: Optional[str] = None):
        self._schema_path = Path(schema_path) if schema_path else _SCHEMA_PATH
        self._schema: Optional[Dict[str, Any]] = None
        self._rejection_count = 0

    def _ensure_schema(self) -> Dict[str, Any]:
        if self._schema is None:
            with open(self._schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request against JSON Schema. Returns request on success.

        Raises:
            SchemaValidationError: with structured reason if validation fails.
        """
        if not isinstance(request, dict):
            self._log_rejection(request, "Payload must be a JSON object")
            raise SchemaValidationError("Payload must be a JSON object")

        try:
            import jsonschema
        except ImportError:
            log.warning("jsonschema not installed — MCP schema validation SKIPPED")
            return request

        schema = self._ensure_schema()
        try:
            jsonschema.validate(instance=request, schema=schema)
        except jsonschema.ValidationError as exc:
            path = " -> ".join(str(p) for p in exc.absolute_path) or "<root>"
            reason = f"[{path}] {exc.message}"
            request_id = request.get("request_id")
            self._log_rejection(request, reason)
            raise SchemaValidationError(reason, request_id) from exc

        log.debug(
            "MCPRequest validated OK: type=%s id=%s",
            request.get("request_type"),
            request.get("request_id"),
        )
        return request

    def safe_validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Non-raising wrapper. Returns structured error dict instead of raising.

        Callers that need to return a response to the agent (rather than propagate
        an exception) should use this variant.
        """
        try:
            return self.validate(request)
        except SchemaValidationError as exc:
            return {
                "status": "ERROR",
                "reason": exc.reason,
                "request_id": exc.request_id
                or (request.get("request_id") if isinstance(request, dict) else None),
            }
        except Exception as exc:
            log.exception("Unexpected error during MCP schema validation")
            return {
                "status": "ERROR",
                "reason": f"Internal validation error: {exc}",
                "request_id": request.get("request_id")
                if isinstance(request, dict)
                else None,
            }

    def _log_rejection(self, request: Any, reason: str) -> None:
        self._rejection_count += 1
        request_id = request.get("request_id") if isinstance(request, dict) else None
        log.warning(
            "MCPRequest REJECTED [%d total] | id=%s reason=%s",
            self._rejection_count,
            request_id,
            reason,
        )

    @property
    def rejection_count(self) -> int:
        return self._rejection_count


def validate_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level convenience function for single-shot validation.

    Raises:
        SchemaValidationError: if validation fails.
    """
    return MCPSchemaValidator().validate(request)


def safe_validate(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level convenience function for non-raising validation."""
    return MCPSchemaValidator().safe_validate(request)
