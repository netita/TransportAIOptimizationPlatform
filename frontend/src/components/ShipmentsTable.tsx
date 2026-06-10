'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowUpRight } from 'lucide-react'
import type { Shipment, ShipmentStatus, Priority } from '@/lib/types'
import clsx from 'clsx'

interface ShipmentsTableProps {
  shipments: Shipment[]
  isLoading: boolean
  showAll?: boolean
}

const statusConfig: Record<ShipmentStatus, { label: string; className: string }> = {
  IN_TRANSIT: { label: 'In Transit', className: 'bg-blue-50 text-blue-700 border border-blue-200' },
  DELAYED: { label: 'Delayed', className: 'bg-red-50 text-red-700 border border-red-200' },
  AT_BORDER: { label: 'At Border', className: 'bg-amber-50 text-amber-700 border border-amber-200' },
  AT_WAREHOUSE: { label: 'At Warehouse', className: 'bg-purple-50 text-purple-700 border border-purple-200' },
  DELIVERED: { label: 'Delivered', className: 'bg-green-50 text-green-700 border border-green-200' },
  PENDING: { label: 'Pending', className: 'bg-slate-50 text-slate-600 border border-slate-200' },
}

const priorityConfig: Record<Priority, { label: string; className: string }> = {
  CRITICAL: { label: 'Critical', className: 'bg-red-100 text-red-800 border border-red-300 font-semibold' },
  HIGH: { label: 'High', className: 'bg-orange-100 text-orange-800 border border-orange-200' },
  MEDIUM: { label: 'Medium', className: 'bg-blue-50 text-blue-700 border border-blue-200' },
  LOW: { label: 'Low', className: 'bg-slate-50 text-slate-600 border border-slate-200' },
}

function StatusBadge({ status }: { status: ShipmentStatus }) {
  const cfg = statusConfig[status] || { label: status, className: 'bg-slate-50 text-slate-600 border border-slate-200' }
  return (
    <span className={clsx('px-2 py-0.5 rounded-md text-xs font-medium', cfg.className)}>
      {cfg.label}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: Priority }) {
  const cfg = priorityConfig[priority] || { label: priority, className: 'bg-slate-50 text-slate-600' }
  return (
    <span className={clsx('px-2 py-0.5 rounded-md text-xs font-medium', cfg.className)}>
      {cfg.label}
    </span>
  )
}

function RiskBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    score >= 0.6 ? 'bg-red-500' : score >= 0.3 ? 'bg-amber-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden min-w-[60px]">
        <div
          className={clsx('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={clsx(
          'text-xs font-medium w-8 text-right',
          score >= 0.6 ? 'text-red-600' : score >= 0.3 ? 'text-amber-600' : 'text-green-600'
        )}
      >
        {pct}%
      </span>
    </div>
  )
}

function DelayProbBadge({
  probability,
  topFactors,
}: {
  probability: number | null
  topFactors: Array<{ factor: string; impact: string }> | null
}) {
  if (probability === null || probability === undefined) {
    return <span className="text-xs text-slate-300">—</span>
  }
  const pct = Math.round(probability * 100)
  const colorClass =
    pct < 30
      ? 'text-green-600 bg-green-50 border-green-200'
      : pct < 60
      ? 'text-amber-600 bg-amber-50 border-amber-200'
      : 'text-red-600 bg-red-50 border-red-200'

  const tooltip =
    topFactors && topFactors.length > 0
      ? topFactors.map((f) => `${f.factor} (${f.impact})`).join(', ')
      : undefined

  return (
    <span
      className={clsx('px-2 py-0.5 rounded-md text-xs font-medium border', colorClass)}
      title={tooltip}
    >
      {pct}%
    </span>
  )
}

function PredictedDelayCell({ minutes }: { minutes: number | null }) {
  if (minutes === null || minutes === undefined) {
    return <span className="text-xs text-slate-300">—</span>
  }
  const rounded = Math.round(minutes)
  if (rounded <= 0) {
    return <span className="text-xs text-slate-400">0 min</span>
  }
  const colorClass =
    rounded > 60
      ? 'text-red-600 font-medium'
      : rounded >= 15
      ? 'text-amber-600 font-medium'
      : 'text-slate-500'
  return <span className={clsx('text-xs', colorClass)}>+{rounded}min</span>
}

function SkeletonRow() {
  return (
    <tr>
      {[...Array(10)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-100 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  )
}

function formatETA(eta: string): string {
  const d = new Date(eta)
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffH = Math.round(diffMs / 3600000)
  if (diffH < 0) return `${Math.abs(diffH)}h ago`
  if (diffH === 0) return 'Now'
  if (diffH < 24) return `in ${diffH}h`
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

export default function ShipmentsTable({
  shipments,
  isLoading,
  showAll = false,
}: ShipmentsTableProps) {
  const router = useRouter()
  const sorted = [...shipments].sort((a, b) => b.risk_score - a.risk_score)
  const displayed = showAll ? sorted : sorted.slice(0, 15)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-800">
          Active Shipments
          {!isLoading && (
            <span className="ml-2 text-sm font-normal text-slate-400">
              ({shipments.length} total)
            </span>
          )}
        </h2>
        {!showAll && (
          <Link
            href="/shipments"
            className="flex items-center gap-1 text-sm text-blue-700 hover:text-blue-800 font-medium"
          >
            View All <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Route
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">
                Carrier
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">
                Priority
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">
                ETA
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden xl:table-cell">
                Delay
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden xl:table-cell">
                <span className="flex items-center gap-1">
                  AI Delay Prob
                  <span className="ml-1 px-1 py-0.5 rounded text-[10px] font-bold bg-violet-100 text-violet-700 border border-violet-200">
                    ML
                  </span>
                </span>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider hidden xl:table-cell">
                <span className="flex items-center gap-1">
                  Predicted Delay
                  <span className="ml-1 px-1 py-0.5 rounded text-[10px] font-bold bg-violet-100 text-violet-700 border border-violet-200">
                    ML
                  </span>
                </span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {isLoading
              ? [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
              : displayed.map((shipment) => (
                  <tr
                    key={shipment.id}
                    onClick={() => router.push(`/shipments/${shipment.shipment_id}`)}
                    className={clsx(
                      'hover:bg-blue-50/40 transition-colors cursor-pointer',
                      shipment.status === 'DELAYED' && 'bg-red-50/30'
                    )}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-blue-700 font-medium whitespace-nowrap">
                      {shipment.shipment_id}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs text-slate-800 font-medium leading-tight">
                        {shipment.origin.split(',')[0]}
                      </div>
                      <div className="text-xs text-slate-400 leading-tight">
                        → {shipment.destination.split(',')[0]}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 hidden md:table-cell">
                      {shipment.carrier}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={shipment.status} />
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <PriorityBadge priority={shipment.priority} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 hidden lg:table-cell whitespace-nowrap">
                      {formatETA(shipment.eta)}
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      {shipment.delay_minutes ? (
                        <span className="text-xs font-medium text-red-600">
                          +{shipment.delay_minutes}min
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 min-w-[100px]">
                      <RiskBar score={shipment.risk_score} />
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      <DelayProbBadge
                        probability={shipment.delay_probability ?? null}
                        topFactors={shipment.top_factors ?? null}
                      />
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      <PredictedDelayCell
                        minutes={shipment.predicted_delay_minutes ?? null}
                      />
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {!isLoading && displayed.length === 0 && (
        <div className="px-4 py-8 text-center text-slate-400 text-sm">
          No shipments found.
        </div>
      )}
    </div>
  )
}
