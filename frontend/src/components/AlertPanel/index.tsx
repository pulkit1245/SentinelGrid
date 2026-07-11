import React, { useState } from 'react'
import { AlertTriangle, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { useAlerts } from '../../hooks/useAlerts'
import { ConfirmModal } from './ConfirmModal'
import { api } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'

export function AlertPanel({ zoneId, maxHeight = '100%' }: { zoneId?: string, maxHeight?: string }) {
  const { alerts, refresh } = useAlerts(zoneId)
  const { currentUser } = useAuth()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmingAlert, setConfirmingAlert] = useState<any | null>(null)

  const activeAlerts = alerts.filter(a => a.is_active)

  if (activeAlerts.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>
        No active alerts in this scope
      </div>
    )
  }

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'critical': return 'var(--color-critical)'
      case 'warning': return 'var(--color-warning)'
      case 'watch': return 'var(--color-watch)'
      default: return 'var(--color-info)'
    }
  }

  const handleConfirm = async () => {
    if (!confirmingAlert) return
    await api.confirmAlert(confirmingAlert.id)
    setConfirmingAlert(null)
    refresh()
  }

  return (
    <div style={{ maxHeight, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {activeAlerts.map(alert => {
        const color = getSeverityColor(alert.severity)
        const isExpanded = expandedId === alert.id
        const isPlantAdmin = currentUser?.role === 'plant_admin'

        return (
          <div key={alert.id} className="card" style={{ borderLeft: `4px solid ${color}`, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ 
                    fontSize: 10, fontWeight: 700, textTransform: 'uppercase', 
                    padding: '2px 6px', borderRadius: 4, 
                    background: `${color}20`, color: color 
                  }}>
                    {alert.severity}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-muted)', fontSize: 12 }}>
                    <Clock size={12} />
                    <span>{new Date(alert.triggered_at).toLocaleTimeString()}</span>
                  </div>
                </div>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                  {alert.title}
                </h3>
                <p style={{ 
                  fontSize: 13, color: 'var(--color-text-secondary)', 
                  display: '-webkit-box', WebkitLineClamp: isExpanded ? 'unset' : 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'
                }}>
                  {alert.description}
                </p>
              </div>
              <button 
                onClick={() => setExpandedId(isExpanded ? null : alert.id)}
                style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 4 }}
              >
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
            </div>

            {isExpanded && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--color-border)' }}>
                <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>Evidence Graph</h4>
                <div style={{ background: 'var(--color-surface-2)', padding: 12, borderRadius: 8, fontSize: 12, fontFamily: 'monospace', color: 'var(--color-text-muted)' }}>
                  {alert.graph_path && alert.graph_path.length > 0 ? (
                    <ul style={{ paddingLeft: 16, margin: 0 }}>
                      {alert.graph_path.map((node: any, idx: number) => (
                        <li key={idx} style={{ marginBottom: 4 }}>
                          <span style={{ color: 'var(--color-accent)' }}>[{node.type}]</span> {node.node}
                          {node.value && ` (Val: ${node.value}, Thr: ${node.threshold})`}
                          {node.overlap && ` (Overlap Detected)`}
                        </li>
                      ))}
                    </ul>
                  ) : 'No graph path evidence provided.'}
                </div>
                
                {isPlantAdmin && (
                  <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
                    <button 
                      className="btn" 
                      style={{ background: 'rgba(248,81,73,0.1)', color: 'var(--color-critical)', border: '1px solid rgba(248,81,73,0.3)', padding: '6px 12px', fontSize: 13 }}
                      onClick={() => setConfirmingAlert(alert)}
                    >
                      <AlertTriangle size={14} style={{ marginRight: 6 }} />
                      Confirm Action
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}

      {confirmingAlert && (
        <ConfirmModal 
          alert={confirmingAlert} 
          onConfirm={handleConfirm} 
          onCancel={() => setConfirmingAlert(null)} 
        />
      )}
    </div>
  )
}
