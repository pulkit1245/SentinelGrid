import React from 'react'
import type { SensorStats } from '../../hooks/useSensorMap'
import { Activity, Wifi, WifiOff, AlertTriangle, Zap, BarChart2, MapPin } from 'lucide-react'

interface DashboardStatsPanelProps {
  stats: SensorStats
  wsConnected: boolean
}

interface StatBadgeProps {
  icon: React.ReactNode
  label: string
  value: number | string
  color: string
  pulse?: boolean
}

function StatBadge({ icon, label, value, color, pulse }: StatBadgeProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '10px 14px',
      background: 'var(--color-surface)',
      border: `1px solid ${color}30`,
      borderRadius: 10,
      backdropFilter: 'blur(8px)',
      animation: pulse ? 'pulse-critical 2s infinite' : undefined,
    }}>
      <div style={{ color, opacity: 0.9 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 18, fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 10, color: 'var(--color-text-secondary)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      </div>
    </div>
  )
}

export function DashboardStatsPanel({ stats, wsConnected }: DashboardStatsPanelProps) {
  return (
    <div style={{
      display: 'flex',
      gap: 10,
      flexWrap: 'wrap',
      alignItems: 'center',
      padding: '12px 16px',
      background: 'var(--color-surface)',
      borderBottom: '1px solid var(--color-border)',
      backdropFilter: 'blur(12px)',
    }}>
      <StatBadge icon={<Activity size={16} />}      label="Total Sensors"  value={stats.total}        color="#58a6ff" />
      <StatBadge icon={<Wifi size={16} />}          label="Online"         value={stats.online}       color="#3fb950" />
      <StatBadge icon={<WifiOff size={16} />}       label="Offline"        value={stats.offline}      color="var(--color-text-muted)" />
      <StatBadge icon={<AlertTriangle size={16} />} label="Warning"        value={stats.warning}      color="#d29922" />
      <StatBadge icon={<Zap size={16} />}           label="Critical"       value={stats.critical}     color="#f85149" pulse={stats.critical > 0} />
      <StatBadge icon={<BarChart2 size={16} />}     label="Active Zones"   value={stats.active_zones} color="#6e5ee0" />

      <div style={{
        marginLeft: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: 4,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-text-secondary)' }}>
          <MapPin size={12} />
          <span>Highest Risk: <strong style={{ color: '#e85d04' }}>{stats.highest_risk_zone}</strong></span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--color-text-muted)' }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: wsConnected ? '#3fb950' : 'var(--color-text-muted)',
            display: 'inline-block',
          }} />
          {wsConnected ? 'Live Feed Active' : 'Connecting...'}
        </div>
      </div>
    </div>
  )
}
