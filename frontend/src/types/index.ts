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
  sensor_type: 'gas' | 'temperature' | 'pressure' | 'vibration'
  unit: string
  is_active: boolean
  statutory_threshold?: number
  warning_threshold?: number
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
  type: 'zone_risk_update' | 'new_alert' | 'alert_confirmed' | 'permit_created' | 'permit_revoked' | 'cv_event' | 'heartbeat' | 'pong'
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
