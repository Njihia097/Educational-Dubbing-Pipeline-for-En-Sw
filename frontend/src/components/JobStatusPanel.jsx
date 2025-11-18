// frontend/src/components/JobStatusPanel.jsx
import useJobStatus from '../hooks/useJobStatus'
import PipelineTracker from './PipelineTracker'

export default function JobStatusPanel({ jobId }) {
  const { job, loading, error } = useJobStatus(jobId, { pollIntervalMs: 2500 })

  const handleRetry = async () => {
    if (!jobId) return

    await fetch(`/api/jobs/${jobId}/retry`, {
      method: 'POST',
      credentials: 'include',
    })

    // force refresh
    window.location.reload()
  }

  if (!jobId) return null

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-900">Pipeline status</h3>
        <span className="text-xs font-mono text-slate-500">
          Job: {jobId.slice(0, 8)}…
        </span>
      </div>

      <PipelineTracker
        job={job}
        loading={loading}
        error={error}
        onRetry={handleRetry}   
      />
    </div>
  )
}
