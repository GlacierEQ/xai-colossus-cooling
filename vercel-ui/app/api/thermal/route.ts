import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const runtime = 'edge';

export async function GET(req: NextRequest) {
  const url  = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key  = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    // Return synthetic demo data when not connected
    const zones = Array.from({ length: 6 }, (_, i) => ({
      zone_id:    `ZONE-${String(i).padStart(3, '0')}`,
      avg_temp:   62 + Math.random() * 12,
      peak_temp:  68 + Math.random() * 18,
      node_count: 100 + Math.floor(Math.random() * 64),
      status:     Math.random() > 0.8 ? 'warm' : 'nominal',
    }));
    return NextResponse.json({ source: 'demo', zones, pue: 1.12 + Math.random() * 0.05 });
  }

  const supabase = createClient(url, key);
  const { data, error } = await supabase
    .from('colossus_thermal_events')
    .select('zone_id, temp_celsius, alert_level')
    .order('timestamp', { ascending: false })
    .limit(500);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  // Aggregate by zone
  const zoneMap: Record<string, number[]> = {};
  (data ?? []).forEach(row => {
    if (!zoneMap[row.zone_id]) zoneMap[row.zone_id] = [];
    zoneMap[row.zone_id].push(row.temp_celsius);
  });

  const zones = Object.entries(zoneMap).map(([zone_id, temps]) => ({
    zone_id,
    avg_temp:   temps.reduce((a, b) => a + b, 0) / temps.length,
    peak_temp:  Math.max(...temps),
    node_count: temps.length,
    status: Math.max(...temps) >= 85 ? 'critical' : Math.max(...temps) >= 78 ? 'hot' : Math.max(...temps) >= 70 ? 'warm' : 'nominal',
  }));

  return NextResponse.json({ source: 'supabase', zones });
}
