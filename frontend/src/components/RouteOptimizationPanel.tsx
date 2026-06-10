'use client'

import { useState } from 'react'
import type { RouteOptimizationResponse, RouteRecommendation } from '@/lib/types'

interface Props {
  data: RouteOptimizationResponse | undefined
  isLoading: boolean
}

const URGENCY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200',
  LOW:      'bg-emerald-100 text-emerald-700 border-emerald-200',
}

const PRIORITY_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700',
  HIGH:     'bg-orange-100 text-orange-700',
  MEDIUM:   'bg-slate-100 text-slate-600',
  LOW:      'bg-slate-100 text-slate-500',
}

function truncate(str: string, n: number) {
  return str.length > n ? str.slice(0, n - 1) + '…' : str
}

function RouteRow({ rec }: { rec: RouteRecommendation }) {
  const [expanded, setExpanded] = useState(false)

  const leftBorder = rec.should_reroute
    ? rec.urgency === 'CRITICAL' ? 'border-l-4 border-l-red-500'
    : rec.urgency === 'HIGH'     ? 'border-l-4 border-l-orange-500'
    :                              'border-l-4 border-l-amber-400'
    : 'border-l-4 border-l-emerald-400'

  return (
    <div className={`rounded-lg bg-white ${leftBorder} shadow-sm border border-slate-100 overflow-hidden`}>
      {/* Main row */}
      <button
        className="w-full text-left px-4 py-3 flex items-start justify-between gap-3 hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-semibold text-slate-800 text-sm">{rec.shipment_id}</span>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${PRIORITY_BADGE[rec.priority] || PRIORITY_BADGE.MEDIUM}`}>
              {rec.priority}
            </span>
            {rec.should_reroute && (
              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${URGENCY_STYLES[rec.urgency]}`}>
                REROUTE
              </span>
            )}
          </div>
          <div className="text-xs text-slate-500 mb-1">
            {truncate(rec.origin, 22)} → {truncate(rec.destination, 22)}
          </div>
          <div className="text-xs text-slate-600">
            {rec.should_reroute ? (
              <span>
                <span className="line-through text-slate-400">{rec.current_route}</span>
                <span className="mx-1 text-slate-400">→</span>
                <span className="font-medium text-blue-700">{rec.recommended_route}</span>
              </span>
            ) : (
              <span className="text-slate-500">{rec.current_route}</span>
            )}
          </div>
        </div>

        <div className="flex-shrink-0 text-right">
          {rec.should_reroute ? (
            <div className="text-sm font-bold text-emerald-600">−{rec.savings_minutes} min</div>
          ) : (
            <div className="text-xs text-emerald-600 font-medium">Optimal</div>
          )}
          <div className="text-xs text-slate-400 mt-0.5">{expanded ? '▲' : '▼'}</div>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-3 border-t border-slate-100 bg-slate-50 space-y-2">
          {/* Reason */}
          <p className="text-xs text-slate-600 pt-2">{rec.reason}</p>

          {/* Border breakdown */}
          {rec.border_breakdown.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">Border checkpoints</div>
              <div className="flex flex-wrap gap-2">
                {rec.border_breakdown.map((b) => (
                  <span
                    key={b.name}
                    className={`text-xs px-2 py-0.5 rounded-full border ${
                      b.wait_min >= 90
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : b.wait_min >= 45
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}
                  >
                    {b.name.length > 28 ? b.name.slice(0, 27) + '…' : b.name} — {b.wait_min} min
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* All route options */}
          {rec.all_options.length > 1 && (
            <div>
              <div className="text-xs font-semibold text-slate-500 mb-1">All route options</div>
              <div className="space-y-1">
                {rec.all_options.map((opt) => (
                  <div
                    key={opt.name}
                    className={`flex items-center justify-between text-xs px-2 py-1 rounded ${
                      opt.is_recommended ? 'bg-blue-50 text-blue-800' : 'text-slate-500'
                    }`}
                  >
                    <span className="truncate mr-2">{opt.is_recommended && '★ '}{opt.name}</span>
                    <span className="flex-shrink-0 font-medium">
                      {Math.round(opt.total_time_min / 60)}h {Math.round(opt.total_time_min % 60)}m
                      <span className="text-slate-400 ml-1">({opt.border_delay_min} min borders)</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function RouteOptimizationPanel({ data, isLoading }: Props) {
  const [showAll, setShowAll] = useState(false)

  if (isLoading) {
    return (
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-5">
        <div className="h-4 bg-slate-100 rounded animate-pulse w-48 mb-3" />
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-slate-100 rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (!data) return null

  const { recommendations, summary } = data
  const visibleRecs = showAll ? recommendations : recommendations.slice(0, 6)

  return (
    <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Route Optimization</h2>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-500 flex-wrap">
            <span>{summary.total_analyzed} shipments analyzed</span>
            {summary.reroute_recommended > 0 && (
              <span className="font-medium text-orange-600">
                ⚠ {summary.reroute_recommended} reroute{summary.reroute_recommended !== 1 ? 's' : ''} recommended
              </span>
            )}
            {summary.total_savings_minutes > 0 && (
              <span className="text-emerald-600 font-medium">
                ~{summary.total_savings_minutes} min total savings possible
              </span>
            )}
          </div>
        </div>
        {summary.reroute_recommended > 0 && (
          <span className="flex-shrink-0 bg-red-100 text-red-700 text-xs font-bold px-2.5 py-1 rounded-full border border-red-200">
            {summary.reroute_recommended} REROUTE{summary.reroute_recommended !== 1 ? 'S' : ''}
          </span>
        )}
      </div>

      {/* Worst bottleneck banner */}
      {summary.worst_bottleneck && (
        <div className="px-5 py-2 bg-amber-50 border-b border-amber-100 text-xs text-amber-800 flex items-center gap-1.5">
          <span className="font-semibold">Top bottleneck:</span>
          <span>{summary.worst_bottleneck}</span>
        </div>
      )}

      {/* Recommendation list */}
      <div className="p-4 space-y-2">
        {visibleRecs.length === 0 ? (
          <div className="text-center py-6 text-sm text-slate-400">
            No active shipments with recognized corridors
          </div>
        ) : (
          visibleRecs.map(rec => <RouteRow key={rec.shipment_id} rec={rec} />)
        )}

        {recommendations.length > 6 && (
          <button
            onClick={() => setShowAll(v => !v)}
            className="w-full text-xs text-slate-500 hover:text-slate-700 py-1 transition-colors"
          >
            {showAll
              ? '▲ Show less'
              : `▼ Show ${recommendations.length - 6} more shipments`}
          </button>
        )}
      </div>
    </div>
  )
}
