'use client'
import clsx from 'clsx'

export function StatusBar({ health }: { health?: any }) {
  const online = health?.status !== 'colossus_unreachable'
  return (
    <div className="flex items-center gap-2">
      <span className={clsx('w-2 h-2 rounded-full', online ? 'bg-green-400 animate-pulse' : 'bg-red-500')} />
      <span className={clsx('text-xs', online ? 'text-green-400' : 'text-red-400')}>
        {online ? 'COLOSSUS LIVE' : 'OFFLINE'}
      </span>
    </div>
  )
}
