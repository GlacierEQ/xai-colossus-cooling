from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


REQUIRED_PATHS = (
    "apex_core/thermal_orchestrator.py",
    "cells/rack_cell.py",
    "src/thermal_sentinel.py",
    "omega/apex_cli.py",
    "apex_cli.py",
    "tests/test_thermal_core.py",
    "requirements.txt",
)

FORBIDDEN_STALE_CLAIMS = (
    "coordinating thermal management across 100,000+ GPUs",
    "zero-copy thermal telemetry schemas",
    "Integrated with APEX Highway mesh",
    "src/cooling_suite.py",
    "proto/colossus_cooling.proto",
    "src/schema.sql",
)


def test_readme_points_only_to_present_core_paths() -> None:
    text = README.read_text(encoding="utf-8")

    for relative_path in REQUIRED_PATHS:
        assert (ROOT / relative_path).exists(), relative_path
        assert relative_path in text


def test_root_cli_is_a_thin_delegating_entrypoint() -> None:
    root_cli = (ROOT / "apex_cli.py").read_text(encoding="utf-8")

    assert "from omega.apex_cli import main" in root_cli
    assert "main()" in root_cli


def test_readme_preserves_non_affiliation_and_simulation_boundary() -> None:
    text = README.read_text(encoding="utf-8")

    assert "not affiliated with xAI" in text
    assert "not evidence of deployment" in text
    assert "heuristic proxy" in text
    assert "not a trained LSTM model" in text
    assert "100,000-GPU or hyperscale operation" in text
    assert "Scenario language only; not verified" in text


def test_stale_claims_and_nonexistent_paths_do_not_return() -> None:
    text = README.read_text(encoding="utf-8")

    for stale_claim in FORBIDDEN_STALE_CLAIMS:
        assert stale_claim not in text


def test_status_command_is_not_misrepresented_as_live_health() -> None:
    text = README.read_text(encoding="utf-8")

    assert "python apex_cli.py status" in text
    assert "not** a live service-health check" in text
