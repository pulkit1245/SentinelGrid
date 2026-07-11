import { useEffect, useState, useCallback } from 'react'
import type { Alert } from '../types'
import { api } from '../services/api'
import { wsManager } from '../services/websocket'
import type { WSMessage } from '../types'

export function useAlerts(zoneId?: string) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.getAlerts(zoneId ? { zone_id: zoneId } : undefined)
      setAlerts(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }, [zoneId])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])

  useEffect(() => {
    const unsub = wsManager.subscribe((msg: WSMessage) => {
      if (msg.type === 'new_alert') {
        const alert = msg.payload as Alert
        if (!zoneId || alert.zone_id === zoneId) {
          setAlerts(prev => [alert, ...prev])
        }
      }
      if (msg.type === 'alert_confirmed') {
        const { alert_id, confirmed_by, confirmed_at } = msg.payload as { alert_id: string; confirmed_by: string; confirmed_at: string }
        setAlerts(prev => prev.map(a => a.id === alert_id ? { ...a, confirmed_by, confirmed_at } : a))
      }
    })
    return unsub
  }, [zoneId])

  const confirmAlert = useCallback(async (alertId: string) => {
    const result = await api.confirmAlert(alertId)
    setAlerts(prev => prev.map(a => a.id === alertId
      ? { ...a, confirmed_by: result.confirmed_by, confirmed_at: result.confirmed_at }
      : a
    ))
    return result
  }, [])

  return { alerts, loading, error, refetch: fetchAlerts, confirmAlert }
}
