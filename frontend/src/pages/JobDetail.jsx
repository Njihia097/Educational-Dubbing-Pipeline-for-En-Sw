// frontend/src/pages/JobDetail.jsx
import { useEffect, useMemo, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import useJobStatus from '../hooks/useJobStatus'
import PipelineTracker from '../components/PipelineTracker'

function parseS3Uri(s3Uri) {
  if (!s3Uri || !s3Uri.startsWith('s3://')) return null
  const withoutScheme = s3Uri.replace('s3://', '')
  const [bucket, ...rest] = withoutScheme.split('/')
  const object = rest.join('/')
  if (!bucket || !object) return null
  return { bucket, object }
}

export default function JobDetail() {
  const { jobId } = useParams()
  const { job, loading, error, refresh } = useJobStatus(jobId)

  const [originalUrl, setOriginalUrl] = useState(null)
  const [dubbedUrl, setDubbedUrl] = useState(null)
  const [urlError, setUrlError] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)
  const [retrying, setRetrying] = useState(false)

  // ------------------------------------------
  // Retry Workflow
  // ------------------------------------------
  const handleRetry = useCallback(async () => {
    if (!jobId) return
    setRetrying(true)
    setUrlError('')
    setDubbedUrl(null)

    try {
      const res = await fetch(`/api/jobs/${jobId}/retry`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Retry failed')

      // Refresh status immediately
      refresh()
      // Trigger URL re-fetch when pipeline restarts
      setOriginalUrl(null)
      setDubbedUrl(null)
      setUrlError('')

    } catch (err) {
      console.error('Retry failed', err)
      setUrlError(err.message)
    } finally {
      setRetrying(false)
    }
  }, [jobId, refresh])


  // ------------------------------------------
  // State badge styles
  // ------------------------------------------
  const stateBadgeClass = useMemo(() => {
    if (!job) return 'bg-slate-100 text-slate-700'
    switch (job.state) {
      case 'running':
        return 'bg-sky-100 text-sky-800'
      case 'queued':
        return 'bg-amber-50 text-amber-800'
      case 'completed':
      case 'succeeded':
        return 'bg-emerald-50 text-emerald-800'
      case 'failed':
        return 'bg-rose-50 text-rose-800'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }, [job])

  // ------------------------------------------
  // Fetch presigned URLs
  // ------------------------------------------
  useEffect(() => {
    if (!job || loading) return

    const inputUri = job.input_s3_uri
    const outputUri = job.output_s3_uri || job.meta?.output_s3_uri

    async function fetchUrls() {
      setUrlError('')
      setUrlLoading(true)

      try {
        let original = null
        const parsedIn = parseS3Uri(inputUri)

        if (parsedIn) {
          const r = await fetch(
            `/api/jobs/presign?bucket=${encodeURIComponent(parsedIn.bucket)}&object=${encodeURIComponent(parsedIn.object)}`,
            { credentials: 'include' }
          )
          const d = await r.json()
          if (!r.ok) throw new Error(d.error || 'Failed to presign original')
          original = { url: d.url, jobId: job.id }
        }

        let dubbed = null
        const parsedOut = parseS3Uri(outputUri)

        if (parsedOut) {
          const r = await fetch(
            `/api/jobs/presign?bucket=${encodeURIComponent(parsedOut.bucket)}&object=${encodeURIComponent(parsedOut.object)}`,
            { credentials: 'include' }
          )
          const d = await r.json()
          if (!r.ok) throw new Error(d.error || 'Failed to presign dubbed')
          dubbed = { url: d.url, jobId: job.id }
        }

        setOriginalUrl(original)
        setDubbedUrl(dubbed)
      } catch (err) {
        console.error(err)
        setUrlError(err.message)
      } finally {
        setUrlLoading(false)
      }
    }

    fetchUrls()
  }, [job, loading])

  // -----------------------
  // Loading / error states
  // -----------------------
  if (loading && !job) return <div>Loading…</div>
  if (error) return <div>Failed: {error}</div>
  if (!job) return <div>No job found.</div>

  // -----------------------
  // RENDER
  // -----------------------
  return (
    <div className="min-h-screen px-4 py-6 bg-slate-50">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Debug logs */}
        {console.log('Presigned original:', originalUrl?.url)}
        {console.log('Presigned dubbed:', dubbedUrl?.url)}

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-800">Job Details</h1>
            <p className="text-xs text-slate-500">Job ID: {job.id}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={refresh}
              className="text-xs px-3 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
            >
              Refresh
            </button>

            <Link
              to="/jobs"
              className="text-sm text-sky-600 hover:underline underline-offset-2"
            >
              ← Back to jobs
            </Link>
          </div>
        </div>

        {/* STATE BADGE */}
        <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border border-slate-200 shadow-sm bg-white gap-2">
          <span className={`px-2 py-0.5 rounded-full ${stateBadgeClass}`}>
            {job.state}
          </span>

          {/* Retry badge */}
          {job.retry_count > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              retries: {job.retry_count}
            </span>
          )}
        </div>

        {/* ERROR MESSAGE */}
        {job.last_error_message && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {job.last_error_message}
          </div>
        )}

        {/* RETRY BUTTON */}
        {job.state === 'failed' && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 disabled:opacity-60"
          >
            {retrying ? 'Retrying…' : 'Retry Job'}
          </button>
        )}

        {/* PIPELINE TRACKER */}
        <PipelineTracker job={job} loading={loading} error={error} onRetry={handleRetry} />

        {/* URL error */}
        {urlError && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {urlError}
          </div>
        )}

        {/* VIDEO VIEW ---- ORIGINAL & DUBBED */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Original */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-slate-700">Original Video</h2>

            {!originalUrl && (
              <p className="text-xs text-slate-500">Waiting for original video…</p>
            )}

            {originalUrl && (
              <video
                src={originalUrl.url}
                controls
                className="w-full rounded-lg shadow bg-black"
              />
            )}
          </div>

          {/* Dubbed */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-slate-700">Dubbed Output</h2>

            {!dubbedUrl && (
              <p className="text-xs text-slate-500">
                {job.state === 'failed'
                  ? 'Pipeline failed — no output generated.'
                  : 'Output not ready yet…'}
              </p>
            )}

            {dubbedUrl && (
              <video
                src={dubbedUrl.url}
                controls
                className="w-full rounded-lg shadow bg-black"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
