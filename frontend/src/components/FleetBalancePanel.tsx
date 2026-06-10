'use client'

import { useState } from 'react'
import { Truck, ArrowRight, BarChart2, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import type { CorridorLoad, CorridorLoadLevel, FleetBalanceResponse } from '@/lib/types'

interface Props {
  data?: FleetBalanceResponse
  isLoading?: boolean
}

const LOAD_CONFIG: Record<CorridorLoadLevel, { bar: string; badge: string; text: string }> = {
  CRITICAL: { bar: 'bg-red-500',    badge: 'bg-red-100 text-red-700',    text: 'Overloaded' },
  HIGH:     { bar: 'bg-orange-400', badge: 'bg-orange-100 text-orange-700', text: 'High' },
  BALANCED: { bar: 'bg-emerald-400',badge: 'bg-emerald-100 text-emerald-700', text: 'Balanced' },
  LOW:      { bar: 'bg-slate-300',  badge: 'bg-slate-100 text-slate-500', text: 'Low' },
}

const PRIORITY_DOT: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-400',
  MEDIUM:   'bg-slate-400',
  LOW:      'bg-slate-300',
}

function CorridorBar({ c, maxTrucks }: { c: CorridorLoad; maxTrucks: number }) {
  const cfg = LOAD_CONFIG[c.load_level]
  const pct = maxTrucks > 0 ? Math.round((c.active_trucks / maxTrucks) * 100) : 0

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-700 font-medium truncate pr-2" title={c.corridor_name}>
          {c.corridor_name}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-slate-500">{c.active_trucks} trucks</span>
          <span className={clsx('px-1.5 py-0.5 rounded text-xs font-semibold', cfg.badge)}>
            {cfg.text}
          </span>
        </div>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', cfg.bar)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {(c.load_level === 'CRITICAL' || c.load_level === 'HIGH') && (
        <p className="text-xs text-slate-500 italic">{c.recommendation}</p>
      )}
    </div>
  )
}

export default function FleetBalancePanel({ data, isLoading }: Props) {
  const [showAllCorridors, setShowAllCorridors] = useState(false)

  const summary = data?.summary
  const corridors = data?.corridor_load ?? []
  const assignments = data?.assignments ?? []
  const unassigned = data?.unassigned_shipments ?? []
  const idle = data?.idle_trucks ?? []

  const maxTrucks = corridors.length > 0 ? Math.max(...corridors.map(c => c.active_trucks)) : 1
  const visibleCorridors = showAllCorridors ? corridors : corridors.slice(0, 5)

  const balancePct = summary ? Math.round(summary.balance_score * 100) : 0
  const balanceColor =
    balancePct >= 75 ? 'text-emerald-600' :
    balancePct >= 50 ? 'text-orange-500' : 'text-red-500'

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-600" />
          <h2 className="text-base font-semibold text-slate-800">Fleet Load Balancing</h2>
        </div>
        {summary && (
          <div className="flex items-center gap-4 text-xs">
            <span className="text-slate-500">
              <span className="font-semibold text-slate-700">{summary.active_trucks}</span> active
              {' / '}
              <span className={clsx('font-semibold', summary.available_trucks > 0 ? 'text-emerald-600' : 'text-slate-400')}>
                {summary.available_trucks}
              </span> available
            </span>
            <span className={clsx('font-bold text-sm', balanceColor)}>
              {balancePct}% balanced
            </span>
          </div>
        )}
      </div>

      <div className="p-4 space-y-5">
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />)}
          </div>
        )}

        {!isLoading && (
          <>
            {/* Corridor load distribution */}
            {corridors.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Corridor Load Distribution
                </div>
                <div className="space-y-3">
                  {visibleCorridors.map(c => (
                    <CorridorBar key={c.corridor_id} c={c} maxTrucks={maxTrucks} />
                  ))}
                </div>
                {corridors.length > 5 && (
                  <button
                    onClick={() => setShowAllCorridors(v => !v)}
                    className="mt-2 w-full text-xs text-slate-500 hover:text-slate-700 py-1 transition-colors"
                  >
                    {showAllCorridors ? '▲ Show less' : `▼ Show ${corridors.length - 5} more corridors`}
                  </button>
                )}
              </div>
            )}

            {corridors.length === 0 && (
              <div className="text-center py-4 text-slate-400 text-sm">
                No active shipments on recognised corridors
              </div>
            )}

            {/* Active assignments */}
            {assignments.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                  Recommended Assignments
                </div>
                <div className="space-y-2">
                  {assignments.map(a => (
                    <div key={a.truck_id + a.shipment_id}
                      className="flex items-center gap-3 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 text-xs"
                    >
                      <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', PRIORITY_DOT[a.priority] ?? 'bg-slate-400')} />
                      <span className="font-semibold text-slate-700">{a.truck_id}</span>
                      <ArrowRight className="w-3 h-3 text-slate-400 flex-shrink-0" />
                      <span className="font-semibold text-blue-700">{a.shipment_id}</span>
                      <span className="text-slate-500 truncate flex-1">{a.origin} → {a.destination}</span>
                      <span className="text-slate-400 flex-shrink-0">{a.distance_km} km</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No assignments — all trucks busy */}
            {assignments.length === 0 && summary && summary.available_trucks === 0 && (
              <div className="flex items-start gap-2 bg-slate-50 rounded-lg px-3 py-2.5 text-xs text-slate-500">
                <Truck className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-slate-400" />
                All {summary.total_trucks} trucks are active.
                {summary.pending_shipments > 0
                  ? ` ${summary.pending_shipments} pending shipment${summary.pending_shipments > 1 ? 's' : ''} will be assigned as trucks become available.`
                  : ' No pending shipments waiting for assignment.'}
              </div>
            )}

            {/* Idle trucks with no work */}
            {idle.length > 0 && (
              <div className="flex items-start gap-2 bg-emerald-50 rounded-lg px-3 py-2.5 text-xs text-emerald-700">
                <Truck className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>
                  <span className="font-semibold">{idle.length} truck{idle.length > 1 ? 's' : ''} idle</span>
                  {' — '}
                  {idle.slice(0, 3).map(t => t.truck_id).join(', ')}
                  {idle.length > 3 && ` +${idle.length - 3} more`}.
                  No pending shipments to assign.
                </span>
              </div>
            )}

            {/* Unassigned critical shipments */}
            {unassigned.length > 0 && (
              <div className="flex items-start gap-2 bg-red-50 rounded-lg px-3 py-2.5 text-xs text-red-700">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>
                  <span className="font-semibold">{unassigned.length} shipment{unassigned.length > 1 ? 's' : ''} unassigned</span>
                  {' — no available truck. '}
                  {unassigned.filter(s => s.priority === 'CRITICAL').length > 0 &&
                    `${unassigned.filter(s => s.priority === 'CRITICAL').length} CRITICAL.`}
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
