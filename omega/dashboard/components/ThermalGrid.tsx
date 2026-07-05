'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import clsx from 'clsx'

type Zone = { temp_c: number; status: string }

const TEMP_COLOR = (t: number) =>
  t < 50 ? 'text-green-400' : t < 65 ? 'text-yellow-400' : t < 80 ? 'text-orange-400' : 'text-red-400'

const GLOW = (t: number) =>
  t < 50 ? 'glow-green' : t < 80 ? '' : 'glow-red'

export function ThermalGrid({ zones, loading }: { zones?: Record<string, Zone>, loading: boolean }) {
  if (loading) return (
    <div className="grid grid-cols-3 gap-3">
      {Array.from({length: 6}).map((_,i) => (
        <div key={i} className="card animate-pulse h-20" />
      ))}
    </div>
  )

  if (!zones) return <p className="text-slate-500 text-sm">No thermal data</p>

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {Object.entries(zones).map(([name, z]) => (
        <div key={name} className={clsx('card', GLOW(z.temp_c))}>
          <p className="text-xs text-slate-400 uppercase tracking-widest">{name.replace('_', ' ')}</p>
          <p className={clsx('text-3xl font-bold mt-1', TEMP_COLOR(z.temp_c))}>
            {z.temp_c.toFixed(1)}<span className="text-sm ml-1">°C</span>
          </p>
          <p className={clsx('text-xs mt-1', z.status === 'nominal' ? 'text-green-400' : 'text-yellow-400')}>
            ● {z.status}
          </p>
        </div>
      ))}
    </div>
  )
}
