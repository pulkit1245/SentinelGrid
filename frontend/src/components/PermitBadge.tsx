import React from 'react'
import type { Permit } from '../types'

const PERMIT_COLORS: Record<string, string> = {
  hot_work: 'var(--color-critical)',
  confined_space: 'var(--color-warning)',
  excavation: 'var(--color-watch)',
  electrical: 'var(--color-info)',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'var(--color-success)',
  closed: 'var(--color-text-muted)',
  revoked: 'var(--color-critical)',
}

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export function PermitBadge({ permit }: { permit: Permit }) {
  const pc = PERMIT_COLORS[permit.permit_type] ?? 'var(--color-text-secondary)'
  const sc = STATUS_COLORS[permit.status] ?? 'var(--color-text-muted)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 14px',
      background: 'var(--color-surface-2)',
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--color-border)',
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: pc, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
          {permit.permit_type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>
          {fmt(permit.valid_from)} → {fmt(permit.valid_to)}
        </div>
      </div>
      <span style={{
        fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 'var(--radius-full)',
        background: `${sc}18`, color: sc, textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>
        {permit.status}
      </span>
    </div>
  )
}
