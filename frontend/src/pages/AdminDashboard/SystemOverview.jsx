// frontend/src/pages/AdminDashboard/SystemOverview.jsx
import { useEffect, useState } from 'react'
import useAuth from '../../hooks/useAuth'
import MetricCard from '../../components/Admin/MetricCard'
import JobsByStateChart from '../../components/Admin/JobsByStateChart'
import JobsTimelineChart from '../../components/Admin/JobsTimelineChart'
import StorageUsageCard from '../../components/Admin/StorageUsageCard'

export default function SystemOverview() {
  const { user } = useAuth()
  const [metrics, setMetrics] = useState(null)
  const [storage, setStorage] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  async function fetchMetrics() {
    if (!isAdmin) return

    try {
      setError('')

      // Fetch overview metrics
      const metricsRes = await fetch('/api/admin/metrics/overview', {
        credentials: 'include',
      })
      if (metricsRes.ok) {
        const metricsData = await metricsRes.json()
        setMetrics(metricsData)
      } else {
        const errorData = await metricsRes.json().catch(() => ({ error: 'Failed to fetch metrics' }))
        throw new Error(errorData.error || `HTTP ${metricsRes.status}`)
      }

      // Fetch storage metrics
      const storageRes = await fetch('/api/admin/metrics/storage', {
        credentials: 'include',
      })
      if (storageRes.ok) {
        const storageData = await storageRes.json()
        setStorage(storageData)
      } else {
        // Storage errors are non-critical, just log
        console.warn('Failed to fetch storage metrics:', storageRes.status)
      }

      // Fetch timeline
      const timelineRes = await fetch('/api/admin/metrics/jobs-timeline?days=7', {
        credentials: 'include',
      })
      if (timelineRes.ok) {
        const timelineData = await timelineRes.json()
        setTimeline(timelineData.timeline || [])
      } else {
        // Timeline errors are non-critical, just log
        console.warn('Failed to fetch timeline:', timelineRes.status)
      }

      setLoading(false)
    } catch (err) {
      console.error('Error fetching metrics:', err)
      setError(err.message || 'Failed to load metrics')
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false)
      setError('Admin privileges required')
      return
    }

    fetchMetrics()

    // Auto-refresh every 15 seconds
    const interval = setInterval(() => {
      fetchMetrics()
    }, 15000)

    // Pause when tab is inactive
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchMetrics()
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

  const formatTime = (seconds) => {
    if (!seconds) return '—'
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
    return `${(seconds / 3600).toFixed(1)}h`
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-slate-900">System Overview</h2>
        <p className="text-xs text-slate-500 mt-1">
          Real-time system metrics and statistics. Auto-refreshes every 15 seconds.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && !metrics ? (
        <div className="text-sm text-slate-500">Loading metrics...</div>
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Total Jobs"
              value={metrics?.total_jobs || 0}
            />
            <MetricCard
              title="Active Tasks"
              value={metrics?.active_tasks || 0}
              subtitle="Queued + Running"
            />
            <MetricCard
              title="Avg Processing Time"
              value={metrics?.avg_processing_time_seconds ? formatTime(metrics.avg_processing_time_seconds) : '—'}
            />
            <MetricCard
              title="Succeeded Jobs"
              value={metrics?.jobs_by_state?.succeeded || 0}
            />
          </div>

          {/* Charts Row */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Jobs by State</h3>
              <JobsByStateChart data={metrics?.jobs_by_state} />
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Job Creation Timeline (Last 7 Days)</h3>
              <JobsTimelineChart data={timeline} />
            </div>
          </div>

          {/* Storage Usage */}
          <div className="grid gap-4 md:grid-cols-3">
            <StorageUsageCard storage={storage} />
          </div>
        </>
      )}
    </div>
  )
}

