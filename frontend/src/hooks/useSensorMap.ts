/**
 * useSensorMap.ts
 *
 * Central state hook for the SCADA Sensor Map.
 * - Maintains live SensorMarker[] state
 * - Subscribes to wsManager for "sensor_update" messages
 * - Derives ZoneRisk aggregations
 * - Tracks SensorIncident timeline
 * - Exposes triggerScenario() for manual test controls
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { SensorMarker, SensorStatus, ZoneRisk, SensorIncident } from '../types'
import { wsManager } from '../services/websocket'
import { INITIAL_SENSORS, ZONE_CONFIGS, STATUS_META } from '../services/sensorMapConfig'

// ── Zone Risk Aggregator ─────────────────────────────────────────────────────

export function aggregateZoneRisk(sensors: SensorMarker[]): ZoneRisk[] {
  return ZONE_CONFIGS.map((zone: { zone_id: string; zone_name: string }) => {
    const zoneSensors = sensors.filter(s => s.zone_id === zone.zone_id)
    const counts = { healthy: 0, warning: 0, high_risk: 0, critical: 0, offline: 0 }
    for (const s of zoneSensors) counts[s.status]++

    const total = zoneSensors.length || 1
    // Weighted score: healthy=0, warning=25, high_risk=60, critical=100, offline=40
    const score = Math.round(
      (counts.healthy * 0 + counts.warning * 25 + counts.high_risk * 60 +
       counts.critical * 100 + counts.offline * 40) / total
    )

    let risk_level: SensorStatus = 'healthy'
    if (counts.critical > 0) risk_level = 'critical'
    else if (counts.high_risk >= 2 || score >= 55) risk_level = 'high_risk'
    else if (counts.warning > 0 || score >= 20) risk_level = 'warning'
    else if (counts.offline > total * 0.3) risk_level = 'offline'

    return {
      zone_id: zone.zone_id,
      zone_name: zone.zone_name,
      risk_level,
      sensor_count: zoneSensors.length,
      ...counts,
      aggregate_score: score,
    }
  })
}

// ── Status calculator from reading ──────────────────────────────────────────

function calcStatus(value: number, warn: number, crit: number): SensorStatus {
  if (value >= crit) return 'critical'
  if (value >= warn * 0.9 && value < crit) return 'high_risk'
  if (value >= warn * 0.7) return 'warning'
  return 'healthy'
}

const VALID_STATUSES = new Set<string>(['healthy', 'warning', 'high_risk', 'critical', 'offline'])
function isValidStatus(s: string): s is SensorStatus {
  return VALID_STATUSES.has(s)
}

// ── Dashboard Stats ──────────────────────────────────────────────────────────

export interface SensorStats {
  total: number
  online: number
  offline: number
  warning: number
  critical: number
  active_zones: number
  highest_risk_zone: string
}

function calcStats(sensors: SensorMarker[], zoneRisks: ZoneRisk[]): SensorStats {
  const online  = sensors.filter(s => s.status !== 'offline').length
  const offline = sensors.filter(s => s.status === 'offline').length
  const warning = sensors.filter(s => s.status === 'warning' || s.status === 'high_risk').length
  const critical = sensors.filter(s => s.status === 'critical').length
  const active_zones = zoneRisks.filter(z => z.risk_level !== 'healthy' && z.risk_level !== 'offline').length
  const highest = [...zoneRisks].sort((a, b) => b.aggregate_score - a.aggregate_score)[0]

  return {
    total: sensors.length,
    online,
    offline,
    warning,
    critical,
    active_zones,
    highest_risk_zone: highest?.zone_name ?? 'None',
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UseSensorMapResult {
  sensors: SensorMarker[]
  zoneRisks: ZoneRisk[]
  incidents: SensorIncident[]
  stats: SensorStats
  selectedSensor: SensorMarker | null
  setSelectedSensor: (s: SensorMarker | null) => void
  hoveredSensor: SensorMarker | null
  setHoveredSensor: (s: SensorMarker | null) => void
  focusedSensorId: string | null
  triggerScenario: (type: ScenarioType, targetId?: string) => void
  clearIncidents: () => void
}

export type ScenarioType =
  | 'gas_leak'
  | 'fire'
  | 'pressure_failure'
  | 'sensor_offline'
  | 'reset_sensor'
  | 'reset_zone'

let incidentCounter = 0

export function useSensorMap(): UseSensorMapResult {
  const [sensors, setSensors] = useState<SensorMarker[]>(
    () => INITIAL_SENSORS.map(s => ({
      ...s,
      // Simulate slight variation in initial battery/signal
      battery_level: Math.max(20, s.battery_level + Math.floor(Math.random() * 10 - 5)),
      signal_strength: Math.max(30, s.signal_strength + Math.floor(Math.random() * 10 - 5)),
    }))
  )
  const [incidents, setIncidents] = useState<SensorIncident[]>([])
  const [selectedSensor, setSelectedSensor] = useState<SensorMarker | null>(null)
  const [hoveredSensor, setHoveredSensor] = useState<SensorMarker | null>(null)
  const [focusedSensorId, setFocusedSensorId] = useState<string | null>(null)
  const prevStatusRef = useRef<Record<string, SensorStatus>>({})

  // Derive on every sensor change
  const zoneRisks = aggregateZoneRisk(sensors)
  const stats = calcStats(sensors, zoneRisks)

  // ── Update sensor from WS ──────────────────────────────────────────────────
  useEffect(() => {
    const unsub = wsManager.subscribe((msg) => {
      if (msg.type !== 'sensor_update') return
      const p = msg.payload as {
        // Rich payload from simulator bridge (matches SensorMarker interface)
        id?: string              // sensor_id from simulator
        sensor_id?: string       // fallback field name
        zone_id?: string
        sensor_type?: string
        value?: number           // legacy minimal format
        current_value?: number   // rich format
        status?: SensorStatus
        battery_level?: number
        signal_strength?: number
        last_updated?: string
        incident_active?: boolean
        incident_type?: string | null
        threshold_warning?: number
        threshold_critical?: number
      }

      // Normalise field names — support both rich (bridge) and legacy formats
      const sensorId      = p.id ?? p.sensor_id
      const currentValue  = p.current_value ?? p.value
      const incomingStatus = p.status

      setSensors(prev => {
        const next = prev.map(s => {
          // Prefer exact sensor ID match (rich simulator payload)
          const idMatch   = sensorId && s.id === sensorId
          // Fallback: match by zone + sensor type (legacy backend ingest)
          const typeMatch = !sensorId && p.zone_id && s.zone_id === p.zone_id &&
                            p.sensor_type && s.sensor_type === mapSimTypeToSensorType(p.sensor_type)

          if (!idMatch && !typeMatch) return s
          if (currentValue === undefined) return s

          const newStatus: SensorStatus = incomingStatus && isValidStatus(incomingStatus)
            ? incomingStatus
            : calcStatus(currentValue, s.threshold_warning, s.threshold_critical)

          const oldStatus = prevStatusRef.current[s.id] ?? s.status

          if (newStatus !== oldStatus) {
            prevStatusRef.current[s.id] = newStatus
            const incident: SensorIncident = {
              id: `inc-${++incidentCounter}`,
              sensor_id: s.id,
              sensor_name: s.name,
              zone_name: s.zone_name,
              old_status: oldStatus,
              new_status: newStatus,
              value: currentValue,
              unit: s.unit,
              timestamp: p.last_updated ?? new Date().toISOString(),
            }
            setIncidents(prev => [incident, ...prev].slice(0, 50))
            if (newStatus === 'critical' || newStatus === 'high_risk') {
              setFocusedSensorId(s.id)
              setTimeout(() => setFocusedSensorId(null), 4000)
            }
          }

          return {
            ...s,
            current_value: Math.round(currentValue * 100) / 100,
            status: newStatus,
            last_updated: p.last_updated ?? new Date().toISOString(),
            // Use simulator-provided battery/signal if available, else drift slowly
            battery_level:   p.battery_level  ?? Math.max(5,  s.battery_level  - Math.random() * 0.01),
            signal_strength: p.signal_strength ?? Math.max(10, s.signal_strength + (Math.random() - 0.5) * 2),
          }
        })
        return next
      })
    })
    return unsub
  }, [])

  // ── Manual test scenarios ──────────────────────────────────────────────────
  const triggerScenario = useCallback((type: ScenarioType, targetId?: string) => {
    setSensors(prev => {
      const next = prev.map(s => {
        const isCandidateByType = (types: SensorMarker['sensor_type'][]) =>
          (!targetId || s.id === targetId || s.zone_id === targetId) &&
          types.includes(s.sensor_type)

        if (type === 'gas_leak' && isCandidateByType(['gas'])) {
          const v = s.threshold_critical * 1.1
          return { ...s, current_value: v, status: 'critical' as SensorStatus, last_updated: new Date().toISOString() }
        }
        if (type === 'fire' && isCandidateByType(['smoke', 'temperature'])) {
          const v = s.threshold_critical * 1.2
          return { ...s, current_value: v, status: 'critical' as SensorStatus, last_updated: new Date().toISOString() }
        }
        if (type === 'pressure_failure' && isCandidateByType(['pressure'])) {
          const v = s.threshold_critical * 1.05
          return { ...s, current_value: v, status: 'critical' as SensorStatus, last_updated: new Date().toISOString() }
        }
        if (type === 'sensor_offline' && (!targetId || s.id === targetId)) {
          return { ...s, status: 'offline' as SensorStatus, last_updated: new Date().toISOString() }
        }
        if (type === 'reset_sensor' && (!targetId || s.id === targetId)) {
          const baseVal = getBaselineValue(s.sensor_type)
          return { ...s, current_value: baseVal, status: 'healthy' as SensorStatus, last_updated: new Date().toISOString() }
        }
        if (type === 'reset_zone' && s.zone_id === targetId) {
          const baseVal = getBaselineValue(s.sensor_type)
          return { ...s, current_value: baseVal, status: 'healthy' as SensorStatus, last_updated: new Date().toISOString() }
        }
        return s
      })

      // Generate incidents for scenario-triggered changes
      next.forEach(s => {
        const prev_s = prev.find(p => p.id === s.id)
        if (prev_s && prev_s.status !== s.status) {
          const incident: SensorIncident = {
            id: `inc-${++incidentCounter}`,
            sensor_id: s.id,
            sensor_name: s.name,
            zone_name: s.zone_name,
            old_status: prev_s.status,
            new_status: s.status,
            value: s.current_value,
            unit: s.unit,
            timestamp: new Date().toISOString(),
          }
          setIncidents(p => [incident, ...p].slice(0, 50))
        }
      })

      return next
    })
  }, [])

  const clearIncidents = useCallback(() => setIncidents([]), [])

  return {
    sensors, zoneRisks, incidents, stats,
    selectedSensor, setSelectedSensor,
    hoveredSensor, setHoveredSensor,
    focusedSensorId,
    triggerScenario, clearIncidents,
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function mapSimTypeToSensorType(simType: string): SensorMarker['sensor_type'] {
  const map: Record<string, SensorMarker['sensor_type']> = {
    gas_ppm:       'gas',
    temp_c:        'temperature',
    pressure_kpa:  'pressure',
    vibration_mm_s:'vibration',
  }
  return map[simType] ?? 'gas'
}

function getBaselineValue(type: SensorMarker['sensor_type']): number {
  const baselines: Record<SensorMarker['sensor_type'], number> = {
    gas: 5, temperature: 30, pressure: 101, vibration: 1.5,
    smoke: 0.5, humidity: 50, water_level: 10,
  }
  return baselines[type] ?? 0
}
