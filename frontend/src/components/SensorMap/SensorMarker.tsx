import React from 'react'
import type { SensorMarker } from '../../types'
import { STATUS_META } from '../../services/sensorMapConfig'

interface SensorMarkerProps {
  sensor: SensorMarker
  isFocused: boolean
  onHover: (s: SensorMarker | null) => void
  onClick: (s: SensorMarker) => void
}

// ── Type-specific SVG icon paths (16×16 viewBox, centred at 0,0) ──────────────

type SensorIconType = SensorMarker['sensor_type']

function SensorIcon({ type, color }: { type: SensorIconType; color: string }) {
  switch (type) {
    case 'gas':
      // Molecule / gas cloud — three circles connected by bonds
      return (
        <g>
          <circle cx={0} cy={-3} r={2.8} fill={color} opacity={0.9} />
          <circle cx={-3.5} cy={2.5} r={2.2} fill={color} opacity={0.75} />
          <circle cx={3.5} cy={2.5} r={2.2} fill={color} opacity={0.75} />
          <line x1={0} y1={-0.2} x2={-2.5} y2={1.2} stroke={color} strokeWidth={1.2} opacity={0.6} />
          <line x1={0} y1={-0.2} x2={2.5} y2={1.2} stroke={color} strokeWidth={1.2} opacity={0.6} />
        </g>
      )

    case 'temperature':
      // Thermometer — slim shaft + bulb
      return (
        <g>
          <rect x={-1.5} y={-6} width={3} height={8} rx={1.5} fill={color} opacity={0.35} />
          <rect x={-1} y={-5.5} width={2} height={6.5} rx={1} fill={color} opacity={0.9} />
          <circle cx={0} cy={4} r={3} fill={color} opacity={0.95} />
          <circle cx={0} cy={4} r={1.6} fill="var(--color-bg, #0d1117)" opacity={0.5} />
        </g>
      )

    case 'pressure':
      // Gauge arc + needle
      return (
        <g>
          <path
            d="M -5 2 A 5 5 0 0 1 5 2"
            fill="none" stroke={color} strokeWidth={2}
            strokeLinecap="round" opacity={0.4}
          />
          <path
            d="M -5 2 A 5 5 0 0 1 2 -3.5"
            fill="none" stroke={color} strokeWidth={2.2}
            strokeLinecap="round" opacity={0.9}
          />
          <circle cx={0} cy={2} r={1.5} fill={color} />
          <line x1={0} y1={2} x2={1.8} y2={-3} stroke={color} strokeWidth={1.3} strokeLinecap="round" />
        </g>
      )

    case 'vibration':
      // Zigzag sine wave
      return (
        <g>
          <polyline
            points="-6,0 -4,-4 -2,4 0,-4 2,4 4,-4 6,0"
            fill="none" stroke={color} strokeWidth={1.8}
            strokeLinecap="round" strokeLinejoin="round"
          />
        </g>
      )

    case 'smoke':
      // Three wavy rising smoke lines
      return (
        <g opacity={0.9}>
          <path d="M 0 5 Q -2 1 0 -2 Q 2 -5 0 -7" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" />
          <path d="M -3 4 Q -5 0 -3 -3" fill="none" stroke={color} strokeWidth={1.3} strokeLinecap="round" opacity={0.7} />
          <path d="M 3 4 Q 5 0 3 -3" fill="none" stroke={color} strokeWidth={1.3} strokeLinecap="round" opacity={0.7} />
        </g>
      )

    case 'humidity':
      // Water droplet
      return (
        <g>
          <path
            d="M 0 -6 Q 4 0 4 3 A 4 4 0 0 1 -4 3 Q -4 0 0 -6 Z"
            fill={color} opacity={0.85}
          />
          <ellipse cx={-1} cy={1} rx={1.2} ry={1.8} fill="var(--color-bg, #0d1117)" opacity={0.4} transform="rotate(-20)" />
        </g>
      )

    case 'water_level':
      // Two wave lines
      return (
        <g>
          <path
            d="M -6 -2 Q -3 -5 0 -2 Q 3 1 6 -2"
            fill="none" stroke={color} strokeWidth={2} strokeLinecap="round"
          />
          <path
            d="M -6 3 Q -3 0 0 3 Q 3 6 6 3"
            fill="none" stroke={color} strokeWidth={1.6} strokeLinecap="round" opacity={0.6}
          />
        </g>
      )

    default:
      // Fallback: wifi/signal icon
      return (
        <g>
          <circle cx={0} cy={2} r={1.8} fill={color} />
          <path d="M -4 -1 Q 0 -5 4 -1" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" opacity={0.8} />
          <path d="M -6.5 -3.5 Q 0 -9 6.5 -3.5" fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" opacity={0.5} />
        </g>
      )
  }
}

// ── Marker component ───────────────────────────────────────────────────────────

export function SensorMarkerDot({ sensor, isFocused, onHover, onClick }: SensorMarkerProps) {
  const meta      = STATUS_META[sensor.status]
  const isCritical = sensor.status === 'critical'
  const isWarning  = sensor.status === 'warning' || sensor.status === 'high_risk'
  const isOffline  = sensor.status === 'offline'

  // Background disc size by status
  const discR = isCritical ? 10 : isWarning ? 9 : 8

  return (
    <g
      style={{ cursor: 'pointer' }}
      onMouseEnter={() => onHover(sensor)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onClick(sensor)}
    >
      {/* Outer pulse ring */}
      {!isOffline && (
        <circle
          cx={sensor.x}
          cy={sensor.y}
          r={discR + 6}
          fill="none"
          stroke={meta.color}
          strokeWidth={1.5}
          opacity={0.3}
          style={{
            transition: 'r 0.4s ease',
            ...(isCritical ? { animation: 'sensor-pulse-critical 1s ease-in-out infinite' } :
                isWarning  ? { animation: 'sensor-pulse-warning  1.5s ease-in-out infinite' } : {}),
          }}
        />
      )}

      {/* Focus ring (incident highlight) */}
      {isFocused && (
        <circle
          cx={sensor.x} cy={sensor.y} r={discR + 12}
          fill="none" stroke="#fff" strokeWidth={2} opacity={0.85} strokeDasharray="4 3"
        />
      )}

      {/* Background disc */}
      <circle
        cx={sensor.x} cy={sensor.y} r={discR}
        fill={isOffline ? 'var(--color-surface-2, #1f2937)' : meta.color}
        stroke="var(--color-bg, #0d1117)"
        strokeWidth={1.8}
        opacity={isOffline ? 0.7 : 1}
        style={{
          filter: isOffline ? 'none' : `drop-shadow(0 0 5px ${meta.glow})`,
          transition: 'fill 0.4s ease, r 0.3s ease',
        }}
      />

      {/* Type-specific icon, centred at sensor.x, sensor.y */}
      <g
        transform={`translate(${sensor.x}, ${sensor.y})`}
        style={{ transition: 'opacity 0.3s' }}
        opacity={isOffline ? 0.45 : 1}
      >
        <SensorIcon
          type={sensor.sensor_type}
          color={isOffline ? 'var(--color-text-muted, #484f58)' : 'var(--color-bg, #0d1117)'}
        />
      </g>
    </g>
  )
}
