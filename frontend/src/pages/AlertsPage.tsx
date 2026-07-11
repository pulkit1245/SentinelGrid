import React from 'react'
import { useAlerts } from '../hooks/useAlerts'
import { AlertFeed } from '../components/AlertFeed'
import { useAuth } from '../hooks/useAuth'
import { Filter } from 'lucide-react'
import { useState } from 'react'

export default function AlertsPage() {
  const [severity, setSeverity] = useState<string>('')
  const { alerts, loading, confirmAlert } = useAlerts()
  const { currentUser } = useAuth()

  const filtered = severity ? alerts.filter(a => a.severity === severity) : alerts

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Active Alerts</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: 4, fontSize: 13 }}>
            {filtered.length} alert{filtered.length !== 1 ? 's' : ''} — sorted by severity
          </p>
        </div>

        {/* Severity filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Filter size={14} color="var(--color-text-muted)" />
          {(['', 'critical', 'warning', 'watch', 'info'] as const).map(s => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`badge ${s ? `badge-${s}` : ''}`}
              style={{
                cursor: 'pointer',
                background: severity === s && s ? undefined : severity === s ? 'var(--color-surface-2)' : 'transparent',
                border: '1px solid var(--color-border)',
                color: s ? undefined : 'var(--color-text-secondary)',
                fontSize: 11,
              }}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      <AlertFeed alerts={filtered} loading={loading} onConfirm={confirmAlert} userRole={currentUser?.role} />
    </div>
  )
}
