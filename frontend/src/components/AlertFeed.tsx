import React from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle, ChevronRight } from 'lucide-react'
import type { Alert } from '../types'

const SEVERITY_ORDER = ['critical', 'warning', 'watch', 'info'] as const

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

interface Props {
  alerts: Alert[]
  loading: boolean
  onConfirm?: (id: string) => Promise<unknown>
  userRole?: string
}

export function AlertFeed({ alerts, loading, onConfirm, userRole }: Props) {
  const navigate = useNavigate()
  const sorted = [...alerts].sort((a, b) =>
    SEVERITY_ORDER.indexOf(a.severity as typeof SEVERITY_ORDER[number]) -
    SEVERITY_ORDER.indexOf(b.severity as typeof SEVERITY_ORDER[number])
  )

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80, borderRadius: 'var(--radius-md)' }} />)}
    </div>
  )

  if (sorted.length === 0) return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '40px 20px', color: 'var(--color-text-muted)', gap: 12, textAlign: 'center',
    }}>
      <CheckCircle size={36} />
      <div style={{ fontSize: 14, fontWeight: 600 }}>All clear</div>
      <div style={{ fontSize: 12 }}>No active alerts in this scope</div>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {sorted.map(alert => (
        <AlertRow
          key={alert.id}
          alert={alert}
          canConfirm={userRole === 'plant_admin' && !alert.confirmed_by}
          onConfirm={onConfirm}
          onClick={() => navigate(`/alerts/${alert.id}`)}
        />
      ))}
    </div>
  )
}

function AlertRow({ alert, canConfirm, onConfirm, onClick }: {
  alert: Alert; canConfirm: boolean; onConfirm?: (id: string) => Promise<unknown>; onClick: () => void
}) {
  const [confirming, setConfirming] = React.useState(false)

  const severityColor: Record<string, string> = {
    critical: 'var(--color-critical)',
    warning: 'var(--color-warning)',
    watch: 'var(--color-watch)',
    info: 'var(--color-info)',
  }
  const sc = severityColor[alert.severity] ?? 'var(--color-text-secondary)'

  async function handleConfirm(e: React.MouseEvent) {
    e.stopPropagation()
    if (!onConfirm) return
    setConfirming(true)
    try { await onConfirm(alert.id) } finally { setConfirming(false) }
  }

  return (
    <div
      id={`alert-row-${alert.id}`}
      onClick={onClick}
      className={alert.severity === 'critical' && !alert.confirmed_by ? 'pulse-critical' : ''}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '12px 14px',
        background: 'var(--color-surface)',
        border: `1px solid ${sc}30`,
        borderLeft: `3px solid ${sc}`,
        borderRadius: 'var(--radius-md)',
        cursor: 'pointer',
        transition: 'background var(--transition-fast)',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-2)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--color-surface)')}
    >
      <AlertTriangle size={16} color={sc} style={{ flexShrink: 0 }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {alert.title}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>
          {timeAgo(alert.triggered_at)}
          {alert.confirmed_by && <span style={{ marginLeft: 8, color: 'var(--color-success)' }}>✓ Confirmed</span>}
        </div>
      </div>

      {canConfirm && (
        <button
          id={`btn-confirm-${alert.id}`}
          onClick={handleConfirm}
          disabled={confirming}
          className="btn btn-danger"
          style={{ fontSize: 11, padding: '4px 10px', flexShrink: 0 }}
        >
          {confirming ? <span className="spinner" style={{ width: 12, height: 12 }} /> : 'Confirm'}
        </button>
      )}

      <ChevronRight size={14} color="var(--color-text-muted)" style={{ flexShrink: 0 }} />
    </div>
  )
}
