// frontend/src/components/Admin/PipelineStepPerformance.jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function PipelineStepPerformance({ stepStats }) {
  if (!stepStats || Object.keys(stepStats).length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        No step performance data available
      </div>
    )
  }

  const chartData = Object.entries(stepStats).map(([step, stats]) => ({
    step: step.charAt(0).toUpperCase() + step.slice(1),
    avgDuration: stats.avg_duration_seconds || 0,
    successRate: stats.success_rate || 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="step" />
        <YAxis yAxisId="left" label={{ value: 'Duration (s)', angle: -90, position: 'insideLeft' }} />
        <YAxis yAxisId="right" orientation="right" label={{ value: 'Success Rate (%)', angle: 90, position: 'insideRight' }} />
        <Tooltip />
        <Legend />
        <Bar yAxisId="left" dataKey="avgDuration" fill="#0ea5e9" name="Avg Duration (s)" />
        <Bar yAxisId="right" dataKey="successRate" fill="#10b981" name="Success Rate (%)" />
      </BarChart>
    </ResponsiveContainer>
  )
}

