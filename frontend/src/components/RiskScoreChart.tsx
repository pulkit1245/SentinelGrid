import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { Zone } from '../types'

interface Props { zones: Zone[] }

function riskFill(score: number): string {
  if (score >= 80) return '#f85149'
  if (score >= 60) return '#e85d04'
  if (score >= 40) return '#d29922'
  return '#3fb950'
}

export function RiskScoreChart({ zones }: Props) {
  const data = zones.map(z => ({
    name: z.name.replace('Zone 0', 'Z').split('—')[0].trim(),
    score: z.current_risk_score,
  }))

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
          axisLine={false} tickLine={false}
        />
        <YAxis domain={[0, 100]} tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12, color: 'var(--color-text-primary)' }}
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
        />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => <Cell key={i} fill={riskFill(entry.score)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
