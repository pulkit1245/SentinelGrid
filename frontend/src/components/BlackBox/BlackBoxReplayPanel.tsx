import React, { useEffect, useState, useRef } from 'react'
import { Play, Pause, RotateCcw, Cpu, ShieldAlert, AlertTriangle, FileText, Activity, FastForward, CheckCircle } from 'lucide-react'
import type { BlackBoxEntry, AgentTranscriptResponse } from '../../types'
import { api } from '../../services/api'

interface BlackBoxReplayPanelProps {
  zoneId?: string
  onZoneChange?: (zoneId: string) => void
}

export function BlackBoxReplayPanel({ zoneId = 'zone-01-degassing', onZoneChange }: BlackBoxReplayPanelProps) {
  const [currentZone, setCurrentZone] = useState(zoneId)
  const [timeline, setTimeline] = useState<BlackBoxEntry[]>([])
  const [storyBeats, setStoryBeats] = useState<BlackBoxEntry[]>([])
  const [selectedTimeS, setSelectedTimeS] = useState<number>(0)
  const [transcript, setTranscript] = useState<AgentTranscriptResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)
  const [isSimulating, setIsSimulating] = useState<boolean>(false)

  const timerRef = useRef<any>(null)

  useEffect(() => {
    setCurrentZone(zoneId)
  }, [zoneId])

  // Fetch timeline and story beats when zone changes
  useEffect(() => {
    loadData(currentZone)
  }, [currentZone])

  // Fetch agent transcript whenever selected time changes
  useEffect(() => {
    if (timeline.length === 0) return
    api.getAgentTranscript(currentZone, selectedTimeS)
      .then(res => setTranscript(res))
      .catch(err => console.error('Failed to load agent transcript:', err))
  }, [currentZone, selectedTimeS, timeline])

  // Auto-play interval handler
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setStoryBeats(prevBeats => {
          if (prevBeats.length === 0) return prevBeats
          setSelectedTimeS(currTime => {
            // Find next story beat or loop
            const beatTimes = prevBeats.map(b => b.sim_time_s)
            const nextTime = beatTimes.find(t => t > currTime)
            if (nextTime !== undefined) {
              return nextTime
            } else {
              setIsPlaying(false)
              return currTime
            }
          })
          return prevBeats
        })
      }, 1800)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isPlaying])

  const loadData = async (zId: string) => {
    setLoading(true)
    try {
      const [tData, bData] = await Promise.all([
        api.getBlackBoxTimeline(zId),
        api.getBlackBoxStoryBeats(zId),
      ])
      setTimeline(tData)
      setStoryBeats(bData)
      if (bData.length > 0) {
        // Find first critical beat or first beat
        const firstCrit = bData.find(b => b.decision === 'critical')
        setSelectedTimeS(firstCrit ? firstCrit.sim_time_s : bData[0].sim_time_s)
      } else if (tData.length > 0) {
        setSelectedTimeS(tData[0].sim_time_s)
      }
    } catch (err) {
      console.error('Failed to load black box data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSimulate = async () => {
    setIsSimulating(true)
    try {
      await api.simulateBlackBoxScenario(currentZone)
      await loadData(currentZone)
    } catch (err) {
      console.error('Simulation failed:', err)
    } finally {
      setIsSimulating(false)
    }
  }

  const maxSimTime = timeline.length > 0 ? timeline[timeline.length - 1].sim_time_s : 4200
  const currentBeat = timeline.find(e => e.sim_time_s === selectedTimeS) ||
                      timeline.reduce((prev, curr) => (curr.sim_time_s <= selectedTimeS ? curr : prev), timeline[0])

  const getDecisionBadge = (decision?: string) => {
    const d = (decision || 'clear').toLowerCase()
    if (d === 'critical') return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', color: '#f87171', label: 'CRITICAL ESCALATION' }
    if (d === 'advisory') return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', color: '#fbbf24', label: 'ADVISORY (MONITORING)' }
    return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', color: '#34d399', label: 'CLEAR (ALL NORMAL)' }
  }

  const getSpeakerStyle = (speaker: string) => {
    if (speaker.includes('Hard-Rules')) return { color: '#f87171', icon: <ShieldAlert size={14} />, bg: 'rgba(239, 68, 68, 0.08)' }
    if (speaker.includes('Compound')) return { color: '#c084fc', icon: <Activity size={14} />, bg: 'rgba(168, 85, 247, 0.08)' }
    if (speaker.includes('Permit')) return { color: '#fbbf24', icon: <FileText size={14} />, bg: 'rgba(245, 158, 11, 0.08)' }
    return { color: '#60a5fa', icon: <Cpu size={14} />, bg: 'rgba(59, 130, 246, 0.08)' }
  }

  const activeBadge = getDecisionBadge(currentBeat?.decision)

  if (loading) {
    return (
      <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="skeleton" style={{ height: 32, width: '40%' }} />
        <div className="skeleton" style={{ height: 120 }} />
        <div className="skeleton" style={{ height: 200 }} />
      </div>
    )
  }

  return (
    <div className="card" style={{
      padding: '24px',
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
      boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
    }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)',
          }}>
            <Cpu size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.2px', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              Black Box Flight Recorder & Multi-Agent Debate
            </h2>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '2px 0 0' }}>
              Historical decision replay & multi-agent reasoning transcript for <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{currentZone}</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleSimulate}
            disabled={isSimulating}
            className="btn btn-ghost"
            style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, border: '1px solid var(--color-border)' }}
          >
            <RotateCcw size={13} className={isSimulating ? 'spin' : ''} />
            {isSimulating ? 'Simulating…' : 'Re-Run Incident Scenario'}
          </button>
        </div>
      </div>

      {/* Decision Banner & Status Pill */}
      <div style={{
        padding: '16px 20px',
        background: activeBadge.bg,
        border: `1px solid ${activeBadge.border}`,
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        transition: 'all 0.3s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: activeBadge.color, textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: activeBadge.color, display: 'inline-block', boxShadow: `0 0 8px ${activeBadge.color}` }} />
            {activeBadge.label}
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', borderLeft: '1px solid var(--color-border)', paddingLeft: 12 }}>
            Sim Time: <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-text-primary)' }}>{(selectedTimeS / 60).toFixed(1)} min</span> ({selectedTimeS}s)
          </div>
        </div>

        {/* Corroborating Signals Pill */}
        {currentBeat && (
          <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>Corroborating Signals:</span>
            <span className="badge badge-info" style={{ fontFamily: 'monospace', fontWeight: 700 }}>
              {currentBeat.corroborating_signals.length} signal(s)
            </span>
          </div>
        )}
      </div>

      {/* Timeline Controls & Time Slider */}
      <div style={{
        background: 'var(--color-surface-2)',
        padding: '16px 20px',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        border: '1px solid var(--color-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="btn btn-primary"
              style={{
                fontSize: 13,
                padding: '6px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                borderRadius: 'var(--radius-full)',
                fontWeight: 700,
              }}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} />}
              {isPlaying ? 'Pause Video Replay' : 'Play Story Beats'}
            </button>
            <button
              onClick={() => {
                if (storyBeats.length > 0) setSelectedTimeS(storyBeats[0].sim_time_s)
              }}
              className="btn btn-ghost"
              style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <RotateCcw size={12} /> Reset to Start
            </button>
          </div>

          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
            0.0 min — {(maxSimTime / 60).toFixed(1)} min ({timeline.length} cycles recorded)
          </div>
        </div>

        {/* Slider Input */}
        <input
          type="range"
          min={0}
          max={maxSimTime}
          step={30}
          value={selectedTimeS}
          onChange={(e) => setSelectedTimeS(Number(e.target.value))}
          style={{
            width: '100%',
            accentColor: 'var(--color-accent)',
            cursor: 'pointer',
            height: 6,
          }}
        />

        {/* Story Beats Navigation Chips */}
        {storyBeats.length > 0 && (
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <FastForward size={12} /> Key Story Beats (Moments Decision Changed):
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {storyBeats.map((beat, idx) => {
                const isSelected = beat.sim_time_s === selectedTimeS
                const bStyle = getDecisionBadge(beat.decision)
                return (
                  <button
                    key={idx}
                    onClick={() => setSelectedTimeS(beat.sim_time_s)}
                    style={{
                      background: isSelected ? bStyle.border : 'var(--color-surface)',
                      color: isSelected ? '#fff' : bStyle.color,
                      border: `1px solid ${bStyle.border}`,
                      borderRadius: 'var(--radius-full)',
                      padding: '4px 12px',
                      fontSize: 11,
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      transition: 'all 0.2s ease',
                      boxShadow: isSelected ? `0 0 10px ${bStyle.border}` : 'none',
                    }}
                  >
                    <span>t={(beat.sim_time_s / 60).toFixed(1)}m</span>
                    <span style={{ textTransform: 'uppercase', opacity: 0.9 }}>{beat.decision}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Multi-Agent Debate Transcript */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
            <Cpu size={16} color="var(--color-accent)" />
            Agent Debate Transcript (Cycle at t={(selectedTimeS / 60).toFixed(1)} min)
          </h3>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', background: 'var(--color-surface-2)', padding: '3px 8px', borderRadius: 4 }}>
            Multi-Agent Dialogue
          </span>
        </div>

        {transcript && transcript.lines && transcript.lines.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {transcript.lines.map((ln, idx) => {
              const spkStyle = getSpeakerStyle(ln.speaker)
              return (
                <div
                  key={idx}
                  style={{
                    background: spkStyle.bg,
                    border: `1px solid ${spkStyle.color}33`,
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: spkStyle.color, fontWeight: 700, fontSize: 12 }}>
                    {spkStyle.icon}
                    <span>{ln.speaker}</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--color-text-primary)', lineHeight: 1.5, paddingLeft: 22 }}>
                    {ln.message}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13, background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)' }}>
            No agent transcript lines recorded for this timestamp.
          </div>
        )}
      </div>

      {/* Snapshot Details (Hard Rules, Compound Finding, Permits) */}
      {currentBeat && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginTop: 4 }}>
          {/* Hard Rules Floor */}
          <div className="card" style={{ padding: 14, background: 'var(--color-surface-2)', fontSize: 12 }}>
            <div style={{ fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={14} color="#f87171" /> Hard Rules Floor
            </div>
            {currentBeat.hard_rule_violation ? (
              <div style={{ color: '#f87171', fontWeight: 600 }}>
                Breached: {currentBeat.hard_rule_violation.sensor_type} = {currentBeat.hard_rule_violation.value} (Limit: {currentBeat.hard_rule_violation.threshold})
              </div>
            ) : (
              <div style={{ color: 'var(--color-text-muted)' }}>No statutory thresholds breached.</div>
            )}
          </div>

          {/* Compound Risk Agent Finding */}
          <div className="card" style={{ padding: 14, background: 'var(--color-surface-2)', fontSize: 12 }}>
            <div style={{ fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Activity size={14} color="#c084fc" /> Compound Risk Finding
            </div>
            {currentBeat.compound_finding_summary ? (
              <div>
                <div style={{ fontWeight: 600, color: currentBeat.compound_finding_summary.triggered ? '#f87171' : '#fbbf24' }}>
                  {currentBeat.compound_finding_summary.triggered ? 'Triggered' : 'Partial Match'} ({currentBeat.compound_finding_summary.signal_count}/3 signals)
                </div>
                <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                  {currentBeat.compound_finding_summary.reasons.join('; ')}
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--color-text-muted)' }}>No compound risk pattern active.</div>
            )}
          </div>

          {/* Permit Intelligence Finding */}
          <div className="card" style={{ padding: 14, background: 'var(--color-surface-2)', fontSize: 12 }}>
            <div style={{ fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <FileText size={14} color="#fbbf24" /> Permit Intelligence
            </div>
            {currentBeat.permit_violations_summary && currentBeat.permit_violations_summary.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {currentBeat.permit_violations_summary.map((v, i) => (
                  <div key={i} style={{ color: v.severity === 'critical' ? '#f87171' : '#fbbf24', fontWeight: 600 }}>
                    {v.reason}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--color-text-muted)' }}>All active permits compliant.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
