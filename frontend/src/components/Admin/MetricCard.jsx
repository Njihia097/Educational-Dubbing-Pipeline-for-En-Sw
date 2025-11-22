// frontend/src/components/Admin/MetricCard.jsx
export default function MetricCard({ title, value, subtitle, icon }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {value !== null && value !== undefined ? value : '—'}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="ml-4 text-slate-400">{icon}</div>
        )}
      </div>
    </div>
  )
}

