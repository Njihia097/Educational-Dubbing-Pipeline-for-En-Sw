// frontend/src/components/StatusBadge.jsx

export default function StatusBadge({ state }) {
  const s = (state || '').toLowerCase()

  let classes =
    'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium'
  let label = state || 'unknown'

  switch (s) {
    case 'running':
      classes += ' bg-sky-100 text-sky-800 border border-sky-200'
      break
    case 'queued':
    case 'pending':
      classes += ' bg-amber-50 text-amber-800 border border-amber-200'
      break
    case 'completed':
    case 'succeeded':
      classes += ' bg-emerald-50 text-emerald-800 border border-emerald-200'
      break
    case 'failed':
    case 'error':
      classes += ' bg-rose-50 text-rose-800 border border-rose-200'
      break
    case 'cancelled':
      classes += ' bg-slate-100 text-slate-700 border border-slate-200'
      break
    default:
      classes += ' bg-slate-100 text-slate-700 border border-slate-200'
      break
  }

  return (
    <span className={classes}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {label}
    </span>
  )
}
