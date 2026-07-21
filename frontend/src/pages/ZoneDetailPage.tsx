import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Activity, Thermometer, Wind, Zap, AlertTriangle, ClipboardList } from 'lucide-react'
import type { Zone, Permit } from '../types'
import { api } from '../services/api'
import { useAlerts } from '../hooks/useAlerts'
import { AlertFeed } from '../components/AlertFeed'
import { useAuth } from '../hooks/useAuth'
import { PermitBadge } from '../components/PermitBadge'
import { RiskExplanation } from '../components/RiskExplanation'
import { BlackBoxReplayPanel } from '../components/BlackBox/BlackBoxReplayPanel'

export default function ZoneDetailPage() {
  const { zoneId } = useParams<{ zoneId: string }>()
  const navigate = useNavigate()
  const [zone, setZone] = useState<Zone | null>(null)
  const [permits, setPermits] = useState<Permit[]>([])
  const [loading, setLoading] = useState(true)
  const { alerts, loading: aLoading, confirmAlert } = useAlerts(zoneId)
  const { currentUser } = useAuth()

  useEffect(() => {
    if (!zoneId) return
    Promise.all([
      api.getZone(zoneId),
      api.getZonePermits(zoneId),
    ]).then(([z, p]) => {
      setZone(z)
      setPermits(p)
    }).finally(() => setLoading(false))
  }, [zoneId])

  if (loading) return (
    <div style={{ padding: 28 }}>
      <div className="skeleton" style={{ height: 48, width: 300, marginBottom: 24 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        {[...Array(3)].map((_, i) => <div key={i} className="skeleton" style={{ height: 120 }} />)}
      </div>
    </div>
  )

  if (!zone) return (
    <div style={{ padding: 28, color: 'var(--color-text-secondary)' }}>Zone not found.</div>
  )

  const riskColor = zone.current_risk_score >= 80 ? 'var(--color-critical)'
    : zone.current_risk_score >= 60 ? 'var(--color-warning)'
    : zone.current_risk_score >= 40 ? 'var(--color-watch)'
    : 'var(--color-success)'

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Back + header */}
      <div>
        <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ marginBottom: 16, fontSize: 13 }}>
          <ArrowLeft size={14} /> Back
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>{zone.name}</h1>
          <span className={`badge badge-${zone.hazard_class === 'gas' ? 'warning' : zone.hazard_class === 'thermal' ? 'critical' : 'info'}`}>
            {zone.hazard_class}
          </span>
          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <div style={{ fontSize: 36, fontWeight: 900, color: riskColor, lineHeight: 1 }}>
              {zone.current_risk_score}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Risk Score</div>
          </div>
        </div>
      </div>

      {/* AI Risk Explanation */}
      <RiskExplanation zone={zone} permits={permits} alerts={alerts} />

      {/* Black Box Flight Recorder & Agent Debate Replay */}
      <BlackBoxReplayPanel zoneId={zone.slug || zone.id} />


      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
        <StatChip label="Active Permits" value={zone.active_permit_count} icon={<ClipboardList size={14} />} color="var(--color-accent)" />
        <StatChip label="Active Alerts" value={zone.active_alert_count} icon={<AlertTriangle size={14} />} color="var(--color-warning)" />
      </div>

      {/* Permits */}
      {permits.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: 14 }}>
            Permits
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {permits.map(p => <PermitBadge key={p.id} permit={p} />)}
          </div>
        </div>
      )}

      {/* Alert feed */}
      <div>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: 14 }}>
          Zone Alerts
        </h2>
        <AlertFeed alerts={alerts} loading={aLoading} onConfirm={confirmAlert} userRole={currentUser?.role} />
      </div>
    </div>
  )
}

function StatChip({ label, value, icon, color }: { label: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 18px' }}>
      <div style={{ color, opacity: 0.8 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 20, fontWeight: 800 }}>{value}</div>
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{label}</div>
      </div>
    </div>
  )
}
