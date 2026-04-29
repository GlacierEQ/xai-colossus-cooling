'use client'
import useSWR from 'swr'
import { ThermalGrid } from '../components/ThermalGrid'
import { PistonPanel }  from '../components/PistonPanel'
import { MorpheusLog }  from '../components/MorpheusLog'
import { StatusBar }    from '../components/StatusBar'

const fetcher = (url: string) =>
  fetch(url, { headers: { 'x-api-key': process.env.NEXT_PUBLIC_COLOSSUS_API_KEY || '' } })
    .then(r => r.json())

export default function Dashboard() {
  const { data: thermal,   error: tErr } = useSWR('/api/thermal',   fetcher, { refreshInterval: 3000 })
  const { data: decisions, error: dErr } = useSWR('/api/decisions',  fetcher, { refreshInterval: 5000 })
  const { data: health,   error: hErr }  = useSWR('/api/health',     fetcher, { refreshInterval: 10000 })
  const { data: forecastBundle, error: fErr } = useSWR('/api/m2a/forecast?zone_id=ZONE-001', fetcher, { refreshInterval: 8000 })

  const topForecast = forecastBundle?.bundle?.selected_responders?.[0]

  return (
    <main className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-apex-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-apex-blue tracking-widest">⬡ COLOSSUS</h1>
          <p className="text-sm text-slate-400">APEX Thermal Intelligence | GlacierEQ</p>
        </div>
        <StatusBar health={health} />
      </div>

      {/* Thermal Grid */}
      <section>
        <h2 className="text-xs uppercase tracking-widest text-slate-400 mb-3">Thermal Zones</h2>
        <ThermalGrid zones={thermal?.zones} loading={!thermal && !tErr} />
      </section>

      {/* Forecast bundle preview */}
      <section className="rounded-xl border border-apex-border p-4 bg-black/20">
        <h2 className="text-xs uppercase tracking-widest text-slate-400 mb-3">M2A Forecast Bundle</h2>
        {fErr ? (
          <p className="text-sm text-red-400">Failed to load M2A forecast bundle.</p>
        ) : topForecast ? (
          <div className="space-y-2 text-sm text-slate-300">
            <p><span className="text-slate-500">Responder:</span> {topForecast.node_id}</p>
            <p><span className="text-slate-500">Action:</span> {topForecast.proposed_action}</p>
            <p><span className="text-slate-500">Relevance:</span> {topForecast.relevance}</p>
            <p><span className="text-slate-500">Confidence:</span> {topForecast.confidence}</p>
            <p><span className="text-slate-500">Audit Event:</span> {forecastBundle?.bundle?.audit_event_id || 'pending'}</p>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No forecast responders selected yet.</p>
        )}
      </section>

      {/* Pistons + MORPHEUS split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <h2 className="text-xs uppercase tracking-widest text-slate-400 mb-3">Pistons</h2>
          <PistonPanel pistons={thermal?.pistons} />
        </section>
        <section>
          <h2 className="text-xs uppercase tracking-widest text-slate-400 mb-3">MORPHEUS RL Decisions</h2>
          <MorpheusLog decisions={decisions?.decisions ?? []} />
        </section>
      </div>
    </main>
  )
}
