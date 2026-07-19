import React, { useEffect, useState } from 'react'
import { Activity, AlertTriangle, Shield, Zap } from 'lucide-react'
import { useZones } from '../hooks/useZones'
import { useAlerts } from '../hooks/useAlerts'
import { ZoneCard } from '../components/ZoneCard'
import { AlertFeed } from '../components/AlertFeed'
import { RiskScoreChart } from '../components/RiskScoreChart'
import { wsManager } from '../services/websocket'
import { useAuth } from '../hooks/useAuth'

export default function CockpitPage() {
  const { zones, loading: zLoading } = useZones()
  const { alerts, loading: aLoading, confirmAlert } = useAlerts()
  const { currentUser } = useAuth()
  const [wsConnected, setWsConnected] = useState(false)
  // Live sensor counts from simulator (updated every second)
  const [liveCritical, setLiveCritical] = useState(0)
  const [liveWarning, setLiveWarning] = useState(0)

  const criticalCount = Math.max(alerts.filter(a => a.severity === 'critical' && a.is_active).length, liveCritical)
  const activeAlerts  = Math.max(alerts.filter(a => a.is_active).length, liveWarning + liveCritical)
  const avgRisk = zones.length ? Math.round(zones.reduce((s, z) => s + z.current_risk_score, 0) / zones.length) : 0

  useEffect(() => {
    // onConnectionChange fires immediately with current state, then on every change
    const unsub = wsManager.onConnectionChange(connected => setWsConnected(connected))
    return unsub
  }, [])

  // Track live critical/warning sensor counts from simulator
  useEffect(() => {
    const unsub = wsManager.subscribe(msg => {
      if (msg.type !== 'simulator_tick') return
      // simulator_tick fires every 10 ticks with sensor_count — we use zone_health to derive counts
    })
    return unsub
  }, [])

  // Derive live critical/warning counts from incoming sensor_update events
  const sensorStatusRef = React.useRef<Record<string, string>>({})
  useEffect(() => {
    const unsub = wsManager.subscribe(msg => {
      if (msg.type !== 'sensor_update') return
      const p = msg.payload as { id?: string; sensor_id?: string; status?: string }
      const sid = p.id ?? p.sensor_id
      if (!sid || !p.status) return
      sensorStatusRef.current[sid] = p.status
      // Recount
      const statuses = Object.values(sensorStatusRef.current)
      setLiveCritical(statuses.filter(s => s === 'critical').length)
      setLiveWarning(statuses.filter(s => s === 'warning' || s === 'high_risk').length)
    })
    return unsub
  }, [])

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.3px' }}>Operations Command Centre</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: 4, fontSize: 13 }}>
            Real-time compound-risk monitoring across all plant zones
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-full)', fontSize: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: wsConnected ? 'var(--color-success)' : 'var(--color-text-muted)', display: 'inline-block' }} />
          {wsConnected ? 'Live Feed Connected' : 'Connecting…'}
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <KpiCard icon={<AlertTriangle size={18} />} label="Active Alerts" value={activeAlerts} color="var(--color-warning)" />
        <KpiCard icon={<Zap size={18} />} label="Critical" value={criticalCount} color="var(--color-critical)" pulse={criticalCount > 0} />
        <KpiCard icon={<Activity size={18} />} label="Avg Risk Score" value={`${avgRisk}/100`} color="var(--color-accent)" />
        <KpiCard icon={<Shield size={18} />} label="Zones Monitored" value={zones.length} color="var(--color-success)" />
      </div>

      {/* Main layout: zone grid + alert feed */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, alignItems: 'start' }}>
        {/* Zone grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Zones ({zones.length})
          </h2>
          {zLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 140, borderRadius: 'var(--radius-lg)' }} />)}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
              {zones.map(zone => <ZoneCard key={zone.id} zone={zone} />)}
            </div>
          )}

          {/* Risk trend chart */}
          {!zLoading && zones.length > 0 && (
            <div className="card" style={{ marginTop: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Zone Risk Snapshot</h3>
              <RiskScoreChart zones={zones} />
            </div>
          )}
        </div>

        {/* Alert feed */}
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 16 }}>
            Alert Feed
          </h2>
          <AlertFeed alerts={alerts} loading={aLoading} onConfirm={confirmAlert} userRole={currentUser?.role} />
        </div>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value, color, pulse }: {
  icon: React.ReactNode; label: string; value: number | string; color: string; pulse?: boolean
}) {
  return (
    <div
      className={`card ${pulse ? 'pulse-critical' : ''}`}
      style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '18px 20px' }}
    >
      <div style={{
        width: 40, height: 40, borderRadius: 'var(--radius-md)',
        background: `${color}18`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', color, flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--color-text-primary)', lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>{label}</div>
      </div>
    </div>
  )
}
