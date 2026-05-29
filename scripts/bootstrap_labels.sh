#!/usr/bin/env bash
# scripts/bootstrap_labels.sh
# Creates the canonical xai-colossus-cooling GitHub Issues label taxonomy.
# Run once: bash scripts/bootstrap_labels.sh
# Requires: gh CLI authenticated to GlacierEQ/xai-colossus-cooling

set -euo pipefail
REPO="GlacierEQ/xai-colossus-cooling"

create_label() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force
  echo "  ✓ $name"
}

echo "Bootstrapping label taxonomy for $REPO..."

# === Priority / Gate ===
create_label "P0_GATE"    "B60205" "Hard deployment gate — human sign-off required, Mentat cannot close"
create_label "P1_SWARM"   "E4E669" "Swarm agent / MCP routing work — Mentat OK for sub-tasks"
create_label "P1_PHYSICS" "0075CA" "Thermal physics, fluid dynamics, energy balance"
create_label "P2_UI"      "5319E7" "Dashboard, API, operator interface"
create_label "P2_DOCS"    "BFD4F2" "Documentation, architecture diagrams, READMEs"

# === Risk / Compliance ===
create_label "RISK/EJ"    "D93F0B" "Environmental justice / community impact risk — escalate immediately"
create_label "RISK/LEGAL" "D93F0B" "Legal / regulatory / permitting risk"
create_label "RISK/GRID"  "E99695" "Grid stability or power capacity risk"

# === Mentat governance ===
create_label "MENTAT_OK"   "0E8A16" "Mentat AI may auto-handle and close this issue"
create_label "HUMAN_GATE"  "B60205" "Must be reviewed and closed by a human — no AI auto-close"

# === Phase tracking ===
create_label "PHASE_3"    "C2E0C6" "Phase 3 scope"
create_label "PHASE_4"    "C2E0C6" "Phase 4 scope"
create_label "PHASE_GATE" "006B75" "Phase transition gate issue"

# === Component ===
create_label "comp/cooling"    "1D76DB" "apex_core, thermal_orchestrator, immersion"
create_label "comp/nanosphere" "1D76DB" "nanosphere ingest, fluid state"
create_label "comp/energy"     "1D76DB" "power_state_bridge, CHUNK_POWER_v2"
create_label "comp/swarm"      "1D76DB" "MCP router, mastermind-fusion, agent coordination"
create_label "comp/water"      "1D76DB" "water plant, commissioning, plant_core"
create_label "comp/ci"         "EDEDED" "CI, gauntlet, test infrastructure"

echo ""
echo "Done. $(gh label list --repo $REPO --limit 50 | wc -l) labels now in $REPO."
