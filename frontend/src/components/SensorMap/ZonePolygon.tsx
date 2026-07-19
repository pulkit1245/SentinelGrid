import React from 'react'
import type { ZoneRisk } from '../../types'
import type { ZoneConfig } from '../../services/sensorMapConfig'
import { STATUS_META } from '../../services/sensorMapConfig'

interface ZonePolygonProps {
  config: ZoneConfig
  risk: ZoneRisk | undefined
}

const ZONE_COLOR_MAP = {
  healthy:   '#3fb950',
  warning:   '#d29922',
  high_risk: '#e85d04',
  critical:  '#f85149',
  offline:   '#484f58',
}

export function ZonePolygon({ config, risk }: ZonePolygonProps) {
  const level = risk?.risk_level ?? 'healthy'
  const color = ZONE_COLOR_MAP[level]
  const isCritical = level === 'critical'
  const score = risk?.aggregate_score ?? 0

  return (
    <g>
      {/* Zone fill */}
      <polygon
        points={config.points}
        fill={color}
        fillOpacity={0.18}
        stroke={color}
        strokeWidth={isCritical ? 3 : 2}
        strokeOpacity={0.95}
        className={isCritical ? 'zone-blink-critical' : undefined}
        style={{
          transition: 'fill 0.6s ease, stroke 0.6s ease, fill-opacity 0.6s ease',
          filter: isCritical ? `drop-shadow(0 0 10px ${color})` : `drop-shadow(0 0 3px ${color}60)`,
        }}
      />

      {/* Zone name label */}
      <text
        x={config.label_x}
        y={config.label_y + 12}
        textAnchor="middle"
        fill={color}
        fontSize={11}
        fontWeight={700}
        letterSpacing={0.5}
        style={{ textTransform: 'uppercase', userSelect: 'none', opacity: 0.9 }}
      >
        {config.zone_name}
      </text>

      {/* Risk score badge */}
      {score > 0 && (
        <>
          <rect
            x={config.label_x - 18}
            y={config.label_y + 18}
            width={36}
            height={14}
            rx={7}
            fill={color}
            fillOpacity={0.2}
            stroke={color}
            strokeWidth={0.8}
            strokeOpacity={0.6}
          />
          <text
            x={config.label_x}
            y={config.label_y + 29}
            textAnchor="middle"
            fill={color}
            fontSize={9}
            fontWeight={700}
          >
            {score}%
          </text>
        </>
      )}
    </g>
  )
}
