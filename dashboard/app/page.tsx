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
