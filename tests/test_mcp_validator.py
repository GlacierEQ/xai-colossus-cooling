#!/usr/bin/env python3
"""
tests/test_mcp_validator.py
===========================
Unit tests for Issue #17 — MCP Schema JSON Validation.

Runs without a live event loop; no external services required.
"""

import pytest
from apex_core.mcp_validator import validate_mcp_request, safe_validate, ValidationError


VALID_FORECAST = {
    "request_id": "123e4567-e89b-12d3-a456-426614174000",
    "request_type": "request_forecast",
    "source_agent": "CORE-THINK",
    "timestamp": "2026-05-28T23:00:00Z",
    "zone_id": "ZONE-A",
    "horizon_ticks": 12,
}

VALID_EMERGENCY = {
    "request_id": "223e4567-e89b-12d3-a456-426614174001",
    "request_type": "emergency_broadcast",
    "source_agent": "SUPERNOVA",
    "timestamp": "2026-05-28T23:01:00Z",
    "severity": "CRITICAL",
    "message": "Thermal runaway detected in ZONE-C",
}


class TestValidateMcpRequest:
    def test_valid_forecast_passes(self):
        result = validate_mcp_request(VALID_FORECAST)
        assert result is VALID_FORECAST

    def test_valid_emergency_passes(self):
        result = validate_mcp_request(VALID_EMERGENCY)
        assert result is VALID_EMERGENCY

    def test_missing_required_field_raises(self):
        bad = {**VALID_FORECAST}
        del bad["request_type"]
        with pytest.raises(ValidationError) as exc_info:
            validate_mcp_request(bad)
        assert "request_type" in exc_info.value.reason

    def test_invalid_request_type_raises(self):
        bad = {**VALID_FORECAST, "request_type": "hack_the_planet"}
        with pytest.raises(ValidationError):
            validate_mcp_request(bad)

    def test_emergency_missing_severity_raises(self):
        bad = {
            "request_id": "323e4567-e89b-12d3-a456-426614174002",
            "request_type": "emergency_broadcast",
            "source_agent": "GHOST",
            "timestamp": "2026-05-28T23:02:00Z",
            # missing severity and message
        }
        with pytest.raises(ValidationError):
            validate_mcp_request(bad)

    def test_horizon_ticks_out_of_range_raises(self):
        bad = {**VALID_FORECAST, "horizon_ticks": 999}
        with pytest.raises(ValidationError):
            validate_mcp_request(bad)


class TestSafeValidate:
    def test_valid_returns_original(self):
        result = safe_validate(VALID_FORECAST)
        assert result is VALID_FORECAST

    def test_invalid_returns_error_dict(self):
        bad = {"request_id": "abc", "source_agent": "X"}  # missing required fields
        result = safe_validate(bad)
        assert result["status"] == "ERROR"
        assert "reason" in result
        assert result["request_id"] == "abc"

    def test_error_dict_never_raises(self):
        """safe_validate must never propagate exceptions."""
        result = safe_validate(None)  # type: ignore — intentional bad input
        assert result["status"] == "ERROR"
