'use client'

import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import {
  ArrowLeft, Truck, MapPin, Package, Clock, AlertTriangle,
  TrendingUp, Navigation, CheckCircle, BarChart2,
} from 'lucide-react'
import clsx from 'clsx'
import Header from '@/components/Header'
import { getShipment, getRouteRecommendations, getDispatcherRecommendations, getLiveTrucks } from '@/lib/api'
import type { Shipment, ShipmentStatus, Priority } from '@/lib/types'

const ShipmentMap = dynamic(() => import('@/components/ShipmentMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-slate-100 animate-pulse flex items-center justify-center">
      <span className="text-slate-400 text-sm">Loading map…</span>
    </div>
  ),
})

// ── Shared badge configs (mirrors ShipmentsTable) ─────────────────────────────

const STATUS_CFG: Record<ShipmentStatus, { label: string; className: string }> = {
  IN_TRANSIT:   { label: 'In Transit',    className: 'bg-blue-50 text-blue-700 border-blue-200' },
  DELAYED:      { label: 'Delayed',       className: 'bg-red-50 text-red-700 border-red-200' },
  AT_BORDER:    { label: 'At Border',     className: 'bg-amber-50 text-amber-700 border-amber-200' },
  AT_WAREHOUSE: { label: 'At Warehouse',  className: 'bg-purple-50 text-purple-700 border-purple-200' },
  DELIVERED:    { label: 'Delivered',     className: 'bg-green-50 text-green-700 border-green-200' },
  PENDING:      { label: 'Pending',       className: 'bg-slate-50 text-slate-600 border-slate-200' },
}

const PRIORITY_CFG: Record<Priority, { label: string; dot: string }> = {
  CRITICAL: { label: 'Critical', dot: 'bg-red-500' },
  HIGH:     { label: 'High',     dot: 'bg-orange-400' },
  MEDIUM:   { label: 'Medium',   dot: 'bg-blue-400' },
  LOW:      { label: 'Low',      dot: 'bg-slate-400' },
}

function StatusBadge({ status }: { status: ShipmentStatus }) {
  const cfg = STATUS_CFG[status]
  return (
    <span className={clsx('px-3 py-1 rounded-full text-sm font-medium border', cfg.className)}>
      {cfg.label}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: Priority }) {
  const cfg = PRIORITY_CFG[priority]
  return (
    <span className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
      <span className={clsx('w-2 h-2 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

function RiskGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = score >= 0.6 ? 'text-red-600' : score >= 0.3 ? 'text-amber-600' : 'text-green-600'
  const bar = score >= 0.6 ? 'bg-red-500' : score >= 0.3 ? 'bg-amber-400' : 'bg-green-500'
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">Risk Score</span>
        <span className={clsx('font-bold text-base', color)}>{pct}%</span>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all', bar)} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400">
        {score >= 0.6 ? 'High risk — immediate attention required' :
         score >= 0.3 ? 'Moderate risk — monitor closely' : 'Low risk — on track'}
      </p>
    </div>
  )
}

function InfoRow({ icon: Icon, label, value, valueClass = '' }: {
  icon: React.ElementType; label: string; value: React.ReactNode; valueClass?: string
}) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-slate-50 last:border-0">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-400">{label}</p>
        <p className={clsx('text-sm font-medium text-slate-800 truncate', valueClass)}>{value}</p>
      </div>
    </div>
  )
}

function formatDateTime(dt: string) {
  return new Date(dt).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatETA(eta: string) {
  const d = new Date(eta)
  const diffH = Math.round((d.getTime() - Date.now()) / 3600000)
  const abs = formatDateTime(eta)
  if (diffH < 0) return `${abs} (${Math.abs(diffH)}h ago)`
  if (diffH === 0) return `${abs} (now)`
  return `${abs} (in ${diffH}h)`
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ShipmentDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: shipment, isLoading } = useSWR(
    id ? `shipment-${id}` : null,
    () => getShipment(id),
    { refreshInterval: 30000 }
  )

  const { data: routeData } = useSWR('routes', getRouteRecommendations, { refreshInterval: 60000 })
  const { data: dispatcherData } = useSWR('dispatcher', getDispatcherRecommendations, { refreshInterval: 60000 })
  const { data: trucks = [] } = useSWR('trucks', getLiveTrucks, { refreshInterval: 30000 })

  const route = routeData?.recommendations.find(r => r.shipment_id === id)
  const actions = dispatcherData?.actions.filter(a => a.entity_id === id) ?? []

  const assignedTruck = shipment?.truck_id
    ? trucks.find(t => t.truck_id === shipment.truck_id)
    : null

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Header />
        <main className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </main>
      </div>
    )
  }

  if (!shipment) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Header />
        <main className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center py-16 text-slate-400">Shipment not found.</div>
        </main>
      </div>
    )
  }

  const delayProb = shipment.delay_probability != null ? Math.round(shipment.delay_probability * 100) : null
  const predDelay = shipment.predicted_delay_minutes != null ? Math.round(shipment.predicted_delay_minutes) : null
  const confidence = shipment.prediction_confidence != null ? Math.round(shipment.prediction_confidence * 100) : null

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">

        {/* Breadcrumb + title */}
        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href="/shipments"
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Shipments
          </Link>
          <span className="text-slate-300">/</span>
          <span className="font-mono text-sm font-semibold text-slate-800">{shipment.shipment_id}</span>
          <div className="flex items-center gap-2 ml-auto">
            <PriorityBadge priority={shipment.priority} />
            <StatusBadge status={shipment.status} />
          </div>
        </div>

        {/* Top grid: Map + Overview + Dispatcher */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* Map */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Navigation className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-800">Route Map</h2>
              </div>
              <span className="text-xs text-slate-500">{Math.round(shipment.distance_km)} km</span>
            </div>
            <div className="h-[280px]">
              <ShipmentMap
                originLat={shipment.origin_lat}
                originLon={shipment.origin_lon}
                destLat={shipment.dest_lat}
                destLon={shipment.dest_lon}
                originName={shipment.origin}
                destName={shipment.destination}
                truckLat={assignedTruck?.lat}
                truckLon={assignedTruck?.lon}
              />
            </div>
            <div className="px-5 py-2.5 border-t border-slate-50 flex items-center gap-6 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-green-500 inline-block" />
                {shipment.origin.split(',')[0]}
              </span>
              {assignedTruck && (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-blue-500 inline-block" />
                  {shipment.truck_id} (last GPS)
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                {shipment.destination.split(',')[0]}
              </span>
            </div>
          </div>

          {/* Overview */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 space-y-1">
            <div className="flex items-center gap-2 mb-3">
              <Package className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-800">Overview</h2>
            </div>

            <InfoRow icon={MapPin} label="Origin" value={shipment.origin} />
            <InfoRow icon={MapPin} label="Destination" value={shipment.destination} />
            <InfoRow icon={Truck} label="Carrier" value={shipment.carrier} />
            <InfoRow
              icon={Truck}
              label="Assigned Truck"
              value={shipment.truck_id ?? 'Unassigned'}
              valueClass={!shipment.truck_id ? 'text-slate-400' : ''}
            />
            <InfoRow icon={Clock} label="ETA" value={formatETA(shipment.eta)} />
            <InfoRow icon={Clock} label="Created" value={formatDateTime(shipment.created_at)} />
            {shipment.actual_arrival && (
              <InfoRow icon={CheckCircle} label="Arrived" value={formatDateTime(shipment.actual_arrival)} />
            )}
            {(shipment.delay_minutes ?? 0) > 0 && (
              <InfoRow
                icon={AlertTriangle}
                label="Current Delay"
                value={`+${shipment.delay_minutes} min`}
                valueClass="text-red-600"
              />
            )}

            <div className="pt-3 mt-2 border-t border-slate-100">
              <RiskGauge score={shipment.risk_score} />
            </div>
          </div>
        </div>

        {/* Bottom grid: ML Prediction + Route Optimization + Dispatcher Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* ML Prediction */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 className="w-4 h-4 text-violet-600" />
              <h2 className="text-sm font-semibold text-slate-800">AI Prediction</h2>
              <span className="ml-auto px-1.5 py-0.5 rounded text-[10px] font-bold bg-violet-100 text-violet-700 border border-violet-200">
                ML
              </span>
            </div>

            {delayProb === null ? (
              <p className="text-sm text-slate-400">Prediction unavailable</p>
            ) : (
              <div className="space-y-4">
                {/* Delay probability */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-slate-500">Delay Probability</span>
                    <span className={clsx(
                      'font-bold text-base',
                      delayProb >= 70 ? 'text-red-600' : delayProb >= 40 ? 'text-amber-600' : 'text-green-600'
                    )}>
                      {delayProb}%
                    </span>
                  </div>
                  <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={clsx('h-full rounded-full transition-all',
                        delayProb >= 70 ? 'bg-red-500' : delayProb >= 40 ? 'bg-amber-400' : 'bg-green-500'
                      )}
                      style={{ width: `${delayProb}%` }}
                    />
                  </div>
                </div>

                {/* Predicted delay + confidence */}
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-xs text-slate-400">Predicted Delay</p>
                    <p className={clsx(
                      'text-xl font-bold',
                      (predDelay ?? 0) > 60 ? 'text-red-600' : (predDelay ?? 0) > 0 ? 'text-amber-600' : 'text-green-600'
                    )}>
                      {predDelay !== null && predDelay > 0 ? `+${predDelay} min` : 'On time'}
                    </p>
                  </div>
                  {confidence !== null && (
                    <div className="ml-auto text-right">
                      <p className="text-xs text-slate-400">Confidence</p>
                      <p className="text-xl font-bold text-slate-700">{confidence}%</p>
                    </div>
                  )}
                </div>

                {/* Top factors */}
                {shipment.top_factors && shipment.top_factors.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                      Top Delay Factors
                    </p>
                    <div className="space-y-1.5">
                      {shipment.top_factors.map((f, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-slate-600 truncate pr-2">{f.factor.replace(/_/g, ' ')}</span>
                          <span className={clsx(
                            'px-2 py-0.5 rounded font-semibold flex-shrink-0',
                            f.impact === 'HIGH' ? 'bg-red-100 text-red-700' :
                            f.impact === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                            'bg-slate-100 text-slate-600'
                          )}>
                            {f.impact}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Route Optimization */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-800">Route Optimization</h2>
            </div>

            {!route ? (
              <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2.5">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                On optimal route — no reroute needed
              </div>
            ) : (
              <div className="space-y-3">
                <div className={clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold',
                  route.should_reroute
                    ? 'bg-orange-50 text-orange-700 border border-orange-200'
                    : 'bg-green-50 text-green-700 border border-green-200'
                )}>
                  {route.should_reroute ? (
                    <><AlertTriangle className="w-3.5 h-3.5" /> Reroute recommended — saves {route.savings_minutes} min</>
                  ) : (
                    <><CheckCircle className="w-3.5 h-3.5" /> On optimal route</>
                  )}
                </div>

                <div className="space-y-1 text-xs">
                  <div className="flex items-start gap-2">
                    <span className="text-slate-400 w-20 flex-shrink-0">Current</span>
                    <span className="text-slate-700 font-medium">{route.current_route}</span>
                  </div>
                  {route.should_reroute && (
                    <div className="flex items-start gap-2">
                      <span className="text-slate-400 w-20 flex-shrink-0">Recommended</span>
                      <span className="text-blue-700 font-medium">{route.recommended_route}</span>
                    </div>
                  )}
                </div>

                {route.border_breakdown.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                      Border Breakdown
                    </p>
                    <div className="space-y-1.5">
                      {route.border_breakdown.map((b, i) => {
                        const isBad = route.bottlenecks.some(n => n.includes(b.name.split('(')[0].trim()))
                        return (
                          <div key={i} className="flex items-center justify-between text-xs">
                            <span className={clsx('truncate pr-2', isBad ? 'text-red-600 font-medium' : 'text-slate-600')}>
                              {b.name}
                            </span>
                            <span className={clsx(
                              'flex-shrink-0 font-semibold',
                              isBad ? 'text-red-600' : 'text-slate-500'
                            )}>
                              {b.wait_min} min
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Dispatcher Actions */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              <h2 className="text-sm font-semibold text-slate-800">Dispatcher Actions</h2>
              {actions.length > 0 && (
                <span className="ml-auto px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-700">
                  {actions.length}
                </span>
              )}
            </div>

            {actions.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2.5">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                No actions required for this shipment
              </div>
            ) : (
              <div className="space-y-2">
                {actions.map(a => (
                  <div
                    key={a.id}
                    className={clsx(
                      'rounded-lg border px-3 py-2.5 space-y-1',
                      a.urgency === 'CRITICAL' ? 'bg-red-50 border-red-200' :
                      a.urgency === 'HIGH' ? 'bg-orange-50 border-orange-200' :
                      'bg-slate-50 border-slate-200'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        'px-1.5 py-0.5 rounded text-[10px] font-bold uppercase',
                        a.urgency === 'CRITICAL' ? 'bg-red-200 text-red-800' :
                        a.urgency === 'HIGH' ? 'bg-orange-200 text-orange-800' :
                        'bg-slate-200 text-slate-700'
                      )}>
                        {a.urgency}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">{a.type}</span>
                    </div>
                    <p className="text-xs text-slate-600">{a.description}</p>
                    <p className="text-xs font-medium text-blue-700">{a.action}</p>
                    {a.impact_label && (
                      <p className="text-xs text-slate-500">{a.impact_label}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
