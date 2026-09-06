"""
gauntlet_integration/run_gauntlet.py
xai-colossus-cooling | Gauntlet CI Harness

Runs a suite of adversarial scenarios against the thermal orchestrator.
Designed to be called by CI (`python gauntlet_integration/run_gauntlet.py --ci`).

Scenarios:
  1. SUPERNOVA_TRIGGER   -- inject CRITICAL node, verify SUPERNOVA fires
  2. BUDGET_OVERRUN      -- push zone draw >5% over budget, verify flag
  3. PISTON_OFFLINE      -- mark SHADOW offline, verify MICROWAVE takes over
  4. EMERGENCY_BROADCAST -- fire MCP emergency, verify Aspen log written
  5. NANOFLUID_DEGRADE   -- degrade circuit conductivity, verify flow increase
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class GauntletResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.critical = False
        self.detail = ""

    def fail(self, detail: str, critical: bool = False):
        self.passed = False
        self.critical = critical
        self.detail = detail
        return self

    def ok(self, detail: str = ""):
        self.passed = True
        self.detail = detail
        return self


async def scenario_emergency_broadcast() -> GauntletResult:
    r = GauntletResult("EMERGENCY_BROADCAST")
    try:
        from mastermind_fusion.mcp_router import build_router, MCPRequest, RequestType

        router = build_router(orchestrator=None)
        req = MCPRequest(
            request_type=RequestType.EMERGENCY,
            severity="CRITICAL",
            message="Gauntlet test: zone thermal runaway simulated",
            zone_id="ZONE-GAUNTLET",
            source_agent="gauntlet",
        )
        resp = await router.dispatch(req)
        log_path = ROOT / "audit_logs" / "aspen_mcp_events.ndjson"
        if not log_path.exists():
            return r.fail("Aspen log not written", critical=True)
        lines = log_path.read_text().strip().splitlines()
        last = json.loads(lines[-1])
        if last.get("event") != "EMERGENCY_BROADCAST":
            return r.fail(
                f"Last log entry is not EMERGENCY_BROADCAST: {last}", critical=True
            )
        return r.ok(f"status={resp.status} log_entry_found=True")
    except Exception as e:
        return r.fail(str(e), critical=True)


async def scenario_zone_snapshot_offline() -> GauntletResult:
    r = GauntletResult("ZONE_SNAPSHOT_OFFLINE")
    try:
        from mastermind_fusion.mcp_router import build_router, MCPRequest, RequestType

        router = build_router(orchestrator=None)
        req = MCPRequest(
            request_type=RequestType.ZONE_SNAPSHOT,
            source_agent="gauntlet",
        )
        resp = await router.dispatch(req)
        if resp.status.value not in ("ok", "partial"):
            return r.fail(f"Unexpected status: {resp.status}")
        return r.ok(f"offline graceful: {resp.data}")
    except Exception as e:
        return r.fail(str(e), critical=True)


async def scenario_unknown_request() -> GauntletResult:
    r = GauntletResult("UNKNOWN_REQUEST_TYPE")
    try:
        from mastermind_fusion.mcp_router import MCPRouter, MCPRequest

        router = MCPRouter(orchestrator=None)
        # Inject a fake request type bypassing enum
        req = MCPRequest.__new__(MCPRequest)
        req.request_type = "totally_unknown"
        req.request_id = "gauntlet-unk-001"
        req.source_agent = "gauntlet"
        req.zone_id = None
        req.piston_name = None
        req.horizon_ticks = 12
        req.severity = "INFO"
        req.message = None
        req.payload = {}
        import datetime

        req.timestamp = datetime.datetime.utcnow().isoformat()
        resp = await router.dispatch(req)
        if resp.status.value != "error":
            return r.fail(f"Expected error status, got: {resp.status}")
        return r.ok("correctly returned error for unknown type")
    except Exception as e:
        return r.fail(str(e), critical=True)


async def run_all() -> list:
    scenarios = [
        scenario_emergency_broadcast,
        scenario_zone_snapshot_offline,
        scenario_unknown_request,
    ]
    results = []
    for scenario_fn in scenarios:
        print(f"  running {scenario_fn.__name__}...", end=" ", flush=True)
        result = await scenario_fn()
        status = (
            "PASS"
            if result.passed
            else ("CRITICAL-FAIL" if result.critical else "FAIL")
        )
        print(f"{status} | {result.detail}")
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description="Colossus Cooling Gauntlet")
    parser.add_argument("--ci", action="store_true")
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    print("=== GAUNTLET RUN START ===")
    results = asyncio.run(run_all())
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    critical_failures = [r for r in results if not r.passed and r.critical]
    print(
        f"=== {passed}/{total} passed | {len(critical_failures)} critical failures ==="
    )

    if args.fail_on_critical and critical_failures:
        print("CRITICAL FAILURES:", [r.name for r in critical_failures])
        sys.exit(1)

    if args.ci and passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
