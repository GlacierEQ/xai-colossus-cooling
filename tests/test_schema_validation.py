"""tests/test_schema_validation.py

Issue #17 acceptance criteria:
  - valid request passes validation
  - malformed requests each return structured {status: ERROR, reason: ...}
  - validator loads src/schemas/mcp_request.json (JSON-RPC envelope)
  - rejection never silently drops — always structured error payload
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# ---------------------------------------------------------------------------
# Bootstrap: make src/ importable and point validator at correct schema path
# ---------------------------------------------------------------------------

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def _make_validator():
    """Build MCPRequestValidator pointed at src/schemas/mcp_request.json."""
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "schemas", "mcp_request.json"
    )
    from schemas.mcp_request_validator import MCPRequestValidator
    return MCPRequestValidator(schema_path=os.path.abspath(schema_path))


def _structured_error(validator, payload) -> dict:
    """Run validation and return a structured {status, reason} dict."""
    is_valid, msg = validator.validate(payload)
    if is_valid:
        return {"status": "SUCCESS", "reason": ""}
    return {"status": "ERROR", "reason": msg}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_tools_call_passes():
    v = _make_validator()
    req = {
        "jsonrpc": "2.0",
        "id": "req-001",
        "method": "tools/call",
        "params": {"name": "thermal_status", "arguments": {}},
    }
    result = _structured_error(v, req)
    assert result["status"] == "SUCCESS"


def test_valid_minimal_request_passes():
    """id + jsonrpc + method are the only required fields."""
    v = _make_validator()
    req = {"jsonrpc": "2.0", "id": 42, "method": "tools/call"}
    result = _structured_error(v, req)
    assert result["status"] == "SUCCESS"


def test_missing_jsonrpc_returns_error():
    v = _make_validator()
    result = _structured_error(v, {"id": "r-1", "method": "tools/call"})
    assert result["status"] == "ERROR"
    assert result["reason"]  # non-empty reason


def test_wrong_jsonrpc_version_returns_error():
    v = _make_validator()
    result = _structured_error(v, {"jsonrpc": "1.0", "id": "r-2", "method": "tools/call"})
    assert result["status"] == "ERROR"
    assert "2.0" in result["reason"] or result["reason"]


def test_missing_method_returns_error():
    v = _make_validator()
    result = _structured_error(v, {"jsonrpc": "2.0", "id": "r-3"})
    assert result["status"] == "ERROR"


def test_missing_id_returns_error():
    v = _make_validator()
    result = _structured_error(v, {"jsonrpc": "2.0", "method": "tools/call"})
    assert result["status"] == "ERROR"


def test_unknown_top_level_field_returns_error():
    """additionalProperties:false in schema must reject unknown fields."""
    v = _make_validator()
    result = _structured_error(v, {
        "jsonrpc": "2.0",
        "id": "r-4",
        "method": "tools/call",
        "EVIL_FIELD": "injected",
    })
    assert result["status"] == "ERROR"


def test_params_name_not_string_returns_error():
    v = _make_validator()
    result = _structured_error(v, {
        "jsonrpc": "2.0",
        "id": "r-5",
        "method": "tools/call",
        "params": {"name": 999, "arguments": {}},
    })
    assert result["status"] == "ERROR"


def test_rejection_never_silent():
    """Every failure path must return a non-empty reason string."""
    v = _make_validator()
    bad_cases = [
        {},
        {"jsonrpc": "2.0"},
        {"method": "tools/call"},
        {"jsonrpc": "1.1", "id": 1, "method": "x"},
        "not a dict",
        None,
    ]
    for case in bad_cases:
        result = _structured_error(v, case)
        assert result["status"] == "ERROR", f"Expected ERROR for: {case}"
        assert result["reason"], f"Empty reason for: {case}"
