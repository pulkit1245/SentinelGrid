/**
 * CriticalAlertBanner.tsx
 *
 * Full-width sticky alert banner that appears when any sensor goes critical.
 * Shows sensor name, zone, value — with a pulsing red glow animation.
 * Includes mute/unmute siren toggle and manual dismiss.
 */
import React, { useEffect, useRef } from 'react'
import { AlertTriangle, Volume2, VolumeX, X, Siren } from 'lucide-react'
import type { SensorIncident } from '../../types'

interface CriticalAlertBannerProps {
  criticalIncidents: SensorIncident[]   // newest critical transitions
  muted: boolean
  onMute: () => void
  onUnmute: () => void
  onDismiss: () => void
}

export function CriticalAlertBanner({
  criticalIncidents,
  muted,
  onMute,
  onUnmute,
  onDismiss,
}: CriticalAlertBannerProps) {
  if (criticalIncidents.length === 0) return null

  const latest = criticalIncidents[0]
  const count = criticalIncidents.length

  return (
    <>
      {/* Pulsing red screen-edge glow */}
      <div style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 998,
        boxShadow: 'inset 0 0 80px rgba(248, 81, 73, 0.35)',
        animation: 'critical-edge-pulse 1s ease-in-out infinite',
      }} />

      {/* Main banner */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 999,
        background: 'linear-gradient(135deg, #1a0505 0%, #2d0808 50%, #1a0505 100%)',
        borderBottom: '2px solid #f85149',
        boxShadow: '0 4px 32px rgba(248,81,73,0.6)',
        padding: '10px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        animation: 'banner-slide-down 0.3s ease forwards',
      }}>

        {/* Animated siren icon */}
        <div style={{
          width: 40, height: 40,
          background: 'rgba(248,81,73,0.2)',
          border: '1px solid rgba(248,81,73,0.5)',
          borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'siren-icon-flash 0.5s ease-in-out infinite alternate',
          flexShrink: 0,
        }}>
          <AlertTriangle size={20} color="#f85149" />
        </div>

        {/* Alert text */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 14, fontWeight: 800, color: '#f85149',
            letterSpacing: '0.04em', textTransform: 'uppercase',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            ⚠ CRITICAL CONDITION DETECTED
            {count > 1 && (
              <span style={{
                fontSize: 11, fontWeight: 700,
                background: 'rgba(248,81,73,0.25)',
                border: '1px solid rgba(248,81,73,0.4)',
                color: '#f85149',
                padding: '1px 8px', borderRadius: 20,
              }}>
                {count} sensors
              </span>
            )}
          </div>
          <div style={{
            fontSize: 12, color: 'rgba(248, 200, 200, 0.85)',
            marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            <strong style={{ color: '#ffcdd2' }}>{latest.sensor_name}</strong>
            {' '} in <strong style={{ color: '#ffcdd2' }}>{latest.zone_name}</strong>
            {' '} — {latest.value.toFixed(2)} {latest.unit}
            {count > 1 && ` (+${count - 1} more)`}
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <button
            onClick={muted ? onUnmute : onMute}
            title={muted ? 'Unmute siren' : 'Mute siren'}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 8,
              background: muted ? 'rgba(248,81,73,0.1)' : 'rgba(248,81,73,0.25)',
              border: '1px solid rgba(248,81,73,0.4)',
              color: '#f85149', cursor: 'pointer',
              fontSize: 11, fontWeight: 700,
              transition: 'background 0.2s',
            }}
          >
            {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            {muted ? 'Unmute' : 'Mute'}
          </button>

          <button
            onClick={onDismiss}
            title="Dismiss alert"
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 8,
              background: 'rgba(255,255,255,0.08)',
              border: '1px solid rgba(255,255,255,0.15)',
              color: 'rgba(255,255,255,0.7)', cursor: 'pointer',
              fontSize: 11, fontWeight: 600,
              transition: 'background 0.2s',
            }}
          >
            <X size={13} />
            Dismiss
          </button>
        </div>
      </div>

      <style>{`
        @keyframes critical-edge-pulse {
          0%, 100% { box-shadow: inset 0 0 60px rgba(248,81,73,0.2); }
          50%       { box-shadow: inset 0 0 120px rgba(248,81,73,0.5); }
        }
        @keyframes banner-slide-down {
          from { transform: translateY(-100%); opacity: 0; }
          to   { transform: translateY(0);     opacity: 1; }
        }
        @keyframes siren-icon-flash {
          from { background: rgba(248,81,73,0.1); box-shadow: 0 0 0 0 rgba(248,81,73,0); }
          to   { background: rgba(248,81,73,0.4); box-shadow: 0 0 16px 4px rgba(248,81,73,0.4); }
        }
      `}</style>
    </>
  )
}
