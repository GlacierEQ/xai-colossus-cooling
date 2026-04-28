# Aspen Grove v7 Integration

## Purpose

Aspen Grove is the memory and audit backbone for the Colossus Cooling stack.

It should record thermal events, anomaly patterns, piston activations, forecast outputs, and deployment history without replacing the core orchestrator.

## Design rule

Aspen Grove is an **attached intelligence spine**, not the orchestrator itself.

- keep the thermal orchestrator as the runtime control loop
- attach Aspen Grove as the memory, correlation, and audit layer
- use Aspen Grove to improve prediction, retrieval, and post-run analysis
- never let Aspen Grove erase required telemetry, tests, or safety checks

## Sink topology

### Sink 1 — Mem0
Use for:
- short-term thermal patterns
- recent anomaly clusters
- short rolling recommendation buffers

### Sink 2 — SuperMemory
Use for:
- longer thermal evolution history
- datacenter behavioral summaries
- cooling-pattern retrospectives

### Sink 3 — Neo4j
Use for:
- thermal correlation graphs
- rack-to-zone relationships
- anomaly propagation paths
- piston effectiveness relationships

### Sink 4 — Pinecone
Use for:
- anomaly vector retrieval
- semantic similarity across thermal incidents
- forecast analog lookup

### Sink 5 — Supabase
Use for:
- durable telemetry persistence
- append-only event tables
- anomaly and piston logs
- emergency cooling events

## Aspen event model

Each major runtime event should be serializable as a structured object.

```json
{
  "event_id": "evt_thermal_2026_04_28_001",
  "event_type": "thermal_forecast_generated",
  "ts": "2026-04-28T12:00:00Z",
  "zone": "zone_a",
  "rack": "rack_17",
  "current_temp_c": 71.2,
  "predicted_temp_c": 78.4,
  "recommended_piston": "MICROWAVE",
  "confidence": 0.84,
  "source": "CORE-THINK",
  "audit_tags": ["forecast", "predictive", "aspen_v7"]
}
```

## Recommended integration points

### 1. Thermal orchestrator hook
Trigger Aspen writes after:
- zone thermal computation
- anomaly detection
- forecast generation
- piston selection
- emergency event activation

### 2. MotherDuck analytics hook
Use Aspen summaries to enrich:
- hot zone trend analysis
- PUE trend interpretation
- repeated anomaly clustering
- cross-window comparison

### 3. Supabase telemetry hook
Persist:
- raw event log
- anomaly log
- piston log
- emergency log
- forecast log

### 4. GitHub / CI hook
Capture:
- deployment commit SHA
- config version
- thermal model version
- schema version
- audit artifact link

## Runtime separation

### Core runtime
Owns:
- temperature reads
- thermal computation
- safety thresholds
- cooling actions

### Aspen Grove
Owns:
- memory
- retrieval
- correlation
- forecast context
- audit history

## Minimum tables

### `colossus_thermal_events`
- event_id
- ts
- zone
- rack
- temp_c
- power_watts
- status
- source

### `colossus_forecasts`
- forecast_id
- ts
- zone
- current_temp_c
- predicted_temp_c
- confidence
- recommended_piston
- model_version

### `colossus_anomalies`
- anomaly_id
- ts
- zone
- severity
- description
- vector_ref
- graph_ref

### `colossus_piston_log`
- piston_event_id
- ts
- piston_name
- trigger_reason
- effectiveness_score
- zone

### `colossus_emergency_log`
- emergency_id
- ts
- zone
- threshold_crossed
- response_mode
- resolved_ts

## Strength-preservation rules

1. Do not replace the orchestrator with Aspen Grove.
2. Do not remove existing thermal tests when adding memory sinks.
3. Do not let memory hooks block emergency cooling paths.
4. Keep Aspen writes async or buffered where possible.
5. Log every forecast and piston recommendation with version info.
6. Keep Supabase as the durable audit sink even when other memory layers are active.

## Success criteria

- Aspen improves recall and forecasting without slowing control loops.
- Forecast events are auditable.
- Piston recommendations are explainable.
- Security fixes remain intact.
- Repo stays mergeable and testable.
