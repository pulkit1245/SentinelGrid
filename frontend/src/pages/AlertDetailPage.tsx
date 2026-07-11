import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, CheckCircle, AlertTriangle, ChevronRight } from 'lucide-react'
import type { Alert } from '../types'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'

export default function AlertDetailPage() {
  const { alertId } = useParams<{ alertId: string }>()
  const navigate = useNavigate()
  const [alert, setAlert] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [report, setReport] = useState<Record<string, unknown> | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const { currentUser } = useAuth()

  useEffect(() => {
    if (!alertId) return
    api.getAlert(alertId).then(setAlert).finally(() => setLoading(false))
  }, [alertId])

  async function handleConfirm() {
    if (!alertId) return
    setConfirming(true)
    try {
      await api.confirmAlert(alertId)
      const updated = await api.getAlert(alertId)
      setAlert(updated)
    } finally {
      setConfirming(false)
    }
  }

  async function handleDownloadReport() {
    if (!alertId) return
    setReportLoading(true)
    try {
      const r = await api.getComplianceReport(alertId)
      setReport(r)
    } finally {
      setReportLoading(false)
    }
  }

  if (loading) return <div style={{ padding: 28 }}><div className="skeleton" style={{ height: 300 }} /></div>
  if (!alert) return <div style={{ padding: 28, color: 'var(--color-text-secondary)' }}>Alert not found.</div>

  const severityColor: Record<string, string> = {
    critical: 'var(--color-critical)',
    warning: 'var(--color-warning)',
    watch: 'var(--color-watch)',
    info: 'var(--color-info)',
  }
  const sc = severityColor[alert.severity] ?? 'var(--color-text-secondary)'

  return (
    <div style={{ padding: '24px 28px', maxWidth: 860, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ alignSelf: 'flex-start', fontSize: 13 }}>
        <ArrowLeft size={14} /> Back
      </button>

      {/* Alert header */}
      <div className="card" style={{ borderLeft: `4px solid ${sc}` }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span className={`badge badge-${alert.severity}`}>{alert.severity}</span>
              {alert.confirmed_by && <span className="badge badge-success"><CheckCircle size={10} /> Confirmed</span>}
            </div>
            <h1 style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>{alert.title}</h1>
            {alert.description && <p style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>{alert.description}</p>}
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Triggered</div>
            <div style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
              {new Date(alert.triggered_at).toLocaleString()}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          {!alert.confirmed_by && currentUser?.role === 'plant_admin' && (
            <button
              id="btn-confirm-alert"
              onClick={handleConfirm}
              disabled={confirming}
              className="btn btn-danger"
              style={{ background: 'rgba(248,81,73,0.2)', color: 'var(--color-critical)' }}
            >
              {confirming ? <span className="spinner" /> : <><AlertTriangle size={14} /> Confirm Evacuation</>}
            </button>
          )}
          {alert.confirmed_by && (currentUser?.role === 'plant_admin' || currentUser?.role === 'auditor') && (
            <button
              id="btn-download-report"
              onClick={handleDownloadReport}
              disabled={reportLoading}
              className="btn btn-ghost"
            >
              {reportLoading ? <span className="spinner" /> : <><Download size={14} /> Compliance Report</>}
            </button>
          )}
        </div>
      </div>

      {/* Causal chain */}
      {alert.graph_path.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: 16 }}>
            Causal Chain (Why this alert fired)
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {alert.graph_path.map((node, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                <div style={{
                  padding: '10px 16px',
                  background: 'var(--color-surface-2)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 13,
                  color: 'var(--color-text-primary)',
                  flex: 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent)' }}>{node.node}</span>
                  {node.value !== undefined && (
                    <span style={{ fontSize: 12, color: node.value > (node.threshold ?? Infinity) ? 'var(--color-critical)' : 'var(--color-text-secondary)' }}>
                      {node.value} {node.threshold ? `/ ${node.threshold}` : ''}
                    </span>
                  )}
                </div>
                {i < alert.graph_path.length - 1 && (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 8px' }}>
                    <div style={{ fontSize: 10, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{node.rel}</div>
                    <ChevronRight size={14} color="var(--color-text-muted)" style={{ transform: 'rotate(90deg)' }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compliance report preview */}
      {report && (
        <div className="card animate-fadeIn">
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: 16 }}>
            Compliance Report Draft
          </h2>
          <pre style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
