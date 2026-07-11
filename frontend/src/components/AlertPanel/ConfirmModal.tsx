import React, { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'

export function ConfirmModal({ alert, onConfirm, onCancel }: { alert: any, onConfirm: () => Promise<void>, onCancel: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    setLoading(true)
    setError(null)
    try {
      await onConfirm()
    } catch (err: any) {
      setError(err.message || 'Failed to confirm alert')
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)',
      backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
      padding: 24
    }}>
      <div className="card animate-fadeIn" style={{ width: '100%', maxWidth: 500, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 24px', background: 'var(--color-surface-2)', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>Confirm Alert Action</h2>
          <button onClick={onCancel} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }} disabled={loading}>
            <X size={20} />
          </button>
        </div>
        
        <div style={{ padding: 24 }}>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <div style={{ 
              width: 48, height: 48, borderRadius: '50%', background: 'rgba(248,81,73,0.1)', 
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 
            }}>
              <AlertTriangle size={24} color="var(--color-critical)" />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                {alert.title}
              </h3>
              <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                You are about to officially confirm this alert. This action will log your approval in the audit trail and may trigger automated evacuation or shutdown protocols for the affected zone.
              </p>
            </div>
          </div>

          {error && (
            <div style={{ padding: 12, background: 'rgba(248,81,73,0.1)', color: 'var(--color-critical)', borderRadius: 8, fontSize: 13, marginBottom: 24, border: '1px solid rgba(248,81,73,0.2)' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <button 
              className="btn" 
              style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-primary)' }} 
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              className="btn btn-primary" 
              style={{ background: 'var(--color-critical)', color: '#fff' }} 
              onClick={handleConfirm}
              disabled={loading}
            >
              {loading ? <span className="spinner" /> : 'Confirm Evacuation / Action'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
