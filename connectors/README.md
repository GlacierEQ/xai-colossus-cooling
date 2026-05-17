# Connectors — GlacierEQ APEX Stack

All connectors share the same env var pattern. Set once, all connectors pick up.

## Environment Variables

```bash
export SUPABASE_URL="https://<your-project>.supabase.co"
export SUPABASE_SERVICE_KEY="<service-role-key>"
export NOTION_TOKEN="<integration-token>"
export MOTHERDUCK_TOKEN="<motherduck-token>"
```

## Connector Matrix

| File | Integration | Ring | Status |
|---|---|---|---|
| `supabase_telemetry.py` | Supabase (GlacierEQ/mastermind) | 0 | Live |
| `sherlock_supernova_webhook.py` | Supabase real-time listener | -3 | Live |
| `notion_dashboard.py` | Notion workspace | 0 | Live |
| `motherduck_analytics.py` | MotherDuck/DuckDB | 0 | Live |
| `autocad_connector.py` | AutoCAD COM / ezdxf | 0 | Live |

## AutoCAD Quick Start

```bash
pip install ezdxf
python connectors/autocad_connector.py
# Outputs: CCL-002_Underfloor_Piping_Plan.dxf
```

Flip to live COM mode (Windows + licensed AutoCAD):
```python
from connectors.autocad_connector import mcp_action_draw_ccl002
mcp_action_draw_ccl002({"prefer_com": True})
```

## SHERLOCK-SUPERNOVA Quick Start

```bash
# 1. Print schema extension SQL
python connectors/sherlock_supernova_webhook.py --schema

# 2. Paste SQL into GlacierEQ/mastermind Supabase SQL editor

# 3. Run the live pipeline
python connectors/sherlock_supernova_webhook.py
```

SHERLOCK is observe-only. No actuation. Physics gate is downstream.
