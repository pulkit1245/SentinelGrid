import React from 'react'
import { useNavigate } from 'react-router-dom'
import type { Zone } from '../types'

const HAZARD_COLORS: Record<string, string> = {
  gas: 'var(--color-warning)',
  thermal: 'var(--color-critical)',
  mechanical: 'var(--color-info)',
  confined_space: 'var(--color-watch)',
  general: 'var(--color-success)',
}

function riskColor(score: number): string {
  if (score >= 80) return 'var(--color-critical)'
  if (score >= 60) return 'var(--color-warning)'
  if (score >= 40) return 'var(--color-watch)'
  return 'var(--color-success)'
}

export function ZoneCard({ zone }: { zone: Zone }) {
  const navigate = useNavigate()
  const score = zone.current_risk_score
  const rc = riskColor(score)
  const hc = HAZARD_COLORS[zone.hazard_class] ?? 'var(--color-info)'

  return (
    <div
      id={`zone-card-${zone.slug ?? zone.id}`}
      onClick={() => navigate(`/zones/${zone.id}`)}
      className="card"
      style={{
        cursor: 'pointer',
        transition: 'transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast)',
        borderLeft: `3px solid ${hc}`,
        padding: '18px 20px',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'
        ;(e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-md)'
        ;(e.currentTarget as HTMLElement).style.borderColor = hc
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.transform = ''
        ;(e.currentTarget as HTMLElement).style.boxShadow = ''
        ;(e.currentTarget as HTMLElement).style.borderColor = hc
      }}
    >
      {/* Background glow for high risk */}
      {score >= 80 && (
        <div style={{
          position: 'absolute', top: 0, right: 0, width: 80, height: 80,
          background: 'radial-gradient(circle, rgba(248,81,73,0.12) 0%, transparent 70%)',
          borderRadius: '50%', transform: 'translate(20%, -20%)',
        }} />
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {zone.name}
          </div>
          <span className="badge" style={{ background: `${hc}18`, color: hc }}>{zone.hazard_class.replace('_', ' ')}</span>
        </div>

        {/* Circular score gauge */}
        <div style={{ position: 'relative', width: 52, height: 52, flexShrink: 0 }}>
          <svg width={52} height={52} viewBox="0 0 52 52">
            <circle cx={26} cy={26} r={22} fill="none" stroke="var(--color-border)" strokeWidth={4} />
            <circle
              cx={26} cy={26} r={22} fill="none" stroke={rc} strokeWidth={4}
              strokeDasharray={`${(score / 100) * 138.2} 138.2`}
              strokeLinecap="round"
              transform="rotate(-90 26 26)"
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          </svg>
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 800, color: rc,
          }}>
            {score}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 14 }}>
        <Stat label="Alerts" value={zone.active_alert_count} color={zone.active_alert_count > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)'} />
        <Stat label="Permits" value={zone.active_permit_count} color="var(--color-text-muted)" />
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div style={{ fontSize: 16, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
    </div>
  )
}
