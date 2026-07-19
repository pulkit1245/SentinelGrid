import { useEffect, useState, useCallback } from 'react'
import type { Zone } from '../types'
import { api } from '../services/api'
import { wsManager } from '../services/websocket'
import type { WSMessage } from '../types'

/** Normalise zone name for comparison — strips punctuation, lowercases */
function zoneKey(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export function useZones() {
  const [zones, setZones] = useState<Zone[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchZones = useCallback(async () => {
    try {
      const data = await api.getZones()
      setZones(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load zones')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchZones()
  }, [fetchZones])

  // Patch zone risk scores from WebSocket updates
  useEffect(() => {
    const unsub = wsManager.subscribe((msg: WSMessage) => {
      // ── Backend zone_risk_update (UUID match) ────────────────────────────
      if (msg.type === 'zone_risk_update' && msg.payload) {
        const updated = msg.payload as unknown as Zone
        setZones(prev => prev.map(z => z.id === updated.id ? { ...z, ...updated } : z))
        return
      }

      // ── Simulator zone_health_update (name/slug match) ───────────────────
      // Simulator uses slug IDs like "zone-01-degassing"; DB zones have UUIDs.
      // We match by normalising the zone name text on both sides.
      if (msg.type === 'zone_health_update' && msg.payload) {
        const p = msg.payload as {
          zone_id: string
          zone_name: string
          risk_score: number
          status: string
          active_incidents: string[]
          affected_sensors: string[]
        }

        const simKey = zoneKey(p.zone_name || p.zone_id)

        setZones(prev => prev.map(z => {
          // Match by normalised zone name
          if (zoneKey(z.name) !== simKey) return z

          // Map simulator risk_score (0-100) → current_risk_score
          // Convert status string to risk score increment on alert counts
          const criticalCount = p.status === 'critical' ? Math.max(1, z.active_alert_count) : 0

          return {
            ...z,
            current_risk_score: p.risk_score,
            // Bump active_alert_count if incidents are active
            active_alert_count: p.active_incidents.length > 0
              ? Math.max(z.active_alert_count, p.active_incidents.length)
              : z.active_alert_count,
          }
        }))
      }
    })
    return unsub
  }, [])

  return { zones, loading, error, refetch: fetchZones }
}

