import React from 'react'
import type { SensorMarker } from '../../types'
import { CONTROL_ROOM_CENTER } from '../../services/sensorMapConfig'

interface ConnectionLinesProps {
  sensors: SensorMarker[]
}

export function ConnectionLines({ sensors }: ConnectionLinesProps) {
  const criticalSensors = sensors.filter(s => s.status === 'critical')

  return (
    <g>
      {criticalSensors.map(sensor => (
        <line
          key={`line-${sensor.id}`}
          x1={sensor.x}
          y1={sensor.y}
          x2={CONTROL_ROOM_CENTER.x}
          y2={CONTROL_ROOM_CENTER.y}
          stroke="#f85149"
          strokeWidth={1.2}
          strokeOpacity={0.5}
          strokeDasharray="6 4"
          className="connection-anim"
        />
      ))}
    </g>
  )
}
