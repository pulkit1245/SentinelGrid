import { useCallback, useEffect, useState } from 'react';
import type { Alert, WSMessage } from '../types';
import { api } from '../services/api';
import { wsManager } from '../services/websocket';

interface UseLiveAlertsResult {
  alerts: Alert[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useLiveAlerts(): UseLiveAlertsResult {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAlerts();
      setAlerts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Real-time updates via WebSocket
  useEffect(() => {
    const unsubscribe = wsManager.subscribe((msg: WSMessage) => {
      if (msg.type === 'new_alert') {
        const newAlert = msg.payload as unknown as Alert;
        setAlerts(prev => [newAlert, ...prev]);
      } else if (msg.type === 'alert_confirmed') {
        const payload = msg.payload as { alert_id: string; confirmed_by: string; confirmed_at: string };
        setAlerts(prev =>
          prev.map(a =>
            a.id === payload.alert_id
              ? { ...a, is_active: false, confirmed_by: payload.confirmed_by, confirmed_at: payload.confirmed_at }
              : a,
          ),
        );
      }
    });
    return unsubscribe;
  }, []);

  return { alerts, loading, error, refetch: fetchAlerts };
}
