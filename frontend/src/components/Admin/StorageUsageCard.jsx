// frontend/src/components/Admin/StorageUsageCard.jsx

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

export default function StorageUsageCard({ storage }) {
  if (!storage) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Storage Usage</h3>
        <p className="text-xs text-slate-500">Loading...</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">Storage Usage</h3>
      
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-600">Uploads</span>
            <span className="text-xs font-medium text-slate-900">
              {formatBytes(storage.uploads?.size_bytes)}
            </span>
          </div>
          <p className="text-[10px] text-slate-500">
            {storage.uploads?.object_count || 0} objects
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-600">Outputs</span>
            <span className="text-xs font-medium text-slate-900">
              {formatBytes(storage.outputs?.size_bytes)}
            </span>
          </div>
          <p className="text-[10px] text-slate-500">
            {storage.outputs?.object_count || 0} objects
          </p>
        </div>

        <div className="pt-2 border-t border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700">Total</span>
            <span className="text-sm font-semibold text-slate-900">
              {formatBytes(storage.total?.size_bytes)}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">
            {storage.total?.object_count || 0} total objects
          </p>
        </div>
      </div>
    </div>
  )
}

