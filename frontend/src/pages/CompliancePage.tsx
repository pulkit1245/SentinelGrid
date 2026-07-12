import React, { useEffect, useState } from 'react'
import { FileText, Download, Loader2, AlertTriangle, CheckCircle } from 'lucide-react'
import { api } from '../services/api'
import type { Alert } from '../types'

export default function CompliancePage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [generatingFor, setGeneratingFor] = useState<string | null>(null)
  const [generatedReports, setGeneratedReports] = useState<Record<string, any>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    api.getConfirmedAlerts().then(data => {
      if (mounted) {
        setAlerts(data)
        setLoading(false)
      }
    }).catch(err => {
      if (mounted) {
        setError('Failed to load confirmed alerts')
        setLoading(false)
      }
    })
    return () => { mounted = false }
  }, [])

  const handleGenerateReport = async (alertId: string) => {
    setGeneratingFor(alertId)
    setError(null)
    try {
      const report = await api.getComplianceReport(alertId)
      setGeneratedReports(prev => ({ ...prev, [alertId]: report }))
    } catch (err: any) {
      setError(err.message || 'Failed to generate report')
    } finally {
      setGeneratingFor(null)
    }
  }

  const handleDownloadReport = (alertId: string) => {
    const html = generatedReports[alertId]
    if (!html) return
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `compliance_report_${alertId}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>Compliance Reports</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>Generate and download audit reports for regulatory compliance.</p>
        </div>
      </div>

      {error && (
        <div style={{ padding: 16, background: 'rgba(248,81,73,0.1)', color: 'var(--color-critical)', borderRadius: 8, fontSize: 14, marginBottom: 24 }}>
          <AlertTriangle size={16} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>
          <Loader2 className="spin" size={32} style={{ margin: '0 auto 16px' }} />
          Loading confirmed incidents...
        </div>
      ) : alerts.length === 0 ? (
        <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
            <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--color-surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileText size={32} color="var(--color-text-muted)" />
            </div>
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 8 }}>No reports generated yet</h3>
          <p style={{ fontSize: 14, maxWidth: 400, margin: '0 auto' }}>When a critical alert is confirmed, a compliance report mapping the incident to OISD/DGMS clauses will appear here.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)', paddingBottom: 12 }}>Confirmed Incidents Requiring Audit</h3>
          
          {alerts.map(alert => {
            const isGenerating = generatingFor === alert.id
            const hasReport = !!generatedReports[alert.id]
            
            return (
              <div key={alert.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', padding: '2px 6px', borderRadius: 4, background: 'var(--color-surface-2)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }}>
                      {alert.severity}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                      Confirmed: {new Date(alert.confirmed_at || alert.triggered_at).toLocaleString()}
                    </span>
                  </div>
                  <h4 style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 4 }}>{alert.title}</h4>
                  <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>ID: {alert.id}</div>
                </div>
                
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  {hasReport ? (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-success)', fontSize: 13, fontWeight: 600, marginRight: 12 }}>
                        <CheckCircle size={16} /> Generated
                      </div>
                      <button className="btn" style={{ background: 'var(--color-surface-2)' }} onClick={() => handleDownloadReport(alert.id)}>
                        <Download size={16} style={{ marginRight: 6 }} /> Download HTML
                      </button>
                    </>
                  ) : (
                    <button 
                      className="btn btn-primary" 
                      disabled={isGenerating}
                      onClick={() => handleGenerateReport(alert.id)}
                    >
                      {isGenerating ? <Loader2 className="spin" size={16} /> : <FileText size={16} style={{ marginRight: 6 }} />}
                      {isGenerating ? 'Generating...' : 'Generate Report'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {Object.entries(generatedReports).map(([alertId, html]) => (
        <div key={alertId} className="card animate-fadeIn" style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: 'var(--color-text-secondary)' }}>
            Report Preview — {alertId.slice(0, 8)}…
          </h3>
          <iframe
            title={`Compliance report ${alertId}`}
            srcDoc={html}
            style={{ width: '100%', minHeight: 420, border: '1px solid var(--color-border)', borderRadius: 8 }}
          />
        </div>
      ))}
    </div>
  )
}
