"""tests/test_schema_validation.py

Issue #17 acceptance criteria + audit gap coverage:
  - valid request passes validation
  - malformed requests each return structured {status: ERROR, reason: ...}
  - validator loads src/schemas/mcp_request.json (JSON-RPC envelope)
  - rejection never silently drops — always structured error payload
  - id=null rejected (audit gap #1)
  - params.arguments not object rejected (audit gap #2)
"""

import pytest
import sys
import os

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def _make_validator():
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "schemas", "mcp_request.json"
    )
    from schemas.mcp_request_validator import MCPRequestValidator
    return MCPRequestValidator(schema_path=os.path.abspath(schema_path))


def _result(validator, payload) -> dict:
    is_valid, msg = validator.validate(payload)
    if is_valid:
        return {"status": "SUCCESS", "reason": ""}
    return {"status": "ERROR", "reason": msg}


# ── Happy paths ─────────────────────────────────────────────────────────────

def test_valid_tools_call_passes():
    v = _make_validator()
    result = _result(v, {
        "jsonrpc": "2.0",
        "id": "req-001",
        "method": "tools/call",
        "params": {"name": "thermal_status", "arguments": {}},
    })
    assert result["status"] == "SUCCESS"


def test_valid_minimal_request_passes():
    v = _make_validator()
    result = _result(v, {"jsonrpc": "2.0", "id": 42, "method": "tools/call"})
    assert result["status"] == "SUCCESS"


def test_integer_id_passes():
    v = _make_validator()
    result = _result(v, {"jsonrpc": "2.0", "id": 1, "method": "tools/call"})
    assert result["status"] == "SUCCESS"


# ── Required field failures ──────────────────────────────────────────────────

def test_missing_jsonrpc_returns_error():
    v = _make_validator()
    result = _result(v, {"id": "r-1", "method": "tools/call"})
    assert result["status"] == "ERROR"
    assert result["reason"]


def test_wrong_jsonrpc_version_returns_error():
    v = _make_validator()
    result = _result(v, {"jsonrpc": "1.0", "id": "r-2", "method": "tools/call"})
    assert result["status"] == "ERROR"


def test_missing_method_returns_error():
    v = _make_validator()
    result = _result(v, {"jsonrpc": "2.0", "id": "r-3"})
    assert result["status"] == "ERROR"


def test_missing_id_returns_error():
    v = _make_validator()
    result = _result(v, {"jsonrpc": "2.0", "method": "tools/call"})
    assert result["status"] == "ERROR"


# ── Type / value failures ────────────────────────────────────────────────────

def test_null_id_returns_error():
    """Audit gap #1: id=null must be rejected (id must be string or integer)."""
    v = _make_validator()
    result = _result(v, {"jsonrpc": "2.0", "id": None, "method": "tools/call"})
    assert result["status"] == "ERROR"


def test_unknown_top_level_field_returns_error():
    v = _make_validator()
    result = _result(v, {
        "jsonrpc": "2.0", "id": "r-4", "method": "tools/call",
        "EVIL_FIELD": "injected",
    })
    assert result["status"] == "ERROR"


def test_params_name_not_string_returns_error():
    v = _make_validator()
    result = _result(v, {
        "jsonrpc": "2.0", "id": "r-5", "method": "tools/call",
        "params": {"name": 999, "arguments": {}},
    })
    assert result["status"] == "ERROR"


def test_params_arguments_not_object_returns_error():
    """Audit gap #2: params.arguments must be an object, not a string/list."""
    v = _make_validator()
    result = _result(v, {
        "jsonrpc": "2.0", "id": "r-6", "method": "tools/call",
        "params": {"name": "thermal_status", "arguments": "not-an-object"},
    })
    assert result["status"] == "ERROR"


# ── Never-silent guarantee ───────────────────────────────────────────────────

def test_rejection_never_silent():
    """Every failure path must return a non-empty reason string."""
    v = _make_validator()
    bad_cases = [
        {},
        {"jsonrpc": "2.0"},
        {"method": "tools/call"},
        {"jsonrpc": "1.1", "id": 1, "method": "x"},
        {"jsonrpc": "2.0", "id": None, "method": "tools/call"},
        "not a dict",
        None,
    ]
    for case in bad_cases:
        result = _result(v, case)
        assert result["status"] == "ERROR", f"Expected ERROR for: {case}"
        assert result["reason"], f"Empty reason for: {case}"
