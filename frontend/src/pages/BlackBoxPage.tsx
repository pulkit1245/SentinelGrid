import React, { useState } from 'react'
import { BlackBoxReplayPanel } from '../components/BlackBox/BlackBoxReplayPanel'
import { Radio, Layers } from 'lucide-react'

const AVAILABLE_ZONES = [
  { id: 'zone-01-degassing', name: 'Zone 1 — Degassing & Separator' },
  { id: 'zone-02-compressor', name: 'Zone 2 — Gas Compression Bay' },
  { id: 'zone-03-storage', name: 'Zone 3 — Liquid Fuel Storage' },
  { id: 'zone-04-flare', name: 'Zone 4 — Flare Stack & Header' },
]

export default function BlackBoxPage() {
  const [selectedZone, setSelectedZone] = useState<string>('zone-01-degassing')

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.3px', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Radio size={22} color="var(--color-accent)" />
            Black Box Replay & Agent Debate Transcript
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: 4, fontSize: 13 }}>
            Inspect time-stamped flight recorder logs and multi-agent reasoning dialogue across industrial zones
          </p>
        </div>

        {/* Zone Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--color-surface)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
          <Layers size={14} color="var(--color-text-muted)" />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)' }}>Zone:</span>
          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            style={{
              background: 'transparent',
              color: 'var(--color-text-primary)',
              border: 'none',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {AVAILABLE_ZONES.map(z => (
              <option key={z.id} value={z.id} style={{ background: 'var(--color-surface)', color: 'var(--color-text-primary)' }}>
                {z.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Replay Panel */}
      <BlackBoxReplayPanel zoneId={selectedZone} onZoneChange={setSelectedZone} />
    </div>
  )
}
