import { useEffect, useState } from 'react'
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '../services/api'

interface Props {
  sensorId: string
  color?: string
}

export function SensorSparkline({ sensorId, color = 'var(--color-accent)' }: Props) {
  const [data, setData] = useState<Array<{ v: number }>>([])

  useEffect(() => {
    api.getSensorReadings(sensorId, 30)
      .then(readings => setData(readings.slice().reverse().map(r => ({ v: r.reading_value }))))
      .catch(() => {})
  }, [sensorId])

  if (data.length === 0) return <div className="skeleton" style={{ height: 40, borderRadius: 4 }} />

  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="v" stroke={color} dot={false} strokeWidth={1.5} />
        <Tooltip
          contentStyle={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 6, fontSize: 11 }}
          formatter={(v: number) => [v.toFixed(2), 'value']}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
