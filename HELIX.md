# 🔱 Double Helix: xAI Colossus Cooling

> Alpha (What) + Omega (How) = Autonomous thermal management for 1.5GW, 200k-GPU supercomputer.

```
BINDING: DOUBLE_HELIX:COLOSSUS_COOLING v1.0
PAIR:    Alpha (thermal physics) ←→ Omega (orchestration + CI)
MANTRA:  Two strands. One autonomous cooling DNA.
```

## 🧬 Alpha Strand (What — Domain Logic)

The physics-first thermal management system.

### Core Files
| File | Purpose |
|------|---------|
| `thermal/pinn_digital_twin.py` | Physics-Informed Neural Network for thermal validation |
| `thermal/immersion_engine.py` | 100-tank immersion cooling control |
| `thermal/cascade_shield.py` | Cascade failure prevention |
| `thermal/predictive_dispatch.py` | Predictive thermal dispatch |
| `physics/constants.py` | Shared physics (Maxwell, Hamilton-Crosser, PARTICLE_DATABASE) |

### Alpha Contract
```python
class ThermalSubsystem:
    """Every thermal module MUST expose tick() + summary()"""
    async def tick(self, zones: Dict, tick_num: int) -> Dict[str, Any]:
        return {"anomalies": [...], "actions": [...]}
    
    def summary(self) -> Dict[str, Any]:
        return {"status": "...", "metrics": {...}}
```

## 🌀 Omega Strand (How — Orchestration)

The operational intelligence layer.

### Core Files
| File | Purpose |
|------|---------|
| `core/colossus_orchestrator.py` | Central brain, tick-driven 500ms |
| `api/gateway.py` | REST gateway (16+ endpoints) |
| `connectors/mcp_bridge.py` | MCP bridge (10 tools) |
| `memory/aspen_bridge.py` | Aspen Grove 4-tier persistence |
| `cli/colossus_cli.py` | CLI (12 commands) |

### Omega Contract
```python
class Orchestrator:
    """Omega orchestrates Alpha subsystems"""
    async def run(self, duration_ticks: int = 100):
        for tick in range(duration_ticks):
            for subsystem in self.subsystems:
                result = await subsystem.tick(self.zones, tick)
                self.process_anomalies(result)
            await asyncio.sleep(0.5)  # 500ms tick
```

## 🔄 Helix Interlock

Alpha and Omega communicate through:
1. **Subsystem Interface** — `tick() → {anomalies, actions}`
2. **TelemetryBus** — Universal event bus (UUID events, max_buffer=10000)
3. **Circuit Breaker** — 3-strike zone isolation with countdown recovery
4. **Fusion Modes** — COLOSSUS_FULL, EMERGENCY_RESPONSE, PREDICTIVE_COOLING, GHOST_OPTIMIZATION

## 📊 Pro-Code Binding

| Gate | Status |
|------|--------|
| Naming (snake_case, prefixes) | ✅ |
| Architecture (subsystem contract) | ✅ |
| Failure handling (circuit breaker) | ✅ |
| Maintainability (4-tier memory) | ✅ |
| Authenticity (physics-first) | ✅ |
| Observability (TelemetryBus) | ✅ |
| Documentation (AGENTS.md) | ✅ |

## 🎯 Job Application Angle

This repo demonstrates:
- **Systems thinking** — 8 subsystems with clean interfaces
- **Physics literacy** — PINN, Maxwell, Hamilton-Crosser models
- **Production engineering** — Circuit breakers, telemetry, graceful degradation
- **AI integration** — MCP bridge, predictive dispatch, digital twin
- **Scale awareness** — 1.5GW, 200k GPUs, 12500 racks
