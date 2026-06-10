'use client'

import {
  Truck,
  Clock,
  AlertTriangle,
  MapPin,
  Flag,
} from 'lucide-react'
import type { KPIDashboard } from '@/lib/types'
import clsx from 'clsx'

interface KPICardsProps {
  data: KPIDashboard | undefined
  isLoading: boolean
}

interface CardConfig {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  color: string
  bgColor: string
  borderColor: string
}

function KPICard({ label, value, sub, icon, color, bgColor, borderColor }: CardConfig) {
  return (
    <div
      className={clsx(
        'bg-white rounded-xl shadow-sm border p-5 flex items-center gap-4 card-transition',
        borderColor
      )}
    >
      <div
        className={clsx(
          'flex items-center justify-center w-12 h-12 rounded-xl flex-shrink-0',
          bgColor
        )}
      >
        <div className={clsx('w-6 h-6', color)}>{icon}</div>
      </div>
      <div className="min-w-0">
        <div className={clsx('text-2xl font-bold leading-none', color)}>
          {value}
        </div>
        <div className="text-sm font-medium text-slate-600 mt-1">{label}</div>
        {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 flex items-center gap-4">
      <div className="w-12 h-12 rounded-xl bg-slate-100 animate-pulse flex-shrink-0" />
      <div className="flex-1">
        <div className="h-7 bg-slate-100 rounded animate-pulse w-16 mb-2" />
        <div className="h-4 bg-slate-100 rounded animate-pulse w-24" />
      </div>
    </div>
  )
}

export default function KPICards({ data, isLoading }: KPICardsProps) {
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  const onTimePercent = Math.round(data.on_time_rate * 100)

  const cards: CardConfig[] = [
    {
      label: 'Active Shipments',
      value: data.active_shipments,
      sub: `${onTimePercent}% on-time`,
      icon: <Truck className="w-full h-full" />,
      color: 'text-blue-700',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-100',
    },
    {
      label: 'Delayed',
      value: data.delayed_count,
      sub: `Avg ${Math.round(data.avg_delay_minutes)}min delay`,
      icon: <Clock className="w-full h-full" />,
      color: data.delayed_count > 0 ? 'text-amber-600' : 'text-slate-400',
      bgColor: data.delayed_count > 0 ? 'bg-amber-50' : 'bg-slate-50',
      borderColor: data.delayed_count > 0 ? 'border-amber-100' : 'border-slate-100',
    },
    {
      label: 'At Risk',
      value: data.at_risk_count,
      sub: 'Risk score ≥ 0.6',
      icon: <AlertTriangle className="w-full h-full" />,
      color: data.at_risk_count > 0 ? 'text-red-600' : 'text-slate-400',
      bgColor: data.at_risk_count > 0 ? 'bg-red-50' : 'bg-slate-50',
      borderColor: data.at_risk_count > 0 ? 'border-red-100' : 'border-slate-100',
    },
    {
      label: 'Trucks Online',
      value: data.trucks_online,
      sub: 'Actively tracked',
      icon: <MapPin className="w-full h-full" />,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      borderColor: 'border-emerald-100',
    },
    {
      label: 'Border Alerts',
      value: data.border_alerts,
      sub: 'Unread alerts',
      icon: <Flag className="w-full h-full" />,
      color: data.border_alerts > 0 ? 'text-orange-600' : 'text-slate-400',
      bgColor: data.border_alerts > 0 ? 'bg-orange-50' : 'bg-slate-50',
      borderColor: data.border_alerts > 0 ? 'border-orange-100' : 'border-slate-100',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {cards.map((card) => (
        <KPICard key={card.label} {...card} />
      ))}
    </div>
  )
}
