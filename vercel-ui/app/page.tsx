'use client';

import { useEffect, useState, useCallback } from 'react';
import { createClient } from '@supabase/supabase-js';

// ── Types ──────────────────────────────────────────────────────────────────
interface ThermalEvent {
  id: number;
  node_id: string;
  zone_id: string;
  temp_celsius: number;
  alert_level: number;
  timestamp: string;
}

interface Anomaly {
  id: number;
  node_id: string;
  deviation_celsius: number;
  severity: string;
  timestamp: string;
}

interface PistonLog {
  id: number;
  piston: string;
  tier: string;
  trigger: string;
  timestamp: string;
}

interface ZoneSummary {
  zone_id: string;
  avg_temp: number;
  peak_temp: number;
  node_count: number;
  status: 'nominal' | 'warm' | 'hot' | 'critical';
}

// ── Supabase client (edge-safe) ────────────────────────────────────────────
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ''
);

// ── Helpers ────────────────────────────────────────────────────────────────
function tempClass(t: number) {
  if (t >= 85) return 'temp-critical';
  if (t >= 78) return 'temp-hot';
  if (t >= 70) return 'temp-warm';
  return 'temp-normal';
}

function tempBar(t: number) {
  const pct = Math.min(100, Math.max(0, ((t - 40) / 50) * 100));
  const color = t >= 85 ? '#ff3333' : t >= 78 ? '#ff8800' : t >= 70 ? '#ffcc00' : '#00ff88';
  return { pct, color };
}

const PISTONS = [
  { name: 'MICROWAVE',  tier: 'APEX',  status: 'active', ops: 12 },
  { name: 'SUPERNOVA',  tier: 'APEX',  status: 'standby', ops: 1 },
  { name: 'CORE-THINK', tier: 'APEX',  status: 'active', ops: 1 },
  { name: 'BODYBUILDER',tier: 'APEX',  status: 'standby', ops: 1 },
  { name: 'SHERLOCK',   tier: 'BLACK', status: 'active', ops: 1 },
  { name: 'SONIC',      tier: 'BLACK', status: 'active', ops: 1 },
  { name: 'GHOST',      tier: 'BLACK', status: 'active', ops: 1 },
  { name: 'PHANTOM',    tier: 'BLACK', status: 'active', ops: 1 },
  { name: 'VIPER',      tier: 'GREY',  status: 'active', ops: 1 },
  { name: 'WRAITH',     tier: 'GREY',  status: 'active', ops: 1 },
  { name: 'SPECTER',    tier: 'GREY',  status: 'active', ops: 1 },
  { name: 'SHADOW',     tier: 'GREY',  status: 'active', ops: 1 },
];

// ── Main Dashboard ─────────────────────────────────────────────────────────
export default function ColossusDashboard() {
  const [events,    setEvents]    = useState<ThermalEvent[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [pistonLog, setPistonLog] = useState<PistonLog[]>([]);
  const [zones,     setZones]     = useState<ZoneSummary[]>([]);
  const [tick,      setTick]      = useState(0);
  const [connected, setConnected] = useState(false);
  const [pue,       setPue]       = useState(1.13);
  const [totalNodes,setTotalNodes]= useState(0);

  // Fetch live data
  const fetchData = useCallback(async () => {
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
      // Demo mode — generate synthetic data
      setConnected(false);
      const demoZones: ZoneSummary[] = Array.from({ length: 6 }, (_, i) => ({
        zone_id: `ZONE-${String(i).padStart(3, '0')}`,
        avg_temp: 62 + Math.random() * 15,
        peak_temp: 70 + Math.random() * 18,
        node_count: 100 + Math.floor(Math.random() * 50),
        status: ['nominal', 'warm', 'nominal', 'hot', 'nominal', 'warm'][i] as ZoneSummary['status'],
      }));
      setZones(demoZones);
      setTotalNodes(demoZones.reduce((s, z) => s + z.node_count, 0));
      setPue(1.11 + Math.random() * 0.06);
      return;
    }

    setConnected(true);
    const [evRes, anRes, plRes] = await Promise.all([
      supabase.from('colossus_thermal_events').select('*').order('timestamp', { ascending: false }).limit(20),
      supabase.from('colossus_anomalies').select('*').order('timestamp', { ascending: false }).limit(10),
      supabase.from('colossus_piston_log').select('*').order('timestamp', { ascending: false }).limit(15),
    ]);
    if (evRes.data)  setEvents(evRes.data);
    if (anRes.data)  setAnomalies(anRes.data);
    if (plRes.data)  setPistonLog(plRes.data);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchData();
      setTick(t => t + 1);
      setPue(p => Math.max(1.08, Math.min(1.20, p + (Math.random() - 0.5) * 0.005)));
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Real-time Supabase subscription
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) return;
    const channel = supabase
      .channel('colossus-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'colossus_thermal_events' },
        payload => setEvents(prev => [payload.new as ThermalEvent, ...prev.slice(0, 19)]))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'colossus_anomalies' },
        payload => setAnomalies(prev => [payload.new as Anomaly, ...prev.slice(0, 9)]))
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, []);

  const criticalCount = zones.filter(z => z.status === 'critical').length;
  const hotCount      = zones.filter(z => z.status === 'hot').length;
  const activePistons = PISTONS.filter(p => p.status === 'active').length;

  return (
    <div className="min-h-screen bg-apex-black p-4">
      <div className="scanline" />

      {/* ── Header ── */}
      <header className="mb-6 flex items-center justify-between border-b border-apex-border pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-widest text-apex-cyan">❄️ APEX COLOSSUS COOLING</h1>
          <p className="text-xs text-gray-500 mt-0.5">xAI Thermal Intelligence System · GlacierEQ Sovereign Stack</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className={connected ? 'text-apex-green' : 'text-gray-500'}>
            {connected ? '● LIVE' : '◌ DEMO MODE'}
          </span>
          <span className="text-gray-600">TICK {String(tick).padStart(6, '0')}</span>
          <span className="text-apex-purple">RING -3</span>
          <span className="text-gray-600">{new Date().toLocaleTimeString()}</span>
        </div>
      </header>

      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'PUE', value: pue.toFixed(3), sub: 'target < 1.15',  color: pue < 1.15 ? 'text-apex-green' : 'text-apex-yellow' },
          { label: 'TOTAL NODES', value: totalNodes.toLocaleString(), sub: 'GPU nodes monitored', color: 'text-apex-cyan' },
          { label: 'PISTONS ACTIVE', value: `${activePistons}/12`, sub: 'stealth agents running', color: 'text-apex-purple' },
          { label: 'CRITICAL ZONES', value: criticalCount, sub: `${hotCount} hot · ${zones.length - criticalCount - hotCount} nominal`, color: criticalCount > 0 ? 'text-apex-red' : 'text-apex-green' },
        ].map(kpi => (
          <div key={kpi.label} className={`apex-card ${criticalCount > 0 && kpi.label === 'CRITICAL ZONES' ? 'apex-glow-red' : 'apex-glow-cyan'}`}>
            <div className="text-xs text-gray-500 mb-1 tracking-widest">{kpi.label}</div>
            <div className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</div>
            <div className="text-xs text-gray-600 mt-0.5">{kpi.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">

        {/* ── Zone Thermal Grid ── */}
        <div className="lg:col-span-2 apex-card">
          <h2 className="text-xs tracking-widest text-gray-400 mb-3">▸ ZONE THERMAL STATUS</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {zones.map(zone => {
              const bar = tempBar(zone.peak_temp);
              return (
                <div key={zone.zone_id} className={`rounded p-3 border ${
                  zone.status === 'critical' ? 'apex-glow-red bg-red-950/20' :
                  zone.status === 'hot'      ? 'apex-glow-yellow bg-yellow-950/20' :
                  'border-apex-border bg-apex-dark'
                }`}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-bold text-gray-300">{zone.zone_id}</span>
                    <span className={`text-xs font-bold ${tempClass(zone.peak_temp)}`}>
                      {zone.peak_temp.toFixed(1)}°C
                    </span>
                  </div>
                  {/* Temp bar */}
                  <div className="w-full bg-gray-800 rounded-full h-1.5 mb-2">
                    <div
                      className="h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${bar.pct}%`, background: bar.color }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-600">
                    <span>avg {zone.avg_temp.toFixed(1)}°C</span>
                    <span>{zone.node_count} nodes</span>
                    <span className={`uppercase font-bold ${
                      zone.status === 'critical' ? 'text-apex-red' :
                      zone.status === 'hot'      ? 'text-apex-yellow' :
                      zone.status === 'warm'     ? 'text-yellow-300' :
                      'text-apex-green'
                    }`}>{zone.status}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── 12 Stealth Pistons ── */}
        <div className="apex-card">
          <h2 className="text-xs tracking-widest text-gray-400 mb-3">▸ MITOCHONDRIA — 12 STEALTH PISTONS</h2>
          <div className="space-y-1.5">
            {PISTONS.map(p => (
              <div key={p.name} className="flex items-center justify-between py-1 border-b border-apex-border/30">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    p.status === 'active' ? 'bg-apex-green animate-pulse' : 'bg-gray-600'
                  }`} />
                  <span className="text-xs font-bold text-gray-200">{p.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {p.ops > 1 && <span className="text-xs text-apex-cyan">{p.ops}x</span>}
                  <span className={`piston-badge tier-${p.tier.toLowerCase()}`}>{p.tier}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-2 border-t border-apex-border/30 text-xs text-gray-600">
            <span className="text-apex-purple">MORPHEUS</span> active · Ring -3
          </div>
        </div>
      </div>

      {/* ── Bottom Row: Events + Anomalies + Piston Log ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* Thermal Events */}
        <div className="apex-card">
          <h2 className="text-xs tracking-widest text-gray-400 mb-3">▸ THERMAL EVENTS</h2>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {events.length === 0 ? (
              <p className="text-xs text-gray-600">Awaiting telemetry stream...</p>
            ) : events.map(e => (
              <div key={e.id} className="flex items-center gap-2 text-xs py-0.5">
                <span className={tempClass(e.temp_celsius)}>●</span>
                <span className="text-gray-500 shrink-0">{e.node_id.slice(-8)}</span>
                <span className={`font-bold ${tempClass(e.temp_celsius)}`}>{e.temp_celsius}°C</span>
                <span className="text-gray-600 ml-auto">{new Date(e.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Anomalies */}
        <div className="apex-card">
          <h2 className="text-xs tracking-widest text-gray-400 mb-3">▸ SHADOW ANOMALIES</h2>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {anomalies.length === 0 ? (
              <p className="text-xs text-gray-600">SHADOW monitoring — no anomalies detected</p>
            ) : anomalies.map(a => (
              <div key={a.id} className="flex items-center gap-2 text-xs py-0.5">
                <span className={a.severity === 'HIGH' ? 'text-apex-red' : a.severity === 'MEDIUM' ? 'text-apex-yellow' : 'text-gray-500'}>▲</span>
                <span className="text-gray-400">{a.node_id.slice(-8)}</span>
                <span className="text-apex-yellow">+{a.deviation_celsius?.toFixed(1)}°C</span>
                <span className={`ml-auto font-bold ${
                  a.severity === 'HIGH' ? 'text-apex-red' :
                  a.severity === 'MEDIUM' ? 'text-apex-yellow' : 'text-gray-500'
                }`}>{a.severity}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Piston Log */}
        <div className="apex-card">
          <h2 className="text-xs tracking-widest text-gray-400 mb-3">▸ PISTON ACTIVATIONS</h2>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {pistonLog.length === 0 ? (
              <p className="text-xs text-gray-600">Awaiting piston telemetry...</p>
            ) : pistonLog.map(pl => (
              <div key={pl.id} className="flex items-center gap-2 text-xs py-0.5">
                <span className={`piston-badge tier-${pl.tier?.toLowerCase()}`}>{pl.piston}</span>
                <span className="text-gray-500 text-xs truncate">{pl.trigger}</span>
                <span className="text-gray-600 ml-auto shrink-0">{new Date(pl.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="mt-6 pt-4 border-t border-apex-border/30 flex justify-between items-center text-xs text-gray-600">
        <span>GlacierEQ Sovereign Stack · Casey Barton · Honolulu, Hawaii</span>
        <span className="text-apex-cyan">APEX COLOSSUS COOLING v1.0</span>
        <span>xAI Thermal Intelligence · {new Date().getFullYear()}</span>
      </footer>
    </div>
  );
}
