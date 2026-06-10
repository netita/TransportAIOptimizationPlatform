'use client'

import { useState } from 'react'
import { Navigation, AlertTriangle, Search, PauseCircle, Clock, Zap } from 'lucide-react'
import clsx from 'clsx'
import type { DispatcherAction, DispatcherResponse } from '@/lib/types'

interface Props {
  data?: DispatcherResponse
  isLoading?: boolean
}

const TYPE_CONFIG = {
  REROUTE: {
    icon: Navigation,
    label: 'Reroute',
    badgeClass: 'bg-blue-100 text-blue-700',
    iconClass: 'text-blue-500',
  },
  ESCALATE: {
    icon: AlertTriangle,
    label: 'Escalate',
    badgeClass: 'bg-red-100 text-red-700',
    iconClass: 'text-red-500',
  },
  INVESTIGATE: {
    icon: Search,
    label: 'Investigate',
    badgeClass: 'bg-orange-100 text-orange-700',
    iconClass: 'text-orange-500',
  },
  HOLD: {
    icon: PauseCircle,
    label: 'Hold',
    badgeClass: 'bg-amber-100 text-amber-700',
    iconClass: 'text-amber-500',
  },
}

const URGENCY_CONFIG = {
  CRITICAL: { border: 'border-l-red-500', bg: 'bg-red-50', badge: 'bg-red-500 text-white' },
  HIGH:     { border: 'border-l-orange-400', bg: 'bg-orange-50', badge: 'bg-orange-400 text-white' },
  MEDIUM:   { border: 'border-l-yellow-400', bg: 'bg-yellow-50', badge: 'bg-yellow-400 text-white' },
  LOW:      { border: 'border-l-slate-300', bg: 'bg-white', badge: 'bg-slate-300 text-slate-700' },
}

function ActionCard({ action }: { action: DispatcherAction }) {
  const type = TYPE_CONFIG[action.type]
  const urgency = URGENCY_CONFIG[action.urgency]
  const Icon = type.icon

  return (
    <div
      className={clsx(
        'border-l-4 rounded-r-lg px-4 py-3 flex items-start gap-3',
        urgency.border,
        urgency.bg
      )}
    >
      {/* Icon */}
      <div className="mt-0.5 flex-shrink-0">
        <Icon className={clsx('w-4 h-4', type.iconClass)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-0.5">
          <span className={clsx('text-xs font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide', urgency.badge)}>
            {action.urgency}
          </span>
          <span className={clsx('text-xs font-medium px-1.5 py-0.5 rounded', type.badgeClass)}>
            {type.label}
          </span>
          <span className="text-xs font-semibold text-slate-800 truncate">{action.title}</span>
        </div>
        <p className="text-xs text-slate-600 leading-snug mb-1">{action.description}</p>
        <p className="text-xs font-medium text-slate-500">
          <span className="text-slate-400">→ </span>{action.action}
        </p>
      </div>

      {/* Impact */}
      <div className="flex-shrink-0 text-right">
        <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">
          {action.impact_label}
        </span>
      </div>
    </div>
  )
}

const PAGE_SIZE = 6

export default function DispatcherPanel({ data, isLoading }: Props) {
  const [showAll, setShowAll] = useState(false)
  const actions = data?.actions ?? []
  const summary = data?.summary
  const visible = showAll ? actions : actions.slice(0, PAGE_SIZE)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-blue-600" />
          <h2 className="text-base font-semibold text-slate-800">Dispatcher Actions</h2>
          {summary && summary.total > 0 && (
            <span className="ml-1 text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
              {summary.total}
            </span>
          )}
        </div>

        {/* Summary chips */}
        {summary && (
          <div className="flex items-center gap-3 text-xs">
            {summary.critical > 0 && (
              <span className="flex items-center gap-1 font-semibold text-red-600">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                {summary.critical} critical
              </span>
            )}
            {summary.high > 0 && (
              <span className="flex items-center gap-1 font-semibold text-orange-500">
                <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
                {summary.high} high
              </span>
            )}
            {summary.total_saveable_minutes > 0 && (
              <span className="flex items-center gap-1 text-blue-600 font-medium">
                <Clock className="w-3 h-3" />
                {(summary.total_saveable_minutes / 60).toFixed(1)}h saveable
              </span>
            )}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4">
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && actions.length === 0 && (
          <div className="text-center py-6 text-slate-400 text-sm">
            No immediate actions required
          </div>
        )}

        {!isLoading && actions.length > 0 && (
          <div className="space-y-2">
            {visible.map((action) => (
              <ActionCard key={action.id} action={action} />
            ))}
            {actions.length > PAGE_SIZE && (
              <button
                onClick={() => setShowAll(v => !v)}
                className="w-full text-xs text-slate-500 hover:text-slate-700 py-1 transition-colors"
              >
                {showAll
                  ? '▲ Show less'
                  : `▼ Show ${actions.length - PAGE_SIZE} more actions`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
