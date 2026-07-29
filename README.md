# xAI Colossus Cooling — Polyglot Thermal Management Suite 🌊

> **gRPC + Protobuf schema, C++ thermal solver, TypeScript dashboard, and SQL persistence for GPU cooling.**

[![Protobuf](https://img.shields.io/badge/Protobuf-3.0+-blue)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6)]()
[![SQL](https://img.shields.io/badge/SQL-PostgreSQL-blue)]()
[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![Domain](https://img.shields.io/badge/Domain-Thermal%20Management-cyan)]()

---

## 🎯 For Recruiters & Hiring Managers

This repository implements the **xAI Colossus Polyglot Cooling Suite** — coordinating thermal management across 100,000+ GPUs using gRPC/Protobuf RPCs, TypeScript frontends, and SQL persistent storage. It demonstrates:

- **Protobuf IDL definitions** (`colossus_cooling.proto`) defining zero-copy thermal telemetry schemas
- **TypeScript dashboard components** rendering real-time thermal heatmaps
- **PostgreSQL schema** tracking historical cooling efficiency and PUE targets
- **Python control loops** tuning liquid flow rates based on GPU load predictions

**Why this matters**: Enterprise thermal management requires polyglot architectures where fast gRPC binary schemas link real-time sensors to analytical databases and web dashboards.

---

## 🔬 For Engineers & Technical Reviewers

### Core Components

| Component | Language | Purpose |
|---|---|---|
| `proto/colossus_cooling.proto` | Protobuf | Binary IDL for thermal sensor & flow control RPCs |
| `src/components/` | TSX/CSS | Real-time thermal heatmap UI components |
| `src/schema.sql` | SQL | PostgreSQL tables for thermal log persistence |
| `src/cooling_suite.py` | Python | Thermal control loop & gRPC server harness |

---

## 🤖 ML/AI & Programmatic Mesh Integration

- **MCP Tool**: `cooling_suite_status()` — thermal queryable by swarm agents
- **Mastermind Sidecar**: Integrated with APEX Highway mesh
- **SHA-256 Integrity**: Tracked in `.integrity/file_hashes.json`

---

## ⚡ Quick Start

```bash
python3 src/cooling_suite.py
```
