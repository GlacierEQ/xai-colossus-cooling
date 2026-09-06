"""Inbound MCP request validator for the APEX router.

The router accepts two intentionally different wire shapes:
1. canonical APEX domain envelopes defined by ``mcp_request.json``; and
2. JSON-RPC 2.0 MCP calls used by direct tool clients.

A request must satisfy the contract for the shape it actually uses. Validation
never falls open because a dependency is missing.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

try:
    import jsonschema
except (
    ImportError
):  # pragma: no cover - exercised by fail-closed branch in minimal envs
    jsonschema = None


JSONRPC_METHODS = frozenset({"tools/call", "tools/list"})


class MCPRequestValidator:
    """Validate domain envelopes and JSON-RPC MCP requests before dispatch."""

    def __init__(self, schema_path: str | None = None):
        self.schema_path = schema_path or os.path.join(
            os.path.dirname(__file__), "mcp_request.json"
        )
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"MCP domain schema not found: {self.schema_path}")
        with open(self.schema_path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict) or not value:
            raise ValueError("MCP domain schema must be a non-empty JSON object")
        return value

    def validate(self, request_payload: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(request_payload, dict):
            return False, "Payload must be a JSON object"

        if "jsonrpc" in request_payload:
            return self._validate_jsonrpc(request_payload)
        if "request_type" in request_payload:
            return self._validate_domain(request_payload)
        return (
            False,
            "Payload is neither a canonical domain envelope nor JSON-RPC request",
        )

    def _validate_domain(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        if jsonschema is None:
            return False, "jsonschema dependency unavailable; domain request refused"
        try:
            validator = jsonschema.Draft7Validator(
                self.schema,
                format_checker=jsonschema.FormatChecker(),
            )
            errors = sorted(
                validator.iter_errors(payload), key=lambda error: list(error.path)
            )
        except Exception as exc:
            return False, f"Domain schema validation unavailable: {exc}"
        if errors:
            primary = errors[0]
            path = " -> ".join(str(part) for part in primary.absolute_path) or "<root>"
            return False, f"Schema validation error [{path}]: {primary.message}"
        return True, "VALIDATED"

    def _validate_jsonrpc(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        required = ("jsonrpc", "method", "id")
        for key in required:
            if key not in payload:
                return False, f"Missing required field: '{key}'"
        if payload["jsonrpc"] != "2.0":
            return False, "Field 'jsonrpc' must be exactly '2.0'"
        if not isinstance(payload["id"], (str, int)) or isinstance(payload["id"], bool):
            return False, "Field 'id' must be a string or integer"
        method = payload["method"]
        if not isinstance(method, str) or method not in JSONRPC_METHODS:
            return False, f"Unsupported JSON-RPC MCP method: {method!r}"

        allowed_keys = {"jsonrpc", "method", "id", "params"}
        unknown = sorted(set(payload) - allowed_keys)
        if unknown:
            return False, f"Unknown top-level field detected: '{unknown[0]}'"

        if "params" in payload:
            params = payload["params"]
            if not isinstance(params, dict):
                return False, "Field 'params' must be a JSON object"

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments", {})
                if not isinstance(name, str) or not name.strip():
                    return (
                        False,
                        "Field 'params.name' must be a non-empty string for tools/call",
                    )
                if not isinstance(arguments, dict):
                    return False, "Field 'params.arguments' must be a JSON object"
        return True, "VALIDATED"
