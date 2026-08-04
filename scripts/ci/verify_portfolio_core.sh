#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=".verification-artifacts"
BLUEPRINT_BASE="${ARTIFACT_DIR}/CCL-002-core"
mkdir -p "${ARTIFACT_DIR}"

python -m pip install --disable-pip-version-check \
  pytest \
  pytest-asyncio \
  ezdxf \
  matplotlib

python -m compileall -q \
  apex_cli.py \
  omega/apex_cli.py \
  apex_core \
  cells \
  src/thermal_sentinel.py

python -m pytest \
  tests/test_portfolio_truth_surface.py \
  tests/test_thermal_core.py \
  -q \
  | tee "${ARTIFACT_DIR}/pytest-core.txt"

python apex_cli.py status \
  | tee "${ARTIFACT_DIR}/cli-status.txt"

python apex_cli.py blueprint \
  --all \
  --output "${BLUEPRINT_BASE}" \
  | tee "${ARTIFACT_DIR}/blueprint-generation.txt"

python - <<'PY'
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

artifact_dir = Path(".verification-artifacts")
expected = [
    artifact_dir / "CCL-002-core.dxf",
    artifact_dir / "CCL-002-core.pdf",
    artifact_dir / "CCL-002-core.svg",
    artifact_dir / "CCL-002-core.png",
]

files = []
for path in expected:
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit(f"Missing or empty blueprint artifact: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    files.append(
        {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": digest,
        }
    )

receipt = {
    "schema": "glaciereq.cooling.portfolio-core-receipt.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "repository": os.environ.get("GITHUB_REPOSITORY", "GlacierEQ/xai-colossus-cooling"),
    "commit": os.environ.get("GITHUB_SHA", "local"),
    "ref": os.environ.get("GITHUB_REF", "local"),
    "python": platform.python_version(),
    "evidence_state": "BOUNDED_CORE_TEST_VERIFIED",
    "verified": {
        "test_files": [
            "tests/test_portfolio_truth_surface.py",
            "tests/test_thermal_core.py",
        ],
        "expected_positive_count": 37,
        "root_cli_status": True,
        "blueprint_generation": True,
        "blueprint_artifacts": files,
    },
    "not_verified": [
        "complete repository test estate",
        "external provider connectivity",
        "real GPU telemetry",
        "cooling hardware control",
        "production deployment",
        "hyperscale performance",
        "PUE, latency, availability, or cost outcomes",
    ],
}

(artifact_dir / "portfolio-core-receipt.json").write_text(
    json.dumps(receipt, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, indent=2))
PY
