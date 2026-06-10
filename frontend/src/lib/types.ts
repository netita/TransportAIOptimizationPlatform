export type ShipmentStatus =
  | 'PENDING'
  | 'IN_TRANSIT'
  | 'AT_BORDER'
  | 'AT_WAREHOUSE'
  | 'DELIVERED'
  | 'DELAYED'

export type TruckStatus =
  | 'MOVING'
  | 'IDLE'
  | 'AT_WAREHOUSE'
  | 'AT_BORDER'
  | 'OFFLINE'

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type BorderStatus = 'NORMAL' | 'SLOW' | 'CONGESTED' | 'CLOSED'

export type AlertType =
  | 'DELAY'
  | 'CONGESTION'
  | 'BORDER'
  | 'ANOMALY'
  | 'SLA_RISK'
  | 'ROUTE'

export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL'

export interface Shipment {
  id: number
  shipment_id: string
  origin: string
  destination: string
  origin_lat: number
  origin_lon: number
  dest_lat: number
  dest_lon: number
  distance_km: number
  carrier: string
  priority: Priority
  status: ShipmentStatus
  eta: string
  actual_arrival: string | null
  delay_minutes: number | null
  risk_score: number
  truck_id: string | null
  created_at: string
  updated_at: string
  predicted_delay_minutes: number | null
  delay_probability: number | null
  prediction_confidence: number | null
  top_factors: Array<{ factor: string; impact: string }> | null
}

export interface ShipmentPrediction {
  shipment_id: string
  predicted_delay_minutes: number
  delay_probability: number
  confidence: number
  top_factors: Array<{ factor: string; impact: string }>
}

export interface ModelMetrics {
  mae: number
  rmse: number
  accuracy: number
  auc: number
  total_samples: number
  trained_at: string
  model_version: string
}

export interface Truck {
  id: number
  truck_id: string
  lat: number
  lon: number
  speed_kmh: number
  heading: number
  status: TruckStatus
  current_shipment_id: string | null
  last_updated: string
}

export interface Warehouse {
  id: number
  name: string
  city: string
  country: string
  lat: number
  lon: number
  total_docks: number
  available_docks: number
  incoming_trucks: number
  avg_unload_time_min: number
  queue_time_min: number
  congestion_risk: number
  updated_at: string
}

export interface Border {
  id: number
  name: string
  lat: number
  lon: number
  wait_time_min: number
  inspection_rate: number
  weather_risk: number
  status: BorderStatus
  updated_at: string
}

export interface Alert {
  id: number
  alert_type: AlertType
  severity: AlertSeverity
  message: string
  shipment_id: string | null
  truck_id: string | null
  is_read: boolean
  created_at: string
}

export interface KPIDashboard {
  active_shipments: number
  delayed_count: number
  at_risk_count: number
  trucks_online: number
  border_alerts: number
  on_time_rate: number
  avg_delay_minutes: number
}

export interface CopilotMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ShipmentListResponse {
  items: Shipment[]
  total: number
}

export interface TimelinePoint {
  hour: string
  created: number
  delivered: number
  delayed: number
}

export interface CongestionData {
  name: string
  city: string
  congestion_risk: number
  queue_time_min: number
  available_docks: number
  total_docks: number
}

export interface AnomalyResult {
  entity_id: string
  entity_type: 'truck' | 'shipment'
  anomaly_score: number
  is_anomaly: boolean
  reason: string
  severity: 'INFO' | 'WARNING' | 'CRITICAL'
}

export type RouteUrgency = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface RouteOption {
  name: string
  total_time_min: number
  border_delay_min: number
  distance_km: number
  is_recommended: boolean
}

export interface BorderCheckpoint {
  name: string
  wait_min: number
}

export interface RouteRecommendation {
  shipment_id: string
  truck_id: string | null
  origin: string
  destination: string
  priority: Priority
  status: ShipmentStatus
  current_route: string
  recommended_route: string
  should_reroute: boolean
  savings_minutes: number
  urgency: RouteUrgency
  current_total_time_min: number
  recommended_total_time_min: number
  current_border_delay_min: number
  recommended_border_delay_min: number
  bottlenecks: string[]
  border_breakdown: BorderCheckpoint[]
  reason: string
  all_options: RouteOption[]
}

export interface RouteOptimizationSummary {
  total_analyzed: number
  reroute_recommended: number
  total_savings_minutes: number
  worst_bottleneck: string | null
}

export interface RouteOptimizationResponse {
  recommendations: RouteRecommendation[]
  summary: RouteOptimizationSummary
}

export type DispatcherActionType = 'REROUTE' | 'ESCALATE' | 'INVESTIGATE' | 'HOLD'

export interface DispatcherAction {
  id: string
  type: DispatcherActionType
  urgency: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  title: string
  description: string
  action: string
  entity_id: string
  entity_type: 'shipment' | 'truck' | 'warehouse'
  impact_minutes: number | null
  impact_label: string
}

export interface DispatcherSummary {
  total: number
  critical: number
  high: number
  total_saveable_minutes: number
}

export interface DispatcherResponse {
  actions: DispatcherAction[]
  summary: DispatcherSummary
}

export type CorridorLoadLevel = 'CRITICAL' | 'HIGH' | 'BALANCED' | 'LOW'

export interface CorridorLoad {
  corridor_id: string
  corridor_name: string
  active_trucks: number
  load_level: CorridorLoadLevel
  recommendation: string
}

export interface FleetAssignment {
  truck_id: string
  shipment_id: string
  priority: Priority
  distance_km: number
  score: number
  truck_status: string
  origin: string
  destination: string
  reason: string
}

export interface FleetSummary {
  total_trucks: number
  available_trucks: number
  active_trucks: number
  pending_shipments: number
  assignments_made: number
  balance_score: number
  overloaded_corridors: number
}

export interface FleetBalanceResponse {
  assignments: FleetAssignment[]
  unassigned_shipments: Array<{ shipment_id: string; priority: Priority; origin: string; destination: string; reason: string }>
  idle_trucks: Array<{ truck_id: string; status: string; lat: number; lon: number }>
  corridor_load: CorridorLoad[]
  summary: FleetSummary
}
