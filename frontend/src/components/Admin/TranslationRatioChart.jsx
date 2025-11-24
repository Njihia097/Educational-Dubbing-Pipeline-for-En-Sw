// frontend/src/components/Admin/TranslationRatioChart.jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export default function TranslationRatioChart({ translationRatios }) {
  if (!translationRatios || translationRatios.avg === undefined) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        No translation ratio data available
      </div>
    )
  }

  // Create a bar chart showing min, avg, max ratios
  const chartData = [
    {
      metric: 'Min',
      ratio: translationRatios.min || 0,
    },
    {
      metric: 'Average',
      ratio: translationRatios.avg || 0,
    },
    {
      metric: 'Max',
      ratio: translationRatios.max || 0,
    },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="metric" />
        <YAxis label={{ value: 'Ratio (Swahili/English)', angle: -90, position: 'insideLeft' }} />
        <Tooltip formatter={(value) => value.toFixed(3)} />
        <ReferenceLine y={1.0} stroke="#ef4444" strokeDasharray="3 3" label="1.0 (Equal)" />
        <Bar dataKey="ratio" fill="#0ea5e9" name="Translation Ratio" />
      </BarChart>
    </ResponsiveContainer>
  )
}

