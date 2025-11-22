// frontend/src/components/Admin/JobsByStateChart.jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function JobsByStateChart({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        No data available
      </div>
    )
  }

  const chartData = [
    { name: 'Queued', value: data.queued || 0 },
    { name: 'Running', value: data.running || 0 },
    { name: 'Succeeded', value: data.succeeded || 0 },
    { name: 'Failed', value: data.failed || 0 },
    { name: 'Cancelled', value: data.cancelled || 0 },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill="#0ea5e9" />
      </BarChart>
    </ResponsiveContainer>
  )
}

