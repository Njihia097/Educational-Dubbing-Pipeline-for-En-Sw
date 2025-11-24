// frontend/src/components/Admin/StepDurationChart.jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function StepDurationChart({ stepDurations }) {
  if (!stepDurations || Object.keys(stepDurations).length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        No step duration data available
      </div>
    )
  }

  const chartData = Object.entries(stepDurations).map(([step, stats]) => ({
    step: step.charAt(0).toUpperCase() + step.slice(1),
    avg: stats.avg || 0,
    min: stats.min || 0,
    max: stats.max || 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="step" />
        <YAxis label={{ value: 'Duration (seconds)', angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Legend />
        <Bar dataKey="avg" fill="#0ea5e9" name="Avg Duration (s)" />
        <Bar dataKey="min" fill="#94a3b8" name="Min Duration (s)" />
        <Bar dataKey="max" fill="#f59e0b" name="Max Duration (s)" />
      </BarChart>
    </ResponsiveContainer>
  )
}

