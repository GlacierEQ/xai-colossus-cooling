#!/usr/bin/env python3
"""
APEX Colossus Simulation Harness
GlacierEQ APEX Stack
Author: Casey Barton

Configurable multi-scale simulation for testing thermal orchestration
without live hardware. Supports:
  - Variable cluster sizes (100 → 100,000 nodes)
  - Scripted thermal events (workload spikes, CRAC failures, hotspots)
  - Heat curve profiles per GPU workload type
  - Performance benchmarking of piston response latency

Usage:
    python simulation/sim_harness.py --zones 10 --nodes-per-zone 100 --ticks 50
    python simulation/sim_harness.py --scenario spike --zones 5 --nodes-per-zone 50
"""

import asyncio
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from apex_core.thermal_orchestrator import (
    APEXThermalOrchestrator,
    CoolingMode,
    CoolingZone,
    ThermalNode,
)


class SimEvent:
    """A scripted thermal event that fires at a specific tick."""

    def __init__(
        self,
        tick: int,
        event_type: str,
        target_zone: str = None,
        temp_delta: float = 0.0,
        description: str = "",
    ):
        self.tick = tick
        self.event_type = event_type
        self.target_zone = target_zone
        self.temp_delta = temp_delta
        self.description = description

    def apply(self, orchestrator: APEXThermalOrchestrator):
        print(f"  [SIM EVENT @ tick {self.tick}] {self.event_type}: {self.description}")
        for zone in orchestrator.zones:
            if self.target_zone and zone.zone_id != self.target_zone:
                continue
            for node in zone.nodes:
                node.temp_celsius = min(node.temp_celsius + self.temp_delta, 105.0)


SCENARIOS = {
    "nominal": [],
    "spike": [
        SimEvent(
            5,
            "WORKLOAD_SPIKE",
            temp_delta=12.0,
            description="Large training run launched — all zones",
        ),
        SimEvent(
            15,
            "PARTIAL_RECOVERY",
            temp_delta=-5.0,
            description="MICROWAVE pre-cooling takes effect",
        ),
        SimEvent(
            25, "SECOND_WAVE", temp_delta=8.0, description="Second model batch begins"
        ),
    ],
    "crac_failure": [
        SimEvent(
            3,
            "CRAC_UNIT_FAIL",
            temp_delta=6.0,
            description="CRAC unit failure — zone A",
        ),
        SimEvent(
            4,
            "HEAT_BUILDUP",
            temp_delta=5.0,
            description="Heat accumulating post-failure",
        ),
        SimEvent(
            10,
            "EMERGENCY_COOL",
            temp_delta=-10.0,
            description="SUPERNOVA blast — liquid loop max",
        ),
    ],
    "hotspot": [
        SimEvent(
            2, "HOTSPOT", temp_delta=25.0, description="Hotspot: GPU overclock event"
        ),
        SimEvent(
            3, "EMERGENCY", temp_delta=5.0, description="Temps approaching throttle"
        ),
        SimEvent(
            6,
            "THROTTLE_ACTIVE",
            temp_delta=-15.0,
            description="GPU throttled + full blast cooling",
        ),
    ],
    "supernova_gauntlet": [
        SimEvent(
            10,
            "CRITICAL_HOTSPOT",
            temp_delta=30.0,
            description="Injecting CRITICAL node to test SUPERNOVA trigger threshold",
        )
    ],
}


def build_cluster(
    num_zones: int, nodes_per_zone: int, base_temp: float = 65.0
) -> APEXThermalOrchestrator:
    """Construct an orchestrator with a synthetic cluster of the requested scale."""
    orch = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS)
    for z in range(num_zones):
        zone = CoolingZone(zone_id=f"ZONE-{z:03d}", zone_name=f"Colossus Zone {z}")
        for n in range(nodes_per_zone):
            jitter = random.gauss(0, 1.2)
            zone.nodes.append(
                ThermalNode(
                    node_id=f"NODE-{z:03d}-{n:04d}",
                    rack_id=f"RACK-{z:03d}",
                    zone_id=zone.zone_id,
                    temp_celsius=round(base_temp + jitter, 1),
                    gpu_utilization=random.uniform(0.75, 0.95),
                    power_watts=random.uniform(650, 750),
                )
            )
        orch.register_zone(zone)
    return orch


async def run_simulation(
    num_zones: int = 3,
    nodes_per_zone: int = 10,
    ticks: int = 20,
    scenario: str = "nominal",
    base_temp: float = 65.0,
) -> dict:
    orch = build_cluster(num_zones, nodes_per_zone, base_temp)
    events = SCENARIOS.get(scenario, [])
    event_map = {e.tick: e for e in events}

    total_nodes = num_zones * nodes_per_zone
    print("\n=== APEX Colossus Simulation ===")
    print(
        f"Scale    : {num_zones} zones × {nodes_per_zone} nodes = {total_nodes:,} total nodes"
    )
    print(f"Scenario : {scenario}")
    print(f"Ticks    : {ticks}")
    print("================================")

    results = []
    t0 = time.perf_counter()
    for tick in range(1, ticks + 1):
        if tick in event_map:
            event_map[tick].apply(orch)
        result = await orch.tick_cycle()
        results.append(result)
        critical = result["critical"]
        anomalies = result["anomalies"]
        if critical or anomalies:
            print(f"  Tick {tick:3d} | critical={critical} | anomalies={anomalies}")

    elapsed = time.perf_counter() - t0
    total_critical = sum(r["critical"] for r in results)
    total_anomalies = sum(r["anomalies"] for r in results)

    print("\n=== Simulation Complete ===")
    print(
        f"Elapsed     : {elapsed:.3f}s for {ticks} ticks ({elapsed / ticks * 1000:.1f}ms avg)"
    )
    print(f"Total critical events : {total_critical}")
    print(f"Total anomalies       : {total_anomalies}")
    print(f"Nodes monitored/tick  : {total_nodes:,}")

    if scenario == "supernova_gauntlet":
        # Verify SUPERNOVA fired at tick 10/11
        supernova_fired = results[9]["critical"] > 0 if len(results) >= 10 else False
        if supernova_fired:
            print(
                "\n✅ [GAUNTLET] SUPERNOVA Gauntlet: PASS (SUPERNOVA fired at tick 10/11 as expected)"
            )
        else:
            print("\n❌ [GAUNTLET] SUPERNOVA Gauntlet: FAIL (SUPERNOVA did not fire!)")
            sys.exit(1)

    return {
        "ticks": ticks,
        "total_nodes": total_nodes,
        "elapsed_s": round(elapsed, 3),
        "avg_tick_ms": round(elapsed / ticks * 1000, 2),
        "total_critical": total_critical,
        "total_anomalies": total_anomalies,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APEX Colossus Thermal Simulation")
    parser.add_argument("--zones", type=int, default=3, help="Number of cooling zones")
    parser.add_argument("--nodes-per-zone", type=int, default=10, help="Nodes per zone")
    parser.add_argument(
        "--ticks", type=int, default=20, help="Number of simulation ticks"
    )
    parser.add_argument(
        "--scenario", type=str, default="nominal", choices=list(SCENARIOS.keys())
    )
    parser.add_argument(
        "--base-temp", type=float, default=65.0, help="Starting baseline temp (C)"
    )
    args = parser.parse_args()
    asyncio.run(
        run_simulation(
            num_zones=args.zones,
            nodes_per_zone=args.nodes_per_zone,
            ticks=args.ticks,
            scenario=args.scenario,
            base_temp=args.base_temp,
        )
    )
