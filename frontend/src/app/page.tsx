'use client'

import dynamic from 'next/dynamic'
import useSWR from 'swr'
import Header from '@/components/Header'
import KPICards from '@/components/KPICards'
import ShipmentsTable from '@/components/ShipmentsTable'
import AlertsFeed from '@/components/AlertsFeed'
import WarehousePanel from '@/components/WarehousePanel'
import BorderPanel from '@/components/BorderPanel'
import RouteOptimizationPanel from '@/components/RouteOptimizationPanel'
import DispatcherPanel from '@/components/DispatcherPanel'
import FleetBalancePanel from '@/components/FleetBalancePanel'
import AICopilot from '@/components/AICopilot'
import {
  getKPI,
  getShipments,
  getLiveTrucks,
  getWarehouses,
  getBorders,
  getAlerts,
  markAlertRead,
  getAnomalies,
  getRouteRecommendations,
  getDispatcherRecommendations,
  getFleetBalance,
} from '@/lib/api'
const LiveMap = dynamic(() => import('@/components/LiveMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full rounded-xl bg-slate-100 animate-pulse flex items-center justify-center">
      <span className="text-slate-400 text-sm">Loading map...</span>
    </div>
  ),
})

// Polling intervals — WS is primary; these are fallbacks
const POLL_SLOW = 30000
const POLL_MEDIUM = 60000

export default function DashboardPage() {
  const { data: kpi, isLoading: kpiLoading } = useSWR('kpi', getKPI, { refreshInterval: POLL_SLOW })
  const { data: shipmentsData, isLoading: shipmentsLoading } = useSWR(
    'shipments',
    () => getShipments({ limit: 100 }),
    { refreshInterval: POLL_SLOW }
  )
  const { data: trucks = [] } = useSWR('trucks', getLiveTrucks, { refreshInterval: POLL_SLOW })
  const { data: warehouses = [] } = useSWR('warehouses', getWarehouses, { refreshInterval: POLL_SLOW })
  const { data: borders = [] } = useSWR('borders', getBorders, { refreshInterval: POLL_SLOW })
  const { data: alerts = [], mutate: mutateAlerts } = useSWR('alerts', getAlerts, {
    refreshInterval: POLL_SLOW,
  })
  const { data: anomalies = [] } = useSWR('anomalies', getAnomalies, { refreshInterval: POLL_MEDIUM })
  const { data: routeData, isLoading: routeLoading } = useSWR(
    'routes',
    getRouteRecommendations,
    { refreshInterval: POLL_MEDIUM }
  )
  const { data: dispatcherData, isLoading: dispatcherLoading } = useSWR(
    'dispatcher',
    getDispatcherRecommendations,
    { refreshInterval: POLL_MEDIUM }
  )
  const { data: fleetData, isLoading: fleetLoading } = useSWR(
    'fleet',
    getFleetBalance,
    { refreshInterval: POLL_MEDIUM }
  )

  async function handleMarkRead(id: number) {
    await markAlertRead(id)
    mutateAlerts(
      alerts.map((a) => (a.id === id ? { ...a, is_read: true } : a)),
      false
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* KPI Row */}
        <KPICards data={kpi} isLoading={kpiLoading} />

        {/* Map + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map — 2/3 width */}
          <div className="lg:col-span-2 h-[420px]">
            <div className="h-full rounded-xl overflow-hidden shadow-sm border border-slate-200">
              <div className="bg-white px-5 py-3 border-b border-slate-100 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-800">Live Fleet Map</h2>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>{trucks.length} trucks</span>
                  <span>{warehouses.length} hubs</span>
                  <span>{borders.length} borders</span>
                </div>
              </div>
              <div style={{ height: '371px' }}>
                <LiveMap
                  trucks={trucks}
                  warehouses={warehouses}
                  borders={borders}
                  anomalies={anomalies}
                />
              </div>
            </div>
          </div>

          {/* Alerts — 1/3 width */}
          <div className="lg:col-span-1">
            <AlertsFeed alerts={alerts} onMarkRead={handleMarkRead} />
          </div>
        </div>

        {/* Shipments + Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Shipments table — 2/3 */}
          <div className="lg:col-span-2">
            <ShipmentsTable
              shipments={shipmentsData?.items || []}
              isLoading={shipmentsLoading}
            />
          </div>

          {/* Warehouse + Border panels — 1/3 */}
          <div className="lg:col-span-1 space-y-4">
            <WarehousePanel warehouses={warehouses} />
            <BorderPanel borders={borders} />
          </div>
        </div>

        {/* Dispatcher Actions + Route Optimization */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DispatcherPanel data={dispatcherData} isLoading={dispatcherLoading} />
          <RouteOptimizationPanel data={routeData} isLoading={routeLoading} />
        </div>

        {/* Fleet Load Balancing — full width */}
        <FleetBalancePanel data={fleetData} isLoading={fleetLoading} />
      </main>

      <AICopilot />
    </div>
  )
}
