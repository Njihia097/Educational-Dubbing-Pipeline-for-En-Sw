// frontend/src/components/Admin/ExternalAIStatus.jsx

function getStatusBadgeClass(status) {
  switch (status) {
    case 'online':
      return 'bg-emerald-100 text-emerald-800'
    case 'offline':
      return 'bg-red-100 text-red-800'
    case 'timeout':
      return 'bg-amber-100 text-amber-800'
    case 'error':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

export default function ExternalAIStatus({ status, loading }) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Checking external AI status...</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">External AI status unavailable</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">External AI Service</h3>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-600">Status</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${getStatusBadgeClass(status.status)}`}>
            {status.status}
          </span>
        </div>

        {status.response_time_ms !== null && status.response_time_ms !== undefined && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-600">Response Time</span>
            <span className="text-xs font-semibold text-slate-900">
              {status.response_time_ms.toFixed(2)} ms
            </span>
          </div>
        )}

        {status.health_data && (
          <div className="pt-2 border-t border-slate-200 space-y-1">
            <p className="text-[10px] font-medium text-slate-600">Health Info</p>
            {status.health_data.device && (
              <p className="text-[10px] text-slate-500">Device: {status.health_data.device}</p>
            )}
            {status.health_data.whisper_model && (
              <p className="text-[10px] text-slate-500">Model: {status.health_data.whisper_model}</p>
            )}
          </div>
        )}

        {status.error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            {status.error}
          </div>
        )}

        {status.url && (
          <div className="pt-2 border-t border-slate-200">
            <p className="text-[10px] text-slate-500 break-all">{status.url}</p>
          </div>
        )}
      </div>
    </div>
  )
}

