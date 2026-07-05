'use client'
import clsx from 'clsx'

type Piston = { state: string; flow_rate: number }

export function PistonPanel({ pistons }: { pistons?: Record<string, Piston> }) {
  if (!pistons) return <div className="card text-slate-500 text-sm">No piston data</div>

  return (
    <div className="card space-y-2">
      {Object.entries(pistons).map(([name, p]) => (
        <div key={name} className="flex items-center gap-3">
          <span className="text-xs text-slate-400 w-20">{name.replace('_', ' ')}</span>
          <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={clsx('h-full rounded-full transition-all duration-700',
                p.state === 'active' ? 'bg-apex-blue' : 'bg-slate-600')}
              style={{ width: p.state === 'active' ? `${Math.min(100, p.flow_rate * 10)}%` : '4%' }}
            />
          </div>
          <span className={clsx('text-xs w-16 text-right',
            p.state === 'active' ? 'text-apex-blue' : 'text-slate-500')}>
            {p.state === 'active' ? `${p.flow_rate} L/m` : 'idle'}
          </span>
        </div>
      ))}
    </div>
  )
}
