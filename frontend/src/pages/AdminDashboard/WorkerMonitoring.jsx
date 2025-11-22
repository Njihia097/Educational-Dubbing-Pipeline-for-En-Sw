// frontend/src/pages/AdminDashboard/WorkerMonitoring.jsx
import { useEffect, useState } from 'react'
import useAuth from '../../hooks/useAuth'
import WorkerList from '../../components/Admin/WorkerList'
import QueueStatus from '../../components/Admin/QueueStatus'
import ExternalAIStatus from '../../components/Admin/ExternalAIStatus'

export default function WorkerMonitoring() {
  const { user } = useAuth()
  const [workers, setWorkers] = useState(null)
  const [queue, setQueue] = useState(null)
  const [externalAI, setExternalAI] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  async function fetchMonitoring() {
    if (!isAdmin) return

    try {
      setError('')

      // Fetch workers
      const workersRes = await fetch('/api/admin/monitoring/workers', {
        credentials: 'include',
      })
      if (workersRes.ok) {
        const workersData = await workersRes.json()
        setWorkers(workersData.workers || [])
      }

      // Fetch queue status
      const queueRes = await fetch('/api/admin/monitoring/queue', {
        credentials: 'include',
      })
      if (queueRes.ok) {
        const queueData = await queueRes.json()
        setQueue(queueData)
      }

      // Fetch external AI status
      const aiRes = await fetch('/api/admin/monitoring/external-ai', {
        credentials: 'include',
      })
      if (aiRes.ok) {
        const aiData = await aiRes.json()
        setExternalAI(aiData)
      }

      setLoading(false)
    } catch (err) {
      console.error('Error fetching monitoring data:', err)
      setError(err.message || 'Failed to load monitoring data')
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false)
      setError('Admin privileges required')
      return
    }

    fetchMonitoring()

    // Auto-refresh every 5 seconds (more frequent for real-time feel)
    const interval = setInterval(() => {
      fetchMonitoring()
    }, 5000)

    // Pause when tab is inactive
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchMonitoring()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isAdmin])

  if (!isAdmin) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        Admin privileges required to view this page.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Worker & Queue Monitoring</h2>
          <p className="text-xs text-slate-500 mt-1">
            Real-time Celery worker health, Redis queue status, and external AI connectivity.
            Auto-refreshes every 5 seconds.
          </p>
        </div>
        <button
          onClick={fetchMonitoring}
          className="text-xs px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Workers and Queue Status */}
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <WorkerList workers={workers} loading={loading} />
        </div>
        <div className="space-y-4">
          <QueueStatus queue={queue} loading={loading} />
          <ExternalAIStatus status={externalAI} loading={loading} />
        </div>
      </div>
    </div>
  )
}

