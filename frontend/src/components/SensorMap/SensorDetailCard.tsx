import React from 'react'
import type { SensorMarker } from '../../types'
import { SENSOR_TYPE_META, STATUS_META } from '../../services/sensorMapConfig'

interface SensorDetailCardProps {
  sensor: SensorMarker
  onClose: () => void
  onTriggerOffline: (id: string) => void
  onResetSensor: (id: string) => void
}

function BatteryBar({ level }: { level: number }) {
  const color = level > 50 ? '#3fb950' : level > 20 ? '#d29922' : '#f85149'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: 'var(--color-border)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${level}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s ease' }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 700, minWidth: 32 }}>{Math.round(level)}%</span>
    </div>
  )
}

function SignalBars({ strength }: { strength: number }) {
  const bars = [25, 50, 75, 100]
  const color = strength > 60 ? '#3fb950' : strength > 30 ? '#d29922' : '#f85149'
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2 }}>
      {bars.map((threshold, i) => (
        <div key={i} style={{
          width: 5,
          height: 4 + i * 3,
          background: strength >= threshold ? color : 'var(--color-border)',
          borderRadius: 1,
          transition: 'background 0.3s ease',
        }} />
      ))}
      <span style={{ fontSize: 11, color, marginLeft: 6, fontWeight: 700 }}>{Math.round(strength)}%</span>
    </div>
  )
}

export function SensorDetailCard({ sensor, onClose, onTriggerOffline, onResetSensor }: SensorDetailCardProps) {
  const typeMeta = SENSOR_TYPE_META[sensor.sensor_type] ?? { label: sensor.sensor_type, icon: '📡', color: '#8b949e' }
  const statusMeta = STATUS_META[sensor.status]

  const pct = Math.min(100, (sensor.current_value / sensor.threshold_critical) * 100)
  const barColor = pct >= 100 ? '#f85149' : pct >= 80 ? '#e85d04' : pct >= 60 ? '#d29922' : '#3fb950'

  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '8px 0', borderBottom: '1px solid var(--color-border)',
    }}>
      <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{label}</span>
      <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{children}</span>
    </div>
  )

  return (
    <div className="slide-in-right" style={{
      position: 'fixed',
      top: 80,
      right: 16,
      width: 340,
      background: 'var(--color-surface)',
      border: `1px solid ${statusMeta.color}50`,
      borderRadius: 14,
      boxShadow: `0 8px 40px rgba(0,0,0,0.4), 0 0 20px ${statusMeta.glow}`,
      zIndex: 1000,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        background: `linear-gradient(135deg, ${statusMeta.color}18, transparent)`,
        borderBottom: `1px solid ${statusMeta.color}30`,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: `${typeMeta.color}18`,
            border: `1px solid ${typeMeta.color}40`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
          }}>
            {typeMeta.icon}
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)' }}>{sensor.name}</div>
            <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2 }}>{sensor.zone_name}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{
            padding: '3px 10px', borderRadius: 20,
            background: `${statusMeta.color}20`,
            border: `1px solid ${statusMeta.color}`,
            color: statusMeta.color, fontSize: 10, fontWeight: 700,
          }}>
            {statusMeta.label.toUpperCase()}
          </span>
          <button onClick={onClose} style={{
            background: 'transparent', color: 'var(--color-text-secondary)',
            fontSize: 18, lineHeight: 1, padding: '2px 6px',
            border: '1px solid var(--color-border)', borderRadius: 6, cursor: 'pointer',
          }}>×</button>
        </div>
      </div>

      {/* Live Reading Gauge */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Current Reading</span>
          <span style={{ fontSize: 20, fontWeight: 800, color: barColor, fontFamily: 'monospace' }}>
            {sensor.current_value.toFixed(2)} <span style={{ fontSize: 12, fontWeight: 400 }}>{sensor.unit}</span>
          </span>
        </div>
        <div style={{ height: 8, background: 'var(--color-border)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: `linear-gradient(90deg, #3fb950, ${barColor})`,
            borderRadius: 4, transition: 'width 0.5s ease',
            boxShadow: `0 0 6px ${barColor}60`,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10, color: 'var(--color-text-muted)' }}>
          <span>0 {sensor.unit}</span>
          <span>⚠ {sensor.threshold_warning}</span>
          <span>🔴 {sensor.threshold_critical}</span>
        </div>
      </div>

      {/* Details */}
      <div style={{ padding: '4px 20px' }}>
        <Row label="Sensor ID"><code style={{ fontSize: 10, color: 'var(--color-accent-light, #8b7de8)' }}>{sensor.id}</code></Row>
        <Row label="Type">{typeMeta.icon} {typeMeta.label}</Row>
        <Row label="Zone">{sensor.zone_name}</Row>
        <Row label="Threshold">⚠ {sensor.threshold_warning} · 🔴 {sensor.threshold_critical} {sensor.unit}</Row>
        <Row label="Last Updated">
          {new Date(sensor.last_updated).toLocaleTimeString()}
        </Row>
        <div style={{ padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Battery Level</span>
          </div>
          <BatteryBar level={sensor.battery_level} />
        </div>
        <div style={{ padding: '8px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Signal Strength</span>
          </div>
          <SignalBars strength={sensor.signal_strength} />
        </div>
      </div>

      {/* Actions */}
      <div style={{ padding: '12px 20px', display: 'flex', gap: 8, borderTop: '1px solid var(--color-border)' }}>
        <button
          className="btn btn-danger"
          style={{ flex: 1, fontSize: 12 }}
          onClick={() => onTriggerOffline(sensor.id)}
        >
          Take Offline
        </button>
        <button
          className="btn"
          style={{ flex: 1, fontSize: 12, background: 'var(--color-surface-2)', color: '#3fb950', border: '1px solid #3fb95040' }}
          onClick={() => onResetSensor(sensor.id)}
        >
          Reset Sensor
        </button>
      </div>
    </div>
  )
}
