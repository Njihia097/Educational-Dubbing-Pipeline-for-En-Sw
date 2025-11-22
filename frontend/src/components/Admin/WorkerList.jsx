// frontend/src/components/Admin/WorkerList.jsx

function getStatusBadgeClass(status) {
  switch (status) {
    case 'online':
      return 'bg-emerald-100 text-emerald-800'
    case 'offline':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

export default function WorkerList({ workers, loading }) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">Loading workers...</p>
      </div>
    )
  }

  if (!workers || workers.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">No workers detected</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-900">Celery Workers</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Worker Name</th>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Status</th>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Active Tasks</th>
            </tr>
          </thead>
          <tbody>
            {workers.map((worker, idx) => (
              <tr key={idx} className="border-b border-slate-100">
                <td className="px-4 py-2 font-mono text-[11px] text-slate-700">
                  {worker.name}
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${getStatusBadgeClass(worker.status)}`}>
                    {worker.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-700">
                  {worker.active_tasks || 0}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

