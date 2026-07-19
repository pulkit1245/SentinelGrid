/**
 * sensorMapConfig.ts
 * 
 * Static floor plan configuration for the SentinelGrid SCADA sensor map.
 * 
 * Zone polygons are defined in SVG coordinate space (1200 x 800 viewBox).
 * Sensor positions are (x, y) within that same coordinate space.
 * 
 * To switch from simulated to real IoT sensors: replace this file's
 * INITIAL_SENSORS data with data fetched from the real backend API.
 * All components depend only on the SensorMarker interface, not this file.
 */

import type { SensorMarker } from '../types'

export interface ZoneConfig {
  zone_id: string
  zone_name: string
  points: string           // SVG polygon points string
  label_x: number
  label_y: number
  center_x: number
  center_y: number
}

// ── Zone Polygons ────────────────────────────────────────────────────────────
// Laid out as a realistic industrial plant floor plan in 1200x800 space.
// 
//   [Degassing Bay]   [Cast Floor]   [Tank Farm  ]
//   [Loading Dock ]   [Comp. House]  [Control Room]
//
export const ZONE_CONFIGS: ZoneConfig[] = [
  {
    zone_id:    'zone-01-degassing',
    zone_name:  'Degassing Bay',
    points:     '20,20 380,20 380,340 20,340',
    label_x:    200,
    label_y:    45,
    center_x:   200,
    center_y:   180,
  },
  {
    zone_id:    'zone-02-castfloor',
    zone_name:  'Cast Floor',
    points:     '400,20 760,20 760,340 400,340',
    label_x:    580,
    label_y:    45,
    center_x:   580,
    center_y:   180,
  },
  {
    zone_id:    'zone-03-tankfarm',
    zone_name:  'Tank Farm',
    points:     '780,20 1180,20 1180,340 780,340',
    label_x:    980,
    label_y:    45,
    center_x:   980,
    center_y:   180,
  },
  {
    zone_id:    'zone-04-loadingdock',
    zone_name:  'Loading Dock',
    points:     '20,360 380,360 380,780 20,780',
    label_x:    200,
    label_y:    390,
    center_x:   200,
    center_y:   570,
  },
  {
    zone_id:    'zone-05-compressor',
    zone_name:  'Compressor House',
    points:     '400,360 760,360 760,780 400,780',
    label_x:    580,
    label_y:    390,
    center_x:   580,
    center_y:   570,
  },
  {
    zone_id:    'zone-06-control',
    zone_name:  'Control Room',
    points:     '780,360 1180,360 1180,780 780,780',
    label_x:    980,
    label_y:    390,
    center_x:   980,
    center_y:   570,
  },
]

// Control room centroid — connection lines draw toward here
export const CONTROL_ROOM_CENTER = { x: 980, y: 570 }

// ── Initial Sensor Definitions ───────────────────────────────────────────────
// These match the simulator's zone_ids and sensor_types exactly.
// battery_level and signal_strength are simulated metadata.

export const INITIAL_SENSORS: SensorMarker[] = [
  // ── Degassing Bay ──
  { id: 'sg-01-gas-1',   zone_id: 'zone-01-degassing', zone_name: 'Degassing Bay',    name: 'Gas Sensor A1',       sensor_type: 'gas',         unit: 'ppm',    x:  80, y:  90,  current_value: 8.0,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 92, signal_strength: 88 },
  { id: 'sg-01-gas-2',   zone_id: 'zone-01-degassing', zone_name: 'Degassing Bay',    name: 'Gas Sensor A2',       sensor_type: 'gas',         unit: 'ppm',    x: 220, y: 130,  current_value: 8.5,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 85, signal_strength: 91 },
  { id: 'sg-01-temp-1',  zone_id: 'zone-01-degassing', zone_name: 'Degassing Bay',    name: 'Temp Sensor A1',      sensor_type: 'temperature', unit: 'C',      x: 330, y:  70,  current_value: 34.0,  threshold_warning: 60,  threshold_critical: 80,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 78, signal_strength: 95 },
  { id: 'sg-01-pres-1',  zone_id: 'zone-01-degassing', zone_name: 'Degassing Bay',    name: 'Pressure Sensor A1',  sensor_type: 'pressure',    unit: 'kPa',    x: 100, y: 280,  current_value: 101.3, threshold_warning: 300, threshold_critical: 400, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 96, signal_strength: 82 },
  { id: 'sg-01-vib-1',   zone_id: 'zone-01-degassing', zone_name: 'Degassing Bay',    name: 'Vibration Sensor A1', sensor_type: 'vibration',   unit: 'mm/s',   x: 290, y: 290,  current_value: 1.1,   threshold_warning: 4.5, threshold_critical: 7.1, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 88, signal_strength: 76 },

  // ── Cast Floor ──
  { id: 'sg-02-temp-1',  zone_id: 'zone-02-castfloor', zone_name: 'Cast Floor',       name: 'Temp Sensor B1',      sensor_type: 'temperature', unit: 'C',      x: 470, y:  80,  current_value: 55.0,  threshold_warning: 60,  threshold_critical: 80,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 71, signal_strength: 84 },
  { id: 'sg-02-temp-2',  zone_id: 'zone-02-castfloor', zone_name: 'Cast Floor',       name: 'Temp Sensor B2',      sensor_type: 'temperature', unit: 'C',      x: 650, y: 150,  current_value: 58.0,  threshold_warning: 60,  threshold_critical: 80,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 65, signal_strength: 79 },
  { id: 'sg-02-gas-1',   zone_id: 'zone-02-castfloor', zone_name: 'Cast Floor',       name: 'Gas Sensor B1',       sensor_type: 'gas',         unit: 'ppm',    x: 540, y: 250,  current_value: 2.0,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 90, signal_strength: 93 },
  { id: 'sg-02-vib-1',   zone_id: 'zone-02-castfloor', zone_name: 'Cast Floor',       name: 'Vibration Sensor B1', sensor_type: 'vibration',   unit: 'mm/s',   x: 730, y: 290,  current_value: 3.2,   threshold_warning: 4.5, threshold_critical: 7.1, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 83, signal_strength: 87 },
  { id: 'sg-02-smoke-1', zone_id: 'zone-02-castfloor', zone_name: 'Cast Floor',       name: 'Smoke Detector B1',   sensor_type: 'smoke',       unit: 'ppm',    x: 460, y: 310,  current_value: 0.5,   threshold_warning: 20,  threshold_critical: 50,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 97, signal_strength: 91 },

  // ── Tank Farm ──
  { id: 'sg-03-gas-1',   zone_id: 'zone-03-tankfarm',  zone_name: 'Tank Farm',        name: 'Gas Sensor C1',       sensor_type: 'gas',         unit: 'ppm',    x: 850, y:  80,  current_value: 5.0,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 74, signal_strength: 80 },
  { id: 'sg-03-gas-2',   zone_id: 'zone-03-tankfarm',  zone_name: 'Tank Farm',        name: 'Gas Sensor C2',       sensor_type: 'gas',         unit: 'ppm',    x: 1050, y: 130, current_value: 5.5,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 86, signal_strength: 77 },
  { id: 'sg-03-pres-1',  zone_id: 'zone-03-tankfarm',  zone_name: 'Tank Farm',        name: 'Pressure Sensor C1',  sensor_type: 'pressure',    unit: 'kPa',    x: 920, y: 200,  current_value: 250.0, threshold_warning: 300, threshold_critical: 400, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 91, signal_strength: 89 },
  { id: 'sg-03-pres-2',  zone_id: 'zone-03-tankfarm',  zone_name: 'Tank Farm',        name: 'Pressure Sensor C2',  sensor_type: 'pressure',    unit: 'kPa',    x: 1130, y: 270, current_value: 252.0, threshold_warning: 300, threshold_critical: 400, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 69, signal_strength: 72 },
  { id: 'sg-03-hum-1',   zone_id: 'zone-03-tankfarm',  zone_name: 'Tank Farm',        name: 'Humidity Sensor C1',  sensor_type: 'humidity',    unit: '%',      x: 800, y: 290,  current_value: 55.0,  threshold_warning: 75,  threshold_critical: 90,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 82, signal_strength: 85 },

  // ── Loading Dock ──
  { id: 'sg-04-gas-1',   zone_id: 'zone-04-loadingdock', zone_name: 'Loading Dock',   name: 'Gas Sensor D1',       sensor_type: 'gas',         unit: 'ppm',    x:  80, y: 430,  current_value: 3.0,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 93, signal_strength: 90 },
  { id: 'sg-04-temp-1',  zone_id: 'zone-04-loadingdock', zone_name: 'Loading Dock',   name: 'Temp Sensor D1',      sensor_type: 'temperature', unit: 'C',      x: 260, y: 480,  current_value: 26.0,  threshold_warning: 60,  threshold_critical: 80,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 77, signal_strength: 83 },
  { id: 'sg-04-vib-1',   zone_id: 'zone-04-loadingdock', zone_name: 'Loading Dock',   name: 'Vibration Sensor D1', sensor_type: 'vibration',   unit: 'mm/s',   x: 130, y: 650,  current_value: 1.8,   threshold_warning: 4.5, threshold_critical: 7.1, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 88, signal_strength: 76 },
  { id: 'sg-04-water-1', zone_id: 'zone-04-loadingdock', zone_name: 'Loading Dock',   name: 'Water Level D1',      sensor_type: 'water_level', unit: 'mm',     x: 330, y: 720,  current_value: 10.0,  threshold_warning: 50,  threshold_critical: 100, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 95, signal_strength: 88 },

  // ── Compressor House ──
  { id: 'sg-05-pres-1',  zone_id: 'zone-05-compressor',  zone_name: 'Compressor House', name: 'Pressure Sensor E1', sensor_type: 'pressure',    unit: 'kPa',    x: 460, y: 440,  current_value: 310.0, threshold_warning: 350, threshold_critical: 400, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 80, signal_strength: 86 },
  { id: 'sg-05-pres-2',  zone_id: 'zone-05-compressor',  zone_name: 'Compressor House', name: 'Pressure Sensor E2', sensor_type: 'pressure',    unit: 'kPa',    x: 650, y: 500,  current_value: 315.0, threshold_warning: 350, threshold_critical: 400, status: 'healthy', last_updated: new Date().toISOString(), battery_level: 72, signal_strength: 81 },
  { id: 'sg-05-temp-1',  zone_id: 'zone-05-compressor',  zone_name: 'Compressor House', name: 'Temp Sensor E1',     sensor_type: 'temperature', unit: 'C',      x: 520, y: 620,  current_value: 42.0,  threshold_warning: 60,  threshold_critical: 80,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 87, signal_strength: 92 },
  { id: 'sg-05-vib-1',   zone_id: 'zone-05-compressor',  zone_name: 'Compressor House', name: 'Vibration Sensor E1',sensor_type: 'vibration',   unit: 'mm/s',   x: 700, y: 700,  current_value: 4.5,   threshold_warning: 4.5, threshold_critical: 7.1, status: 'warning', last_updated: new Date().toISOString(), battery_level: 64, signal_strength: 74 },
  { id: 'sg-05-smoke-1', zone_id: 'zone-05-compressor',  zone_name: 'Compressor House', name: 'Smoke Detector E1',  sensor_type: 'smoke',       unit: 'ppm',    x: 430, y: 750,  current_value: 1.2,   threshold_warning: 20,  threshold_critical: 50,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 98, signal_strength: 94 },

  // ── Control Room ──
  { id: 'sg-06-gas-1',   zone_id: 'zone-06-control',     zone_name: 'Control Room',     name: 'Gas Sensor F1',      sensor_type: 'gas',         unit: 'ppm',    x: 860, y: 430,  current_value: 0.5,   threshold_warning: 15,  threshold_critical: 25,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 99, signal_strength: 99 },
  { id: 'sg-06-temp-1',  zone_id: 'zone-06-control',     zone_name: 'Control Room',     name: 'Temp Sensor F1',     sensor_type: 'temperature', unit: 'C',      x: 1050, y: 470, current_value: 22.0,  threshold_warning: 35,  threshold_critical: 45,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 97, signal_strength: 99 },
  { id: 'sg-06-hum-1',   zone_id: 'zone-06-control',     zone_name: 'Control Room',     name: 'Humidity Sensor F1', sensor_type: 'humidity',    unit: '%',      x: 950, y: 620,  current_value: 45.0,  threshold_warning: 70,  threshold_critical: 85,  status: 'healthy', last_updated: new Date().toISOString(), battery_level: 96, signal_strength: 98 },
]

// ── Sensor type display metadata ─────────────────────────────────────────────
export const SENSOR_TYPE_META: Record<string, { label: string; icon: string; color: string }> = {
  gas:         { label: 'Gas',         icon: '💨', color: '#d29922' },
  temperature: { label: 'Temperature', icon: '🌡️', color: '#e85d04' },
  pressure:    { label: 'Pressure',    icon: '⚙️', color: '#58a6ff' },
  vibration:   { label: 'Vibration',   icon: '📳', color: '#a371f7' },
  smoke:       { label: 'Smoke',       icon: '🔥', color: '#f85149' },
  humidity:    { label: 'Humidity',    icon: '💧', color: '#3fb950' },
  water_level: { label: 'Water Level', icon: '🌊', color: '#1f6feb' },
}

// ── Status display metadata ──────────────────────────────────────────────────
export const STATUS_META = {
  healthy:   { color: '#3fb950', label: 'Healthy',   glow: 'rgba(63,185,80,0.5)' },
  warning:   { color: '#d29922', label: 'Warning',   glow: 'rgba(210,153,34,0.5)' },
  high_risk: { color: '#e85d04', label: 'High Risk', glow: 'rgba(232,93,4,0.5)' },
  critical:  { color: '#f85149', label: 'Critical',  glow: 'rgba(248,81,73,0.6)' },
  offline:   { color: '#484f58', label: 'Offline',   glow: 'rgba(72,79,88,0.3)' },
} as const
