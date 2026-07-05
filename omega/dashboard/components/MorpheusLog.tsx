'use client'

type Decision = { id: string; timestamp: string; action: string; reward: number; confidence: number }

export function MorpheusLog({ decisions }: { decisions: Decision[] }) {
  if (!decisions.length) return <div className="card text-slate-500 text-sm">No decisions</div>

  return (
    <div className="card space-y-3 max-h-72 overflow-y-auto">
      {decisions.map(d => (
        <div key={d.id} className="border-b border-apex-border pb-2 last:border-0">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>{d.id}</span>
            <span>{new Date(d.timestamp).toLocaleTimeString()}</span>
          </div>
          <p className="text-sm text-apex-cyan font-mono">{d.action}</p>
          <div className="flex gap-4 mt-1">
            <span className="text-xs text-green-400">reward {(d.reward*100).toFixed(0)}%</span>
            <span className="text-xs text-blue-400">conf {(d.confidence*100).toFixed(0)}%</span>
          </div>
        </div>
      ))}
    </div>
  )
}
