import React from 'react'
import type { SensorMarker } from '../../types'
import { SENSOR_TYPE_META, STATUS_META } from '../../services/sensorMapConfig'

interface SensorTooltipProps {
  sensor: SensorMarker
}

export function SensorTooltip({ sensor }: SensorTooltipProps) {
  const typeMeta = SENSOR_TYPE_META[sensor.sensor_type] ?? { label: sensor.sensor_type, icon: '📡' }
  const statusMeta = STATUS_META[sensor.status]

  // Position tooltip: offset from sensor dot
  // We let the parent <foreignObject> handle positioning
  return (
    <div style={{
      background: 'rgba(13,17,23,0.97)',
      border: `1px solid ${statusMeta.color}`,
      borderRadius: 10,
      padding: '10px 14px',
      minWidth: 200,
      boxShadow: `0 4px 24px rgba(0,0,0,0.7), 0 0 12px ${statusMeta.glow}`,
      pointerEvents: 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 18 }}>{typeMeta.icon}</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#e6edf3' }}>{sensor.name}</div>
          <div style={{ fontSize: 11, color: '#8b949e' }}>{sensor.zone_name}</div>
        </div>
        <div style={{
          marginLeft: 'auto',
          padding: '2px 8px',
          borderRadius: 20,
          background: `${statusMeta.color}20`,
          border: `1px solid ${statusMeta.color}60`,
          color: statusMeta.color,
          fontSize: 10,
          fontWeight: 700,
        }}>
          {statusMeta.label.toUpperCase()}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#8b949e' }}>
        <span>Reading</span>
        <span style={{ color: statusMeta.color, fontWeight: 700, fontFamily: 'monospace' }}>
          {sensor.current_value.toFixed(2)} {sensor.unit}
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#484f58', marginTop: 3 }}>
        <span>Threshold</span>
        <span style={{ fontFamily: 'monospace' }}>⚠ {sensor.threshold_warning} · 🔴 {sensor.threshold_critical}</span>
      </div>
    </div>
  )
}
