import type {
  Alert,
  AnomalyResult,
  Border,
  CopilotMessage,
  DispatcherResponse,
  FleetBalanceResponse,
  KPIDashboard,
  ModelMetrics,
  RouteOptimizationResponse,
  Shipment,
  ShipmentListResponse,
  ShipmentPrediction,
  TimelinePoint,
  CongestionData,
  Truck,
  Warehouse,
} from './types'

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText} for ${path}`)
  }
  return res.json() as Promise<T>
}

export async function getKPI(): Promise<KPIDashboard> {
  return apiFetch<KPIDashboard>('/api/v1/analytics/kpi')
}

export async function getShipments(params?: {
  status?: string
  priority?: string
  carrier?: string
  skip?: number
  limit?: number
}): Promise<ShipmentListResponse> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.priority) qs.set('priority', params.priority)
  if (params?.carrier) qs.set('carrier', params.carrier)
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return apiFetch<ShipmentListResponse>(
    `/api/v1/shipments/${query ? `?${query}` : ''}`
  )
}

export async function getLiveTrucks(): Promise<Truck[]> {
  return apiFetch<Truck[]>('/api/v1/gps/live')
}

export async function getWarehouses(): Promise<Warehouse[]> {
  return apiFetch<Warehouse[]>('/api/v1/warehouse/')
}

export async function getBorders(): Promise<Border[]> {
  return apiFetch<Border[]>('/api/v1/borders/')
}

export async function getAlerts(): Promise<Alert[]> {
  return apiFetch<Alert[]>('/api/v1/analytics/alerts')
}

export async function markAlertRead(id: number): Promise<void> {
  await apiFetch<{ status: string }>(`/api/v1/analytics/alerts/${id}/read`, {
    method: 'PUT',
  })
}

export async function chatCopilot(
  message: string,
  history: CopilotMessage[]
): Promise<{ response: string }> {
  return apiFetch<{ response: string }>('/api/v1/copilot/chat', {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  })
}

export async function getShipmentTimeline(): Promise<TimelinePoint[]> {
  return apiFetch<TimelinePoint[]>('/api/v1/analytics/shipment-timeline')
}

export async function getCongestionHeatmap(): Promise<CongestionData[]> {
  return apiFetch<CongestionData[]>('/api/v1/analytics/congestion-heatmap')
}

export async function getModelMetrics(): Promise<ModelMetrics> {
  return apiFetch<ModelMetrics>('/api/v1/analytics/model-metrics')
}

export async function getShipment(id: string): Promise<Shipment> {
  return apiFetch<Shipment>(`/api/v1/shipments/${id}`)
}

export async function getShipmentPrediction(id: string): Promise<ShipmentPrediction> {
  return apiFetch<ShipmentPrediction>(`/api/v1/shipments/${id}/prediction`)
}

export async function getPredictionsSummary(): Promise<{
  avg_predicted_delay: number
  pct_likely_delayed: number
  top_factors: Array<{ factor: string; count: number }>
}> {
  return apiFetch('/api/v1/analytics/predictions/summary')
}

export async function getAnomalies(): Promise<AnomalyResult[]> {
  return apiFetch<AnomalyResult[]>('/api/v1/analytics/anomalies')
}

export async function getRouteRecommendations(): Promise<RouteOptimizationResponse> {
  return apiFetch<RouteOptimizationResponse>('/api/v1/routes/recommendations')
}

export async function getDispatcherRecommendations(): Promise<DispatcherResponse> {
  return apiFetch<DispatcherResponse>('/api/v1/dispatcher/recommendations')
}

export async function getFleetBalance(): Promise<FleetBalanceResponse> {
  return apiFetch<FleetBalanceResponse>('/api/v1/fleet/balance')
}
