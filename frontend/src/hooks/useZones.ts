import { useEffect, useState, useCallback } from 'react'
import type { Zone } from '../types'
import { api } from '../services/api'
import { wsManager } from '../services/websocket'
import type { WSMessage } from '../types'

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
      if (msg.type === 'zone_risk_update' && msg.payload) {
        const updated = msg.payload as unknown as Zone
        setZones(prev => prev.map(z => z.id === updated.id ? { ...z, ...updated } : z))
      }
    })
    return unsub
  }, [])

  return { zones, loading, error, refetch: fetchZones }
}
