import React, { useEffect, useState } from 'react'
import { api } from '../../services/api'
import type { Permit } from '../../types'

export function PermitTimeline({ zoneId }: { zoneId?: string }) {
  const [permits, setPermits] = useState<Permit[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    const fetchPermits = async () => {
      setLoading(true)
      try {
        // Fallback for now if there is no endpoint to fetch all permits, fetch zone permits
        if (zoneId) {
            const data = await api.getZonePermits(zoneId)
            if (mounted) setPermits(data)
        } else {
            // Ideally an endpoint for all permits would exist. For mock we just show empty.
            if (mounted) setPermits([])
        }
      } catch (err) {
        console.error('Failed to fetch permits', err)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchPermits()
    return () => { mounted = false }
  }, [zoneId])

  if (loading) return <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Loading timeline...</div>

  if (permits.length === 0) return <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>No permits active or recent for this scope.</div>

  // Calculate timeline bounds (last 24h to +12h)
  const now = new Date()
  const minTime = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const maxTime = new Date(now.getTime() + 12 * 60 * 60 * 1000)
  const totalDuration = maxTime.getTime() - minTime.getTime()

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'var(--color-success)'
      case 'closed': return 'var(--color-text-muted)'
      case 'revoked': return 'var(--color-critical)'
      default: return 'var(--color-border)'
    }
  }

  return (
    <div style={{ position: 'relative', paddingTop: 24, paddingBottom: 24 }}>
      {/* Time Axis */}
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: 150, right: 0, borderLeft: '1px solid var(--color-border)', borderRight: '1px solid var(--color-border)' }}>
        {/* Now marker */}
        <div style={{ 
          position: 'absolute', top: 0, bottom: 0, 
          left: `${((now.getTime() - minTime.getTime()) / totalDuration) * 100}%`,
          borderLeft: '1px dashed var(--color-accent)', zIndex: 0
        }}>
          <div style={{ position: 'absolute', top: -20, left: -14, fontSize: 10, color: 'var(--color-accent)', fontWeight: 600 }}>NOW</div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'relative', zIndex: 1 }}>
        {permits.map(permit => {
          const start = new Date(permit.valid_from)
          const end = new Date(permit.valid_to)
          
          // clamp to bounds
          const displayStart = Math.max(start.getTime(), minTime.getTime())
          const displayEnd = Math.min(end.getTime(), maxTime.getTime())
          
          const leftPct = ((displayStart - minTime.getTime()) / totalDuration) * 100
          const widthPct = ((displayEnd - displayStart) / totalDuration) * 100
          const color = getStatusColor(permit.status)

          return (
            <div key={permit.id} style={{ display: 'flex', alignItems: 'center', height: 32 }}>
              <div style={{ width: 140, paddingRight: 10, fontSize: 12, color: 'var(--color-text-secondary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{permit.permit_type.replace('_', ' ')}</span>
                <br/>{permit.status.toUpperCase()}
              </div>
              <div style={{ flex: 1, position: 'relative', height: '100%' }}>
                <div style={{ 
                  position: 'absolute', left: `${leftPct}%`, width: `${widthPct}%`, top: '50%', transform: 'translateY(-50%)',
                  height: 20, borderRadius: 4, background: color, opacity: 0.8,
                  boxShadow: permit.status === 'active' ? `0 0 8px ${color}40` : 'none',
                  display: 'flex', alignItems: 'center', padding: '0 8px', fontSize: 10, color: '#fff', fontWeight: 600, overflow: 'hidden', whiteSpace: 'nowrap'
                }}>
                  {start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
