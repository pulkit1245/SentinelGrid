import React, { useState } from 'react'
import type { ScenarioType } from '../../hooks/useSensorMap'
import { ZONE_CONFIGS } from '../../services/sensorMapConfig'
import { Flame, Wind, Gauge, WifiOff, RefreshCw, RotateCcw } from 'lucide-react'

interface ManualTestControlsProps {
  onTrigger: (type: ScenarioType, targetId?: string) => void
}

export function ManualTestControls({ onTrigger }: ManualTestControlsProps) {
  const [selectedZone, setSelectedZone] = useState(ZONE_CONFIGS[0].zone_id)

  const globalBtn = (
    label: string,
    type: ScenarioType,
    icon: React.ReactNode,
    color: string,
  ) => (
    <button
      onClick={() => onTrigger(type)}
      style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '8px 14px',
        background: `${color}18`, color,
        border: `1px solid ${color}40`,
        borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = `${color}30`)}
      onMouseLeave={e => (e.currentTarget.style.background = `${color}18`)}
    >
      {icon}
      {label}
    </button>
  )

  return (
    <div style={{
      padding: '12px 16px',
      background: 'rgba(13,17,23,0.9)',
      border: '1px solid #21262d',
      borderRadius: 12,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
        Manual Test Controls
      </div>

      {/* Global scenarios */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {globalBtn('Gas Leak',         'gas_leak',         <Wind size={13} />,    '#d29922')}
        {globalBtn('Fire / Smoke',     'fire',             <Flame size={13} />,   '#f85149')}
        {globalBtn('Pressure Failure', 'pressure_failure', <Gauge size={13} />,   '#e85d04')}
        {globalBtn('Sensor Offline',   'sensor_offline',   <WifiOff size={13} />, '#484f58')}
      </div>

      {/* Zone-targeted controls */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <select
          value={selectedZone}
          onChange={e => setSelectedZone(e.target.value)}
          style={{
            background: '#21262d', color: '#e6edf3', border: '1px solid #30363d',
            borderRadius: 8, padding: '7px 10px', fontSize: 12, cursor: 'pointer',
            outline: 'none',
          }}
        >
          {ZONE_CONFIGS.map(z => (
            <option key={z.zone_id} value={z.zone_id}>{z.zone_name}</option>
          ))}
        </select>

        <button
          onClick={() => onTrigger('reset_zone', selectedZone)}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '7px 14px',
            background: '#3fb95018', color: '#3fb950',
            border: '1px solid #3fb95040',
            borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}
        >
          <RefreshCw size={13} /> Reset Zone
        </button>

        <button
          onClick={() => onTrigger('reset_sensor')}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '7px 14px',
            background: '#58a6ff18', color: '#58a6ff',
            border: '1px solid #58a6ff40',
            borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}
        >
          <RotateCcw size={13} /> Reset All
        </button>
      </div>
    </div>
  )
}
