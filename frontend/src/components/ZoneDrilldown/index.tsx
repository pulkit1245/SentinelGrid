import React, { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { AlertPanel } from '../AlertPanel'
import { PermitTimeline } from '../PermitTimeline'
import type { Zone } from '../../types'
import { Activity, ShieldAlert, Thermometer, Wind } from 'lucide-react'

export function ZoneDrilldown({ zoneId }: { zoneId: string }) {
  const [zone, setZone] = useState<Zone | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    const fetchZone = async () => {
      setLoading(true)
      try {
        const data = await api.getZone(zoneId)
        if (mounted) setZone(data)
      } catch (err) {
        console.error('Failed to fetch zone', err)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchZone()
    return () => { mounted = false }
  }, [zoneId])

  if (loading) {
    return <div style={{ padding: 24, color: 'var(--color-text-muted)' }}>Loading zone details...</div>
  }
  if (!zone) {
    return <div style={{ padding: 24, color: 'var(--color-critical)' }}>Failed to load zone</div>
  }

  const riskColor = zone.current_risk_score > 80 ? 'var(--color-critical)' 
    : zone.current_risk_score > 60 ? 'var(--color-warning)'
    : zone.current_risk_score > 30 ? 'var(--color-watch)'
    : 'var(--color-success)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>{zone.name}</h2>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ 
              fontSize: 12, fontWeight: 600, textTransform: 'uppercase', 
              padding: '4px 8px', borderRadius: 4, 
              background: 'var(--color-surface-2)', color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)'
            }}>
              HAZARD: {zone.hazard_class}
            </span>
            <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>ID: {zone.id}</span>
          </div>
        </div>
        <div style={{ 
          width: 80, height: 80, borderRadius: '50%', 
          border: `4px solid ${riskColor}`,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          boxShadow: `0 0 16px ${riskColor}40`
        }}>
          <span style={{ fontSize: 28, fontWeight: 800, color: riskColor, lineHeight: 1 }}>{zone.current_risk_score}</span>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Risk</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
        {/* Sensors */}
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={18} color="var(--color-accent)" />
            Active Sensors
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {zone.sensors?.map((s: any) => (
              <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'var(--color-surface-2)', borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ color: 'var(--color-text-muted)' }}>
                    {s.sensor_type === 'gas' ? <Wind size={16} /> : s.sensor_type === 'temperature' ? <Thermometer size={16} /> : <Activity size={16} />}
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>{s.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>{s.sensor_type}</div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: s.is_active ? 'var(--color-success)' : 'var(--color-text-muted)' }}>
                    {s.is_active ? 'Active' : 'Offline'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{s.unit}</div>
                </div>
              </div>
            ))}
            {(!zone.sensors || zone.sensors.length === 0) && (
              <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>No sensors registered in this zone.</div>
            )}
          </div>
        </div>

        {/* Alerts */}
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldAlert size={18} color="var(--color-critical)" />
            Recent Alerts
          </h3>
          <AlertPanel zoneId={zoneId} maxHeight="400px" />
        </div>
      </div>

      {/* Permits Timeline */}
      <div className="card">
        <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 16 }}>Permit Timeline</h3>
        <PermitTimeline zoneId={zoneId} />
      </div>
    </div>
  )
}
