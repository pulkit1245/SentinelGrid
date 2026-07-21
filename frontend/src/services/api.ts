import type { Alert, BlackBoxEntry, AgentTranscriptResponse, Permit, RAGResponse, Zone } from '../types'
import { authApi } from './auth'

// Initialize from localStorage so API calls work immediately on page reload
let _accessToken: string | null = localStorage.getItem('sg_access_token')

// Called by App.tsx useEffect whenever the context token changes.
// Only updates the module variable — localStorage is managed solely by AuthContext.
export const setApiToken = (t: string | null) => { _accessToken = t }

const BASE = '/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`

  let resp = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' })

  // Silently refresh on 401 and retry once
  if (resp.status === 401 && _accessToken) {
    try {
      const { access_token } = await authApi.refreshToken()
      _accessToken = access_token
      localStorage.setItem('sg_access_token', access_token)
      headers['Authorization'] = `Bearer ${access_token}`
      resp = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' })
    } catch {
      _accessToken = null
      localStorage.removeItem('sg_access_token')  // wipe stale token
      window.location.href = '/login'
      throw new Error('Session expired')
    }
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `Request failed: ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  // ── Zones ──────────────────────────────────────────────────────────────────
  getZones: () => request<{ zones: Zone[]; total: number }>('/zones').then(r => r.zones),
  getZone: (id: string) => request<Zone>(`/zones/${id}`),

  // ── Black Box & Agent Transcript ─────────────────────────────────────────────
  getBlackBoxTimeline: (zoneId: string) =>
    request<BlackBoxEntry[]>(`/zones/${zoneId}/black-box`),
  getBlackBoxStoryBeats: (zoneId: string) =>
    request<BlackBoxEntry[]>(`/zones/${zoneId}/black-box/changes`),
  getAgentTranscript: (zoneId: string, simTimeS?: number) =>
    request<AgentTranscriptResponse>(`/zones/${zoneId}/transcript${simTimeS !== undefined ? `?sim_time_s=${simTimeS}` : ''}`),
  simulateBlackBoxScenario: (zoneId: string) =>
    request<{ status: string; zone_id: string; entry_count: number; story_beat_count: number }>(
      `/zones/${zoneId}/black-box/simulate`, { method: 'POST' }
    ),

  // ── Sensors ────────────────────────────────────────────────────────────────
  getSensorReadings: (sensorId: string, limit = 100) =>
    request<Array<{ sensor_id: string; reading_value: number; recorded_at: string }>>(
      `/sensors/${sensorId}/readings?limit=${limit}`
    ),

  // ── Permits ────────────────────────────────────────────────────────────────
  createPermit: (data: Omit<Permit, 'id' | 'status'>) =>
    request<Permit>('/permits', { method: 'POST', body: JSON.stringify(data) }),
  revokePermit: (id: string) =>
    request<Permit>(`/permits/${id}/revoke`, { method: 'PATCH' }),
  getZonePermits: (zoneId: string) =>
    request<Permit[]>(`/permits/zone/${zoneId}`),

  // ── Alerts ─────────────────────────────────────────────────────────────────
  getAlerts: (params?: { zone_id?: string; severity?: string }) => {
    const qs = new URLSearchParams(params as Record<string, string> || {}).toString()
    return request<Alert[]>(`/alerts${qs ? `?${qs}` : ''}`)
  },
  getConfirmedAlerts: () => request<Alert[]>('/alerts/confirmed'),
  getAlert: (id: string) => request<Alert>(`/alerts/${id}`),
  confirmAlert: (id: string) =>
    request<{ id: string; confirmed_by: string; confirmed_at: string; message: string }>(
      `/alerts/${id}/confirm`, { method: 'PATCH' }
    ),

  // ── RAG ────────────────────────────────────────────────────────────────────
  ragQuery: (question: string) =>
    request<RAGResponse>('/rag/query', { method: 'POST', body: JSON.stringify({ question }) }),

  // ── Compliance ─────────────────────────────────────────────────────────────
  getComplianceReport: async (alertId: string): Promise<string> => {
    const headers: Record<string, string> = {}
    if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`

    let resp = await fetch(`${BASE}/compliance/report/${alertId}`, { headers, credentials: 'include' })
    if (resp.status === 401 && _accessToken) {
      try {
        const { access_token } = await authApi.refreshToken()
        _accessToken = access_token
        localStorage.setItem('sg_access_token', access_token)
        headers['Authorization'] = `Bearer ${access_token}`
        resp = await fetch(`${BASE}/compliance/report/${alertId}`, { headers, credentials: 'include' })
      } catch {
        _accessToken = null
        localStorage.removeItem('sg_access_token')
        window.location.href = '/login'
        throw new Error('Session expired')
      }
    }

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to generate compliance report')
    }
    return resp.text()
  },
}

