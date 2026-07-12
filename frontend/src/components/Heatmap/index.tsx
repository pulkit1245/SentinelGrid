import React from 'react'
import { useNavigate } from 'react-router-dom'
import type { Zone } from '../../types'

export function Heatmap({ zones }: { zones: Zone[] }) {
  const navigate = useNavigate()

  const getRiskColor = (score: number) => {
    if (score > 80) return 'var(--color-critical)'
    if (score > 60) return 'var(--color-warning)'
    if (score > 30) return 'var(--color-watch)'
    return 'var(--color-success)'
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: 16
    }}>
      {zones.map(zone => {
        const color = getRiskColor(zone.current_risk_score)
        const isCritical = zone.current_risk_score > 80
        
        return (
          <div 
            key={zone.id}
            onClick={() => navigate(`/zones/${zone.id}`)}
            className="card"
            style={{ 
              cursor: 'pointer',
              border: `1px solid ${isCritical ? color : 'var(--color-border)'}`,
              boxShadow: isCritical ? `0 0 16px ${color}20` : 'none',
              transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
              position: 'relative',
              overflow: 'hidden'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = `0 4px 20px ${color}40`
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = isCritical ? `0 0 16px ${color}20` : 'none'
            }}
          >
            {/* Top color bar */}
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: color }} />
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                  {zone.name}
                </h3>
                <span style={{ 
                  fontSize: 10, fontWeight: 600, textTransform: 'uppercase', 
                  color: color
                }}>
                  {zone.hazard_class}
                </span>
              </div>
              <div style={{ 
                width: 40, height: 40, borderRadius: '50%', 
                border: `2px solid ${color}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: isCritical ? `${color}10` : 'transparent',
                animation: isCritical ? 'pulse 2s infinite' : 'none'
              }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: color }}>
                  {zone.current_risk_score}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 16, marginTop: 16, borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)' }}>{zone.active_alert_count || 0}</span>
                <span style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Alerts</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)' }}>{zone.active_permit_count || 0}</span>
                <span style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Permits</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
