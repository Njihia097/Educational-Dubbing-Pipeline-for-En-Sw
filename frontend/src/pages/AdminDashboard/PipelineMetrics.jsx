// frontend/src/pages/AdminDashboard/PipelineMetrics.jsx
import { useEffect, useState } from 'react'
import useAuth from '../../hooks/useAuth'
import MetricCard from '../../components/Admin/MetricCard'
import PipelineStepPerformance from '../../components/Admin/PipelineStepPerformance'
import TextAnalyticsCard from '../../components/Admin/TextAnalyticsCard'
import ProcessingVolumeCard from '../../components/Admin/ProcessingVolumeCard'
import StepDurationChart from '../../components/Admin/StepDurationChart'
import TranslationRatioChart from '../../components/Admin/TranslationRatioChart'

export default function PipelineMetrics() {
  const { user } = useAuth()
  const [pipelineMetrics, setPipelineMetrics] = useState(null)
  const [stepMetrics, setStepMetrics] = useState(null)
  const [textAnalytics, setTextAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  async function fetchMetrics() {
    if (!isAdmin) return

    try {
      setError('')

      // Fetch aggregated pipeline metrics
      const pipelineRes = await fetch('/api/admin/metrics/pipeline', {
        credentials: 'include',
      })
      if (pipelineRes.ok) {
        const pipelineData = await pipelineRes.json()
        console.log('[PipelineMetrics] Pipeline data:', pipelineData)
        setPipelineMetrics(pipelineData)
      } else {
        const errorData = await pipelineRes.json().catch(() => ({ error: 'Failed to fetch pipeline metrics' }))
        console.error('[PipelineMetrics] Pipeline metrics error:', errorData)
        // Don't throw - allow other metrics to load
        setPipelineMetrics({ text_analytics: {}, step_durations: {} })
      }

      // Fetch step metrics
      const stepsRes = await fetch('/api/admin/metrics/pipeline/steps', {
        credentials: 'include',
      })
      if (stepsRes.ok) {
        const stepsData = await stepsRes.json()
        console.log('[PipelineMetrics] Step data:', stepsData)
        setStepMetrics(stepsData.steps || {})
      } else {
        console.warn('[PipelineMetrics] Failed to fetch step metrics:', stepsRes.status)
        setStepMetrics({})
      }

      // Fetch text analytics
      const analyticsRes = await fetch('/api/admin/metrics/pipeline/text-analytics', {
        credentials: 'include',
      })
      if (analyticsRes.ok) {
        const analyticsData = await analyticsRes.json()
        console.log('[PipelineMetrics] Text analytics data:', analyticsData)
        setTextAnalytics(analyticsData)
      } else {
        console.warn('[PipelineMetrics] Failed to fetch text analytics:', analyticsRes.status)
        setTextAnalytics(null)
      }

      setLoading(false)
    } catch (err) {
      console.error('Error fetching pipeline metrics:', err)
      setError(err.message || 'Failed to load pipeline metrics')
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

  // Find bottleneck (slowest step)
  const bottleneck = pipelineMetrics?.step_durations
    ? Object.entries(pipelineMetrics.step_durations)
        .sort((a, b) => (b[1].avg || 0) - (a[1].avg || 0))[0]
    : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Pipeline Metrics</h2>
        <p className="text-xs text-slate-500 mt-1">
          ML/NLP pipeline performance, text analytics, and processing statistics. Auto-refreshes every 15 seconds.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && !pipelineMetrics && !stepMetrics ? (
        <div className="text-sm text-slate-500">Loading pipeline metrics...</div>
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Total Videos Processed"
              value={pipelineMetrics?.text_analytics?.total_videos_processed || 0}
            />
            <MetricCard
              title="Total Words Processed"
              value={pipelineMetrics?.text_analytics?.total_english_words ? pipelineMetrics.text_analytics.total_english_words.toLocaleString() : 0}
              subtitle="English words"
            />
            <MetricCard
              title="Avg Words per Video"
              value={pipelineMetrics?.text_analytics?.avg_words_per_video ? pipelineMetrics.text_analytics.avg_words_per_video.toFixed(0) : '—'}
            />
            <MetricCard
              title="Translation Ratio"
              value={pipelineMetrics?.text_analytics?.avg_translation_ratio ? pipelineMetrics.text_analytics.avg_translation_ratio.toFixed(2) : '—'}
              subtitle={bottleneck ? `Slowest: ${bottleneck[0]}` : 'Swahili/English'}
            />
          </div>

          {/* Charts Row */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Step Performance</h3>
              <PipelineStepPerformance stepStats={stepMetrics} />
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Step Durations</h3>
              <StepDurationChart stepDurations={pipelineMetrics?.step_durations} />
            </div>
          </div>

          {/* Translation Ratio Chart */}
          {textAnalytics?.translation_ratio && (
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Translation Ratio Statistics</h3>
              <TranslationRatioChart translationRatios={textAnalytics.translation_ratio} />
            </div>
          )}

          {/* Analytics Cards */}
          <div className="grid gap-4 md:grid-cols-2">
            <TextAnalyticsCard analytics={textAnalytics} />
            <ProcessingVolumeCard metrics={pipelineMetrics} />
          </div>
        </>
      )}
    </div>
  )
}

