'use client'

import type { Warehouse } from '@/lib/types'
import clsx from 'clsx'

interface WarehousePanelProps {
  warehouses: Warehouse[]
}

function CongestionGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 70 ? '#dc2626' : pct >= 40 ? '#d97706' : '#16a34a'
  const radius = 20
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (pct / 100) * circumference

  return (
    <div className="relative flex items-center justify-center w-14 h-14">
      <svg className="w-14 h-14 -rotate-90" viewBox="0 0 52 52">
        <circle
          cx="26"
          cy="26"
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="5"
        />
        <circle
          cx="26"
          cy="26"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          className="text-xs font-bold"
          style={{ color }}
        >
          {pct}%
        </span>
      </div>
    </div>
  )
}

function getWarehouseStatus(wh: Warehouse): { label: string; className: string } {
  const pct = wh.congestion_risk
  if (pct >= 0.7)
    return { label: 'Overloaded', className: 'bg-red-50 text-red-700 border border-red-200' }
  if (pct >= 0.4)
    return { label: 'Busy', className: 'bg-amber-50 text-amber-700 border border-amber-200' }
  return { label: 'Normal', className: 'bg-green-50 text-green-700 border border-green-200' }
}

export default function WarehousePanel({ warehouses }: WarehousePanelProps) {
  const sorted = [...warehouses].sort(
    (a, b) => b.congestion_risk - a.congestion_risk
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-base font-semibold text-slate-800">Warehouse Status</h2>
      </div>
      <div className="divide-y divide-slate-50">
        {sorted.map((wh) => {
          const statusBadge = getWarehouseStatus(wh)
          return (
            <div key={wh.id} className="px-4 py-3 flex items-center gap-3">
              <CongestionGauge value={wh.congestion_risk} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-slate-800 truncate">
                    {wh.name}
                  </span>
                  <span
                    className={clsx(
                      'px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0',
                      statusBadge.className
                    )}
                  >
                    {statusBadge.label}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span>
                    <strong className="text-slate-700">{wh.available_docks}</strong>
                    /{wh.total_docks} docks
                  </span>
                  <span>
                    Queue:{' '}
                    <strong
                      className={clsx(
                        wh.queue_time_min > 60
                          ? 'text-red-600'
                          : wh.queue_time_min > 30
                          ? 'text-amber-600'
                          : 'text-green-600'
                      )}
                    >
                      {Math.round(wh.queue_time_min)}min
                    </strong>
                  </span>
                  <span className="text-slate-400">{wh.city}</span>
                </div>
              </div>
              {wh.incoming_trucks > 0 && (
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-semibold text-slate-800">
                    {wh.incoming_trucks}
                  </div>
                  <div className="text-xs text-slate-400">inbound</div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
