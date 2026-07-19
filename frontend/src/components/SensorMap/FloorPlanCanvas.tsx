import React, { useRef, useState } from 'react'
import type { SensorMarker, ZoneRisk } from '../../types'
import { ZONE_CONFIGS } from '../../services/sensorMapConfig'
import { ZonePolygon } from './ZonePolygon'
import { SensorMarkerDot } from './SensorMarker'
import { SensorTooltip } from './SensorTooltip'
import { ConnectionLines } from './ConnectionLines'

interface FloorPlanCanvasProps {
  sensors: SensorMarker[]
  zoneRisks: ZoneRisk[]
  focusedSensorId: string | null
  hoveredSensor: SensorMarker | null
  onHover: (s: SensorMarker | null) => void
  onSelectSensor: (s: SensorMarker) => void
}

export function FloorPlanCanvas({
  sensors, zoneRisks, focusedSensorId,
  hoveredSensor, onHover, onSelectSensor,
}: FloorPlanCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null)

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    setTooltipPos({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 60 })
  }

  return (
    <div style={{ position: 'relative', width: '100%', userSelect: 'none' }}>
      <svg
        ref={svgRef}
        viewBox="0 0 1200 800"
        style={{
          width: '100%',
          height: 'auto',
          borderRadius: 12,
          border: '1px solid #1e3a3a',
          display: 'block',
          background: '#060d0d',
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => { onHover(null); setTooltipPos(null) }}
      >
        <defs>
          <clipPath id="canvas-clip">
            <rect width="1200" height="800" />
          </clipPath>
        </defs>

        {/* ── Real factory floor plan background ── */}
        <image
          href="/factory_floor_plan.jpg"
          x="0" y="0"
          width="1200" height="800"
          preserveAspectRatio="xMidYMid slice"
          clipPath="url(#canvas-clip)"
        />
        {/* Dark overlay so zone polygons + sensors stay readable */}
        <rect width="1200" height="800" fill="rgba(6,13,13,0.50)" />

        {/* Zone polygons */}
        {ZONE_CONFIGS.map(zone => (
          <ZonePolygon
            key={zone.zone_id}
            config={zone}
            risk={zoneRisks.find(r => r.zone_id === zone.zone_id)}
          />
        ))}

        {/* Connection lines from critical sensors to control room */}
        <ConnectionLines sensors={sensors} />

        {/* Sensor markers */}
        {sensors.map(sensor => (
          <SensorMarkerDot
            key={sensor.id}
            sensor={sensor}
            isFocused={focusedSensorId === sensor.id}
            onHover={onHover}
            onClick={onSelectSensor}
          />
        ))}

        {/* Plant title watermark */}
        <text
          x="600" y="790"
          textAnchor="middle"
          fill="#21262d"
          fontSize={11}
          fontWeight={600}
          letterSpacing={2}
        >
          SENTINELGRID — INDUSTRIAL PLANT FLOOR PLAN — LIVE SCADA VIEW
        </text>
      </svg>

      {/* Tooltip overlay */}
      {hoveredSensor && tooltipPos && (
        <div style={{
          position: 'absolute',
          left: tooltipPos.x,
          top: tooltipPos.y,
          zIndex: 500,
          pointerEvents: 'none',
        }}>
          <SensorTooltip sensor={hoveredSensor} />
        </div>
      )}
    </div>
  )
}
