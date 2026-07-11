import React from 'react'
import { Shield, Bell } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useAlerts } from '../../hooks/useAlerts'
import { Link } from 'react-router-dom'

export function Navbar() {
  const { currentUser } = useAuth()
  const { alerts } = useAlerts()
  const activeAlertsCount = alerts.filter(a => a.is_active).length

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 24px',
      background: 'var(--color-surface)',
      borderBottom: '1px solid var(--color-border)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Left */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 32, height: 32,
          background: 'linear-gradient(135deg, var(--color-accent), #4f3fb0)',
          borderRadius: 8,
          boxShadow: 'var(--shadow-glow-accent)',
        }}>
          <Shield size={18} color="#fff" />
        </div>
        <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)' }}>SentinelGrid</span>
      </Link>

      {/* Center */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', background: 'rgba(52, 211, 153, 0.1)', borderRadius: 'var(--radius-full)', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%', background: 'var(--color-success)',
          boxShadow: '0 0 8px var(--color-success)',
          animation: 'pulse 2s infinite'
        }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-success)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Live Feed Connected
        </span>
      </div>

      {/* Right */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ position: 'relative', cursor: 'pointer' }}>
          <Bell size={20} color="var(--color-text-secondary)" />
          {activeAlertsCount > 0 && (
            <div style={{
              position: 'absolute', top: -4, right: -4,
              minWidth: 16, height: 16, borderRadius: 8,
              background: 'var(--color-critical)', color: '#fff',
              fontSize: 10, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '0 4px',
            }}>
              {activeAlertsCount}
            </div>
          )}
        </div>
        
        {currentUser && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 20, borderLeft: '1px solid var(--color-border)' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{currentUser.email}</div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {currentUser.role?.replace('_', ' ')}
              </div>
            </div>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--color-surface-2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: 'var(--color-text-secondary)'
            }}>
              {currentUser.email?.charAt(0).toUpperCase()}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
