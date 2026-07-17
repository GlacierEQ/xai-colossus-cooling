# Foundation choices — Colossus cooling

**Truth protocol.** No costume technologies.

## Stack in this repo

| Layer | Choice | Why |
|-------|--------|-----|
| Arrays | **NumPy** | SI heat/power balances, readable, demo-stable |
| Patterns | **sklearn** (where used) | Light sensor/pattern hooks — not a claim of production MLOps |
| Constants | Exact SI (e.g. Stefan–Boltzmann, g) | Challengeable numbers win interviews |
| Connectors | Zone telemetry / power bridges | Systems integration taste |

## Why not JAX (yet)

JAX shines for **autodiff + XLA** on GPU when you train/optimize against live telemetry residuals. This portfolio motion prioritizes **physics clarity and interviewability**.  

A future Omega strand (`colossus-autodiff-jax`) is only honest once real residual graphs exist here.

## Employer value

You get a **physics-first thermal motion** that plugs into AKOS governance and Swarm flippers — not a black-box vendor deck.
