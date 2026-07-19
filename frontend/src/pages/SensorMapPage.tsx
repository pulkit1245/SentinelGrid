import React, { useEffect, useRef, useState } from 'react'
import { useSensorMap } from '../hooks/useSensorMap'
import { useSiren } from '../hooks/useSiren'
import { FloorPlanCanvas } from '../components/SensorMap/FloorPlanCanvas'
import { DashboardStatsPanel } from '../components/SensorMap/DashboardStatsPanel'
import { IncidentTimeline } from '../components/SensorMap/IncidentTimeline'
import { ManualTestControls } from '../components/SensorMap/ManualTestControls'
import { SensorDetailCard } from '../components/SensorMap/SensorDetailCard'
import { CriticalAlertBanner } from '../components/SensorMap/CriticalAlertBanner'
import { wsManager } from '../services/websocket'
import type { SensorIncident } from '../types'

const SIMULATOR_URL = 'http://localhost:8002'

export default function SensorMapPage() {
  const {
    sensors, zoneRisks, incidents, stats,
    selectedSensor, setSelectedSensor,
    hoveredSensor, setHoveredSensor,
    focusedSensorId,
    triggerScenario,
    clearIncidents,
  } = useSensorMap()

  // ── WebSocket connection status ───────────────────────────────────────────
  const [wsConnected, setWsConnected] = useState(wsManager.isConnected)
  useEffect(() => wsManager.onConnectionChange(setWsConnected), [])

  // ── Siren ─────────────────────────────────────────────────────────────────
  const { play: sirenPlay, stop: sirenStop, mute: sirenMute, unmute: sirenUnmute, muted: sirenMuted } = useSiren()

  // ── Critical incident tracking ────────────────────────────────────────────
  const [activeCritical, setActiveCritical] = useState<SensorIncident[]>([])
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const lastCriticalIdRef = useRef<string | null>(null)

  // Detect new critical transitions from incident timeline
  useEffect(() => {
    if (incidents.length === 0) return
    const newest = incidents[0]

    // Only fire siren on new critical transitions (not re-renders)
    if (
      newest.new_status === 'critical' &&
      newest.id !== lastCriticalIdRef.current
    ) {
      lastCriticalIdRef.current = newest.id
      setBannerDismissed(false)

      // Collect all currently critical sensors
      const criticals = incidents
        .filter(i => i.new_status === 'critical')
        .slice(0, 8)  // cap at 8 for display
      setActiveCritical(criticals)

      // Trigger siren
      sirenPlay(12_000)  // 12 seconds max
    }

    // Auto-clear banner when no sensors are critical anymore
    const anyCritical = sensors.some(s => s.status === 'critical')
    if (!anyCritical) {
      setActiveCritical([])
      sirenStop()
    }
  }, [incidents, sensors, sirenPlay, sirenStop])

  const handleDismiss = () => {
    setBannerDismissed(true)
    sirenStop()
  }

  // ── Server-side scenario triggers (hit simulator REST API) ─────────────────
  const serverTrigger = async (type: string, zoneId: string) => {
    try {
      const endpoint = `${SIMULATOR_URL}/simulate/${type}`
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zoneId, severity: 'critical', duration: 180 }),
      })
    } catch (e) {
      // Fallback to local simulation if simulator not reachable
      console.warn('Simulator unreachable, using local simulation')
    }
  }

  const handleTriggerScenario = async (type: Parameters<typeof triggerScenario>[0], targetId?: string) => {
    // Map frontend scenario types to simulator endpoints + zones
    const serverMap: Record<string, [string, string]> = {
      gas_leak:         ['gas-leak',   'zone-01-degassing'],
      fire:             ['fire',        'zone-02-castfloor'],
      pressure_failure: ['pressure-spike', 'zone-05-compressor'],
    }
    const serverArgs = serverMap[type]
    if (serverArgs) {
      await serverTrigger(serverArgs[0], serverArgs[1])
    }
    // Also update local state immediately for snappy UI
    triggerScenario(type, targetId)
  }

  const showBanner = activeCritical.length > 0 && !bannerDismissed

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden',
      paddingTop: showBanner ? 62 : 0,  // push content below banner
      transition: 'padding-top 0.3s ease',
    }}>

      {/* Critical alert banner — fixed above everything */}
      {showBanner && (
        <CriticalAlertBanner
          criticalIncidents={activeCritical}
          muted={sirenMuted}
          onMute={sirenMute}
          onUnmute={() => { sirenUnmute(); sirenPlay(8_000) }}
          onDismiss={handleDismiss}
        />
      )}

      {/* Stats bar */}
      <DashboardStatsPanel stats={stats} wsConnected={wsConnected} />

      {/* Main content: floor plan + right panel */}
      <div style={{ display: 'flex', flex: 1, gap: 16, padding: '16px', overflow: 'hidden', minHeight: 0 }}>
        {/* Floor plan */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto', minWidth: 0 }}>
          <FloorPlanCanvas
            sensors={sensors}
            zoneRisks={zoneRisks}
            focusedSensorId={focusedSensorId}
            hoveredSensor={hoveredSensor}
            onHover={setHoveredSensor}
            onSelectSensor={setSelectedSensor}
          />
          <ManualTestControls onTrigger={handleTriggerScenario} />
        </div>

        {/* Right panel: incident timeline */}
        <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <IncidentTimeline incidents={incidents} onClear={clearIncidents} />
        </div>
      </div>

      {/* Sensor detail card */}
      {selectedSensor && (
        <SensorDetailCard
          sensor={selectedSensor}
          onClose={() => setSelectedSensor(null)}
          onTriggerOffline={id => {
            triggerScenario('sensor_offline', id)
            setSelectedSensor(null)
          }}
          onResetSensor={id => {
            triggerScenario('reset_sensor', id)
            setSelectedSensor(null)
          }}
        />
      )}
    </div>
  )
}
