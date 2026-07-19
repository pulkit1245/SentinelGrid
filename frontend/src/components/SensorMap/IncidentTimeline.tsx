import React from 'react'
import type { SensorIncident } from '../../types'
import { STATUS_META } from '../../services/sensorMapConfig'
import { Clock, Trash2 } from 'lucide-react'

interface IncidentTimelineProps {
  incidents: SensorIncident[]
  onClear: () => void
}

export function IncidentTimeline({ incidents, onClear }: IncidentTimelineProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 12,
      overflow: 'hidden',
      maxHeight: '100%',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={14} color="var(--color-text-secondary)" />
          <span style={{
            fontSize: 12, fontWeight: 700,
            color: 'var(--color-text-secondary)',
            textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>
            Incident Timeline
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {incidents.length > 0 && (
            <span style={{
              padding: '1px 7px', borderRadius: 20,
              background: '#f8514920', color: '#f85149',
              fontSize: 10, fontWeight: 700,
            }}>{incidents.length}</span>
          )}
          <button
            onClick={onClear}
            style={{ background: 'transparent', color: 'var(--color-text-muted)', border: 'none', cursor: 'pointer', padding: 2 }}
            title="Clear incidents"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Feed */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {incidents.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>
            No incidents yet.<br />
            <span style={{ fontSize: 11 }}>Use test controls or wait for live data.</span>
          </div>
        ) : (
          incidents.map((inc, i) => {
            const newMeta = STATUS_META[inc.new_status]
            const oldMeta = STATUS_META[inc.old_status]
            const isNew = i === 0
            return (
              <div
                key={inc.id}
                className={isNew ? 'animate-fadeIn' : undefined}
                style={{
                  padding: '10px 16px',
                  borderBottom: '1px solid var(--color-border)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  background: isNew ? `${newMeta.color}08` : 'transparent',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>{inc.sensor_name}</span>
                  <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                    {new Date(inc.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{inc.zone_name}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                  <span style={{
                    padding: '1px 6px', borderRadius: 10, fontSize: 9, fontWeight: 700,
                    background: `${oldMeta.color}20`, color: oldMeta.color,
                  }}>{inc.old_status.toUpperCase()}</span>
                  <span style={{ color: 'var(--color-text-muted)', fontSize: 11 }}>→</span>
                  <span style={{
                    padding: '1px 6px', borderRadius: 10, fontSize: 9, fontWeight: 700,
                    background: `${newMeta.color}20`, color: newMeta.color,
                  }}>{inc.new_status.toUpperCase()}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
                    {inc.value.toFixed(2)} {inc.unit}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
