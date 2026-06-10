'use client'

import { AlertTriangle, Info, Zap, CheckCircle } from 'lucide-react'
import type { Alert, AlertSeverity } from '@/lib/types'
import clsx from 'clsx'

interface AlertsFeedProps {
  alerts: Alert[]
  onMarkRead: (id: number) => void
}

const severityConfig: Record<
  AlertSeverity,
  { borderColor: string; bgColor: string; icon: React.ReactNode; iconColor: string }
> = {
  CRITICAL: {
    borderColor: 'border-l-red-500',
    bgColor: 'bg-red-50',
    icon: <Zap className="w-4 h-4" />,
    iconColor: 'text-red-600',
  },
  WARNING: {
    borderColor: 'border-l-amber-500',
    bgColor: 'bg-amber-50',
    icon: <AlertTriangle className="w-4 h-4" />,
    iconColor: 'text-amber-600',
  },
  INFO: {
    borderColor: 'border-l-blue-400',
    bgColor: 'bg-blue-50',
    icon: <Info className="w-4 h-4" />,
    iconColor: 'text-blue-600',
  },
}

const alertTypeLabels: Record<string, string> = {
  DELAY: 'Delay',
  CONGESTION: 'Congestion',
  BORDER: 'Border',
  ANOMALY: 'Anomaly',
  SLA_RISK: 'SLA Risk',
  ROUTE: 'Route',
}

function timeAgo(isoString: string): string {
  const now = new Date()
  const then = new Date(isoString)
  const diffMs = now.getTime() - then.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return `${Math.floor(diffH / 24)}d ago`
}

export default function AlertsFeed({ alerts, onMarkRead }: AlertsFeedProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 flex flex-col overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
        <h2 className="text-base font-semibold text-slate-800">
          Live Alerts
          {alerts.filter((a) => !a.is_read).length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-bold rounded-full">
              {alerts.filter((a) => !a.is_read).length}
            </span>
          )}
        </h2>
        <span className="text-xs text-slate-400">{alerts.length} total</span>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[420px]">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-400">
            <CheckCircle className="w-8 h-8 mb-2 text-green-400" />
            <span className="text-sm">All clear — no active alerts</span>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {alerts.map((alert) => {
              const cfg = severityConfig[alert.severity]
              return (
                <div
                  key={alert.id}
                  onClick={() => !alert.is_read && onMarkRead(alert.id)}
                  className={clsx(
                    'flex gap-3 px-4 py-3 border-l-4 transition-all cursor-pointer hover:bg-slate-50',
                    cfg.borderColor,
                    alert.is_read ? 'opacity-50 bg-white' : cfg.bgColor
                  )}
                >
                  <div className={clsx('flex-shrink-0 mt-0.5', cfg.iconColor)}>
                    {cfg.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className={clsx(
                          'text-xs font-semibold uppercase tracking-wide',
                          cfg.iconColor
                        )}
                      >
                        {alertTypeLabels[alert.alert_type] || alert.alert_type}
                      </span>
                      <span className="text-xs text-slate-400">
                        {timeAgo(alert.created_at)}
                      </span>
                      {!alert.is_read && (
                        <span className="ml-auto w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-slate-700 leading-relaxed">
                      {alert.message}
                    </p>
                    {alert.shipment_id && (
                      <div className="mt-1 text-xs text-blue-600 font-mono">
                        {alert.shipment_id}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {alerts.some((a) => !a.is_read) && (
        <div className="px-4 py-2 border-t border-slate-100 text-center">
          <span className="text-xs text-slate-400">
            Click an alert to mark as read
          </span>
        </div>
      )}
    </div>
  )
}
