// frontend/src/components/Admin/QueueStatus.jsx

export default function QueueStatus({ queue, loading }) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Loading queue status...</p>
      </div>
    )
  }

  if (!queue) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Queue status unavailable</p>
      </div>
    )
  }

  const hasError = queue.error !== undefined

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">Redis Queue Status</h3>
      
      {hasError ? (
        <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          Error: {queue.error}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-600">Queue Name</span>
            <span className="text-xs font-mono text-slate-900">{queue.queue_name || 'default'}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-600">Pending Tasks</span>
            <span className="text-xs font-semibold text-slate-900">
              {queue.pending_tasks !== null ? queue.pending_tasks : '—'}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-600">Reserved Tasks</span>
            <span className="text-xs font-semibold text-slate-900">
              {queue.reserved_tasks !== null ? queue.reserved_tasks : '—'}
            </span>
          </div>
          
          <div className="pt-2 border-t border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700">Total Tasks</span>
              <span className="text-sm font-semibold text-slate-900">
                {queue.total_tasks !== null ? queue.total_tasks : '—'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

