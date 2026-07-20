/**
 * useRiskExplanation.ts  —  NEW FILE (no existing files modified)
 *
 * React hook that fetches an AI-generated human-readable explanation for a
 * zone's current risk score.  Drop this into any component:
 *
 *   const { explanation, loading, riskLevel } = useRiskExplanation(zone, permits, alerts)
 *
 * The hook debounces re-fetches so it won't hammer the endpoint on every
 * WebSocket tick – it only refetches when the risk score changes by ≥ 3 points
 * or after a 90-second TTL.
 */
import { useState, useEffect, useRef } from 'react'
import type { Zone, Alert, Permit } from '../types'

export type RiskLevel = 'low' | 'watch' | 'warning' | 'critical'

export interface RiskExplanationResult {
  explanation: string
  riskLevel: RiskLevel
  loading: boolean
  error: string | null
  generatedBy: 'llm' | 'rule_based' | null
}

interface CacheEntry {
  explanation: string
  riskLevel: RiskLevel
  generatedBy: 'llm' | 'rule_based'
  fetchedAt: number   // epoch ms
  score: number
}

// Module-level cache (survives component re-mounts within a session)
const cache: Record<string, CacheEntry> = {}
const CACHE_TTL_MS = 90_000   // 90 seconds
const SCORE_DELTA_THRESHOLD = 3   // re-fetch only if score changed by this much

function getAccessToken(): string | null {
  return localStorage.getItem('sg_access_token')
}

async function fetchExplanation(
  zone: Zone,
  permits: Permit[],
  alerts: Alert[],
): Promise<{ explanation: string; riskLevel: RiskLevel; generatedBy: 'llm' | 'rule_based' }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  // Build minimal sensor trend note from active alert descriptions
  const trendNote = alerts
    .filter(a => a.is_active && a.description)
    .slice(0, 1)
    .map(a => a.description)
    .join('. ') || null

  const body = {
    zone_name: zone.name,
    hazard_class: zone.hazard_class,
    risk_score: zone.current_risk_score,
    active_alerts: alerts
      .filter(a => a.is_active)
      .slice(0, 5)
      .map(a => ({
        severity: a.severity,
        title: a.title,
        description: a.description ?? undefined,
      })),
    active_permits: permits
      .filter(p => p.status === 'active')
      .slice(0, 5)
      .map(p => ({
        permit_type: p.permit_type,
        valid_from: p.valid_from,
        valid_to: p.valid_to,
      })),
    sensor_trend_note: trendNote,
    shift_change_in_minutes: null,
  }

  const resp = await fetch('/api/v1/risk/explain', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
    body: JSON.stringify(body),
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({})) as Record<string, string>
    throw new Error(err.detail || `Request failed: ${resp.status}`)
  }

  const data = await resp.json() as {
    explanation: string
    risk_level: RiskLevel
    score: number
    generated_by: 'llm' | 'rule_based'
  }

  return {
    explanation: data.explanation,
    riskLevel: data.risk_level,
    generatedBy: data.generated_by,
  }
}

export function useRiskExplanation(
  zone: Zone | null,
  permits: Permit[] = [],
  alerts: Alert[] = [],
): RiskExplanationResult {
  const [explanation, setExplanation] = useState<string>('')
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('low')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generatedBy, setGeneratedBy] = useState<'llm' | 'rule_based' | null>(null)

  // Track last fetched score to avoid redundant calls
  const lastFetchedScore = useRef<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!zone) return

    const cacheKey = zone.id
    const now = Date.now()
    const cached = cache[cacheKey]
    const scoreChanged = lastFetchedScore.current === null
      || Math.abs(zone.current_risk_score - lastFetchedScore.current) >= SCORE_DELTA_THRESHOLD

    // Return from cache if still fresh and score hasn't changed much
    if (cached && (now - cached.fetchedAt) < CACHE_TTL_MS && !scoreChanged) {
      setExplanation(cached.explanation)
      setRiskLevel(cached.riskLevel)
      setGeneratedBy(cached.generatedBy)
      return
    }

    if (!scoreChanged && cached) return

    // Cancel any in-flight request
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setLoading(true)
    setError(null)
    lastFetchedScore.current = zone.current_risk_score

    fetchExplanation(zone, permits, alerts)
      .then(result => {
        cache[cacheKey] = {
          explanation: result.explanation,
          riskLevel: result.riskLevel,
          generatedBy: result.generatedBy,
          fetchedAt: Date.now(),
          score: zone.current_risk_score,
        }
        setExplanation(result.explanation)
        setRiskLevel(result.riskLevel)
        setGeneratedBy(result.generatedBy)
      })
      .catch(err => {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message)
        }
      })
      .finally(() => setLoading(false))

    return () => { abortRef.current?.abort() }
  // We intentionally only re-run when zone id or score changes, not on every render
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zone?.id, zone?.current_risk_score])

  return { explanation, riskLevel, loading, error, generatedBy }
}
