'use client'

import { Clock } from 'lucide-react'
import type { Border, BorderStatus } from '@/lib/types'
import clsx from 'clsx'

interface BorderPanelProps {
  borders: Border[]
}

const statusConfig: Record<
  BorderStatus,
  { label: string; className: string; waitColor: string }
> = {
  NORMAL: {
    label: 'Normal',
    className: 'bg-green-50 text-green-700 border border-green-200',
    waitColor: 'text-green-600',
  },
  SLOW: {
    label: 'Slow',
    className: 'bg-amber-50 text-amber-700 border border-amber-200',
    waitColor: 'text-amber-600',
  },
  CONGESTED: {
    label: 'Congested',
    className: 'bg-red-50 text-red-700 border border-red-200',
    waitColor: 'text-red-600',
  },
  CLOSED: {
    label: 'Closed',
    className: 'bg-slate-800 text-white border border-slate-900',
    waitColor: 'text-slate-800',
  },
}

export default function BorderPanel({ borders }: BorderPanelProps) {
  const sorted = [...borders].sort((a, b) => b.wait_time_min - a.wait_time_min)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-base font-semibold text-slate-800">Border Crossings</h2>
      </div>
      <div className="divide-y divide-slate-50">
        {sorted.map((border) => {
          const cfg = statusConfig[border.status] || statusConfig.NORMAL
          return (
            <div key={border.id} className="px-4 py-3 flex items-center gap-3">
              <div className="flex-shrink-0 text-center">
                <div className={clsx('text-xl font-bold tabular-nums', cfg.waitColor)}>
                  {border.status === 'CLOSED'
                    ? '∞'
                    : Math.round(border.wait_time_min)}
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-0.5">
                  <Clock className="w-2.5 h-2.5" />
                  <span>min</span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-slate-800 truncate">
                    {border.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      'px-1.5 py-0.5 rounded text-xs font-medium',
                      cfg.className
                    )}
                  >
                    {cfg.label}
                  </span>
                  <span className="text-xs text-slate-400">
                    {Math.round(border.inspection_rate * 100)}% inspection
                  </span>
                  {border.weather_risk > 0.1 && (
                    <span className="text-xs text-amber-500">
                      ⚠ weather
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
