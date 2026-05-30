# 🗄️ Database Setup Guide — APEX Colossus Cooling

## Supabase Schema Activation

### Step 1 — Run the Schema
1. Open your Supabase project → **SQL Editor**
2. Copy the entire contents of `database/supabase_schema.sql`
3. Paste and click **Run**
4. All 6 tables will be created with indexes, RLS policies, and real-time enabled

### Step 2 — Set Environment Variables

For Vercel deployment:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

For the Python orchestrator:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

### Step 3 — Deploy to Vercel
```bash
cd vercel-ui
npm install
vercel deploy --prod
```

Or connect the repo to Vercel dashboard and it auto-deploys on push.

### Step 4 — Verify
Hit `https://your-deployment.vercel.app/api/status` — you should see:
```json
{
  "system": "APEX Colossus Cooling",
  "pistons": { "total": 12, "active": 10 },
  "morpheus": "ACTIVE",
  "ring": -3
}
```

## MotherDuck (DuckDB Cloud)

```python
import duckdb
conn = duckdb.connect('md:colossus_cooling?motherduck_token=YOUR_TOKEN')
# Tables auto-created by motherduck_analytics.py connector
```

## Tables Created

| Table | Purpose | Real-time |
|---|---|---|
| `colossus_thermal_events` | Node-level temp readings | ✅ |
| `colossus_anomalies` | SHADOW piston detections | ✅ |
| `colossus_zone_snapshots` | Zone-level summaries | ❌ |
| `colossus_piston_log` | Agent activation history | ✅ |
| `colossus_emergency_log` | Emergency events | ❌ |
| `colossus_pue_log` | Power usage efficiency | ❌ |
