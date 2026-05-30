import json
import os
from typing import Dict, Any, Tuple

# Attempt to load standard jsonschema library, fallback to native if not present
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

class MCPRequestValidator:
    """
    Validates inbound MCPRequests against the strict jsonrpc schema.
    Guarantees structural validity prior to dispatcher ingestion.
    """
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.join(
            os.path.dirname(__file__), "mcp_request.json"
        )
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file."""
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                return json.load(f)
        return {}

    def validate(self, request_payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates the request payload.
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(request_payload, dict):
            return False, "Payload must be a JSON object"

        if HAS_JSONSCHEMA and self.schema:
            try:
                jsonschema.validate(instance=request_payload, schema=self.schema)
                return True, "VALIDATED"
            except jsonschema.ValidationError as e:
                return False, f"Schema validation error: {e.message}"
            except Exception as e:
                # If jsonschema fails for an unexpected reason, fall back to native
                pass
        
        # Robust native validation fallback
        return self._native_validation(request_payload)

    def _native_validation(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Fallback validation check to guarantee Zero-Crash performance."""
        # 1. Check required fields
        required_keys = ["jsonrpc", "method", "id"]
        for key in required_keys:
            if key not in payload:
                return False, f"Missing required field: '{key}'"

        # 2. Validate jsonrpc version
        if payload["jsonrpc"] != "2.0":
            return False, "Field 'jsonrpc' must be exactly '2.0'"

        # 3. Validate method type
        if not isinstance(payload["method"], str) or len(payload["method"].strip()) == 0:
            return False, "Field 'method' must be a non-empty string"

        # 4. Validate id type
        if not isinstance(payload["id"], (str, int)):
            return False, "Field 'id' must be a string or integer"

        # 5. Validate params block
        if "params" in payload:
            params = payload["params"]
            if not isinstance(params, dict):
                return False, "Field 'params' must be a JSON object"
            
            # Sub-properties inside params
            if "name" in params and not isinstance(params["name"], str):
                return False, "Field 'params.name' must be a string"
            if "arguments" in params and not isinstance(params["arguments"], dict):
                return False, "Field 'params.arguments' must be a JSON object"

        # 6. Reject unknown top-level keys
        allowed_keys = {"jsonrpc", "method", "id", "params"}
        for key in payload.keys():
            if key not in allowed_keys:
                return False, f"Unknown top-level field detected: '{key}'"

        return True, "VALIDATED"
