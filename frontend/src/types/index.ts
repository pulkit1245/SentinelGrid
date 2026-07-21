export interface Zone {
  id: string
  plant_id: string
  name: string
  hazard_class: 'gas' | 'thermal' | 'mechanical' | 'confined_space' | 'general'
  polygon_geojson?: GeoJSONPolygon | null
  current_risk_score: number
  active_permit_count: number
  active_alert_count: number
  slug?: string
  sensors?: Sensor[]
}

export interface GeoJSONPolygon {
  type: 'Polygon'
  coordinates: number[][][]
}

export interface Sensor {
  id: string
  zone_id: string
  name: string
  sensor_type: 'gas' | 'temperature' | 'pressure' | 'vibration' | 'smoke' | 'humidity' | 'water_level'
  unit: string
  is_active: boolean
  statutory_threshold?: number
  warning_threshold?: number
}

export type SensorStatus = 'healthy' | 'warning' | 'high_risk' | 'critical' | 'offline'

export interface SensorMarker {
  id: string
  zone_id: string
  zone_name: string
  name: string
  sensor_type: 'gas' | 'temperature' | 'pressure' | 'vibration' | 'smoke' | 'humidity' | 'water_level'
  unit: string
  x: number
  y: number
  current_value: number
  threshold_warning: number
  threshold_critical: number
  status: SensorStatus
  last_updated: string
  battery_level: number    // simulated 0-100
  signal_strength: number  // simulated 0-100
}

export interface ZoneRisk {
  zone_id: string
  zone_name: string
  risk_level: SensorStatus
  sensor_count: number
  healthy: number
  warning: number
  high_risk: number
  critical: number
  offline: number
  aggregate_score: number  // 0-100
}

export interface SensorIncident {
  id: string
  sensor_id: string
  sensor_name: string
  zone_name: string
  old_status: SensorStatus
  new_status: SensorStatus
  value: number
  unit: string
  timestamp: string
}

export interface SensorReading {
  sensor_id: string
  reading_value: number
  recorded_at: string
}

export interface Permit {
  id: string
  zone_id: string
  permit_type: 'hot_work' | 'confined_space' | 'excavation' | 'electrical'
  issued_to_worker_id?: string
  issued_by_user_id?: string
  valid_from: string
  valid_to: string
  status: 'active' | 'closed' | 'revoked'
  notes?: string
}

export interface GraphPathNode {
  node: string
  rel?: string
  next?: string
  value?: number
  threshold?: number
}

export interface Alert {
  id: string
  zone_id: string
  severity: 'info' | 'watch' | 'warning' | 'critical'
  title: string
  description?: string
  graph_path: GraphPathNode[]
  triggered_at: string
  confirmed_by?: string | null
  confirmed_at?: string | null
  is_active: boolean
  evidence_snapshot_id?: string | null
}

export interface Worker {
  id: string
  plant_id: string
  name: string
  badge_id?: string
  role?: string
  phone?: string
  is_on_shift: boolean
}

export interface User {
  id: string
  email: string
  role: 'safety_officer' | 'plant_admin' | 'auditor'
  full_name?: string
  is_active: boolean
}

export interface WSMessage {
  type: 'zone_risk_update' | 'new_alert' | 'alert_confirmed' | 'permit_created' | 'permit_revoked' |
        'cv_event' | 'heartbeat' | 'pong' | 'sensor_update' | 'zone_health_update' | 'simulator_tick'
  timestamp: string
  payload: Record<string, unknown>
}

export interface RAGResponse {
  answer: string
  sources?: string[]
  citations?: Array<{ source: string; clause: string; excerpt: string }>
  confidence?: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface BlackBoxEntry {
  sim_time_s: number
  zone_id: string
  hard_rule_violation?: {
    sensor_type: string
    value: number
    threshold: number
  } | null
  compound_finding_summary?: {
    triggered: boolean
    reasons: string[]
    signal_count: number
  } | null
  permit_violations_summary?: Array<{
    reason: string
    severity: string
  }>
  corroborating_signals: string[]
  decision: 'critical' | 'advisory' | 'clear'
  dispatched: boolean
}

export interface TranscriptLine {
  speaker: string
  message: string
}

export interface AgentTranscriptResponse {
  zone_id: string
  sim_time_s?: number | null
  decision: string
  transcript: string
  lines: TranscriptLine[]
}

