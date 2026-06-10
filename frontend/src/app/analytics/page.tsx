'use client'

import useSWR from 'swr'
import Header from '@/components/Header'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import {
  getShipmentTimeline,
  getCongestionHeatmap,
  getShipments,
  getBorders,
  getKPI,
  getModelMetrics,
} from '@/lib/api'
import clsx from 'clsx'

const REFRESH_INTERVAL = 30000

const PRIORITY_COLORS = {
  CRITICAL: '#dc2626',
  HIGH: '#d97706',
  MEDIUM: '#2563eb',
  LOW: '#94a3b8',
}

const STATUS_COLORS = {
  IN_TRANSIT: '#2563eb',
  DELAYED: '#dc2626',
  AT_BORDER: '#d97706',
  AT_WAREHOUSE: '#7c3aed',
  DELIVERED: '#16a34a',
  PENDING: '#94a3b8',
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-800">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function LoadingChart() {
  return (
    <div className="h-48 flex items-center justify-center">
      <div className="w-full h-full bg-slate-50 rounded-lg animate-pulse" />
    </div>
  )
}

export default function AnalyticsPage() {
  const { data: timeline, isLoading: tlLoading } = useSWR(
    'timeline',
    getShipmentTimeline,
    { refreshInterval: REFRESH_INTERVAL }
  )
  const { data: congestion, isLoading: cgLoading } = useSWR(
    'congestion',
    getCongestionHeatmap,
    { refreshInterval: REFRESH_INTERVAL }
  )
  const { data: shipmentsData } = useSWR(
    'shipments-analytics',
    () => getShipments({ limit: 500 }),
    { refreshInterval: REFRESH_INTERVAL }
  )
  const { data: borders } = useSWR('borders-analytics', getBorders, {
    refreshInterval: REFRESH_INTERVAL,
  })
  const { data: kpi } = useSWR('kpi-analytics', getKPI, {
    refreshInterval: REFRESH_INTERVAL,
  })
  const { data: modelMetrics } = useSWR('model-metrics', getModelMetrics, {
    refreshInterval: REFRESH_INTERVAL,
    shouldRetryOnError: false,
  })

  const shipments = shipmentsData?.items || []

  // Priority breakdown for pie chart
  const priorityCounts = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => ({
    name: p,
    value: shipments.filter((s) => s.priority === p).length,
    color: PRIORITY_COLORS[p as keyof typeof PRIORITY_COLORS],
  }))

  // Status breakdown for bar chart
  const statusCounts = Object.keys(STATUS_COLORS).map((s) => ({
    name: s.replace('_', ' '),
    count: shipments.filter((sh) => sh.status === s).length,
    color: STATUS_COLORS[s as keyof typeof STATUS_COLORS],
  }))

  // Border wait times
  const borderData = borders
    ? [...borders].sort((a, b) => b.wait_time_min - a.wait_time_min)
    : []

  const onTimePct = kpi ? Math.round(kpi.on_time_rate * 100) : 0

  // AI Predicted vs Actual delays — last 10 shipments that have both values
  const predictedVsActual = shipments
    .filter(
      (s) =>
        s.predicted_delay_minutes !== null &&
        s.predicted_delay_minutes !== undefined
    )
    .slice(0, 10)
    .map((s) => ({
      id: s.shipment_id.replace('DISC-', ''),
      predicted: Math.round(s.predicted_delay_minutes ?? 0),
      actual: s.delay_minutes ?? 0,
    }))

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
          <p className="text-sm text-slate-500 mt-1">
            Operational insights and performance metrics for Discordia's logistics network.
          </p>
        </div>

        {/* AI Model Performance section */}
        <div>
          <h2 className="text-base font-semibold text-slate-700 mb-3 flex items-center gap-2">
            AI Model Performance
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-violet-100 text-violet-700 border border-violet-200">
              XGBoost ML
            </span>
          </h2>
          {modelMetrics ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                <div className="text-2xl font-bold text-blue-700">
                  {modelMetrics.mae.toFixed(1)}
                  <span className="text-sm font-normal text-blue-500 ml-1">min</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">ETA Prediction MAE</div>
              </div>
              <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                <div className="text-2xl font-bold text-green-700">
                  {(modelMetrics.accuracy * 100).toFixed(1)}
                  <span className="text-sm font-normal text-green-500 ml-1">%</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Delay Classification Accuracy</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <div className="text-2xl font-bold text-slate-700">
                  {modelMetrics.total_samples.toLocaleString()}
                </div>
                <div className="text-xs text-slate-500 mt-1">Model Training Samples</div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="bg-slate-50 rounded-xl p-4 border border-slate-100 animate-pulse h-20"
                />
              ))}
            </div>
          )}
        </div>

        {/* Summary stats */}
        {kpi && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: 'On-Time Rate',
                value: `${onTimePct}%`,
                color: onTimePct >= 80 ? 'text-green-600' : 'text-amber-600',
                bg: onTimePct >= 80 ? 'bg-green-50' : 'bg-amber-50',
              },
              {
                label: 'Active Shipments',
                value: kpi.active_shipments,
                color: 'text-blue-700',
                bg: 'bg-blue-50',
              },
              {
                label: 'Avg Delay',
                value: `${Math.round(kpi.avg_delay_minutes)}min`,
                color: kpi.avg_delay_minutes > 60 ? 'text-red-600' : 'text-slate-700',
                bg: kpi.avg_delay_minutes > 60 ? 'bg-red-50' : 'bg-slate-50',
              },
              {
                label: 'At Risk',
                value: kpi.at_risk_count,
                color: kpi.at_risk_count > 0 ? 'text-red-600' : 'text-green-600',
                bg: kpi.at_risk_count > 0 ? 'bg-red-50' : 'bg-green-50',
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className={clsx(
                  'rounded-xl p-4 border border-transparent',
                  stat.bg
                )}
              >
                <div className={clsx('text-2xl font-bold', stat.color)}>
                  {stat.value}
                </div>
                <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Charts row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Shipments timeline */}
          <ChartCard
            title="Shipment Activity (Last 24h)"
            subtitle="Hourly breakdown of created, delivered, and delayed shipments"
          >
            {tlLoading ? (
              <LoadingChart />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={timeline || []}
                  margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    interval={3}
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: '1px solid #e2e8f0',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="created" fill="#2563eb" name="Created" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="delivered" fill="#16a34a" name="Delivered" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="delayed" fill="#dc2626" name="Delayed" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* Shipments by status */}
          <ChartCard
            title="Shipments by Status"
            subtitle="Current distribution across all status categories"
          >
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={statusCounts}
                margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 9, fill: '#94a3b8' }}
                  angle={-20}
                  textAnchor="end"
                  height={40}
                />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: '1px solid #e2e8f0',
                  }}
                />
                <Bar dataKey="count" name="Count" radius={[3, 3, 0, 0]}>
                  {statusCounts.map((entry, i) => (
                    <Cell key={`cell-${i}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* Charts row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Priority pie */}
          <ChartCard
            title="Shipments by Priority"
            subtitle="Breakdown of active shipments by priority level"
          >
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={priorityCounts.filter((p) => p.value > 0)}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {priorityCounts.map((entry, i) => (
                      <Cell key={`cell-${i}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: '1px solid #e2e8f0',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {priorityCounts.map((p) => (
                  <div key={p.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-sm flex-shrink-0"
                        style={{ backgroundColor: p.color }}
                      />
                      <span className="text-xs text-slate-600 capitalize">
                        {p.name.charAt(0) + p.name.slice(1).toLowerCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-semibold text-slate-800">
                        {p.value}
                      </span>
                      {shipments.length > 0 && (
                        <span className="text-xs text-slate-400">
                          ({Math.round((p.value / shipments.length) * 100)}%)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>

          {/* Border wait times */}
          <ChartCard
            title="Border Wait Times"
            subtitle="Current wait times at all monitored border crossings (minutes)"
          >
            {borders ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={borderData}
                  layout="vertical"
                  margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    unit="min"
                  />
                  <YAxis
                    dataKey="name"
                    type="category"
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    width={140}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: '1px solid #e2e8f0',
                    }}
                    formatter={(val: number) => [`${val} min`, 'Wait Time']}
                  />
                  <Bar dataKey="wait_time_min" name="Wait Time" radius={[0, 3, 3, 0]}>
                    {borderData.map((entry, i) => (
                      <Cell
                        key={`cell-${i}`}
                        fill={
                          entry.wait_time_min >= 90
                            ? '#dc2626'
                            : entry.wait_time_min >= 45
                            ? '#d97706'
                            : '#16a34a'
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <LoadingChart />
            )}
          </ChartCard>
        </div>

        {/* AI Predicted vs Actual Delays */}
        {predictedVsActual.length > 0 && (
          <ChartCard
            title="AI Predicted vs Actual Delays"
            subtitle="XGBoost predicted delay vs recorded actual delay for the most recent shipments (minutes)"
          >
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={predictedVsActual}
                margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="id"
                  tick={{ fontSize: 9, fill: '#94a3b8' }}
                  angle={-20}
                  textAnchor="end"
                  height={40}
                />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} unit="min" />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: '1px solid #e2e8f0',
                  }}
                  formatter={(val: number) => [`${val} min`]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar
                  dataKey="predicted"
                  name="Predicted (XGBoost)"
                  fill="#7c3aed"
                  radius={[2, 2, 0, 0]}
                />
                <Bar
                  dataKey="actual"
                  name="Actual"
                  fill="#dc2626"
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {/* Warehouse congestion */}
        <ChartCard
          title="Warehouse Congestion Levels"
          subtitle="Current congestion risk across all distribution hubs (0-100%)"
        >
          {cgLoading ? (
            <LoadingChart />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={congestion || []}
                margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="city"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#94a3b8' }}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  domain={[0, 1]}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: '1px solid #e2e8f0',
                  }}
                  formatter={(val: number) => [
                    `${Math.round(val * 100)}%`,
                    'Congestion',
                  ]}
                />
                <Bar
                  dataKey="congestion_risk"
                  name="Congestion Risk"
                  radius={[3, 3, 0, 0]}
                >
                  {(congestion || []).map((entry, i) => (
                    <Cell
                      key={`cell-${i}`}
                      fill={
                        entry.congestion_risk >= 0.7
                          ? '#dc2626'
                          : entry.congestion_risk >= 0.4
                          ? '#d97706'
                          : '#16a34a'
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </main>
    </div>
  )
}
