// frontend/src/pages/JobDetail.jsx
import { useEffect, useMemo, useState, useCallback } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import useJobStatus from '../hooks/useJobStatus'
import PipelineTracker from '../components/PipelineTracker'
import TranscriptViewer from '../components/TranscriptViewer'
import VideoPlayer from '../components/VideoPlayer'

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
  const navigate = useNavigate()
  const { job, loading, error, refresh } = useJobStatus(jobId)

  const [originalUrl, setOriginalUrl] = useState(null)
  const [dubbedUrl, setDubbedUrl] = useState(null)
  const [urlError, setUrlError] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)
  const [retrying, setRetrying] = useState(false)

  // Transcripts state
  const [transcripts, setTranscripts] = useState({
    english: '',
    swahili: '',
    englishSegments: [],
    swahiliSegments: [],
  })
  const [transcriptsLoading, setTranscriptsLoading] = useState(false)

  // Video playback state
  const [currentTime, setCurrentTime] = useState(0)
  const [hideOriginal, setHideOriginal] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)

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
  // Fetch presigned URLs (original + dubbed)
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
            `/api/jobs/presign?bucket=${encodeURIComponent(
              parsedIn.bucket
            )}&object=${encodeURIComponent(parsedIn.object)}`,
            { credentials: 'include' }
          )
          const d = await r.json()
          if (!r.ok) throw new Error(d.error || 'Failed to presign original')
          original = d.url
        }

        let dubbed = null
        const parsedOut = parseS3Uri(outputUri)

        if (parsedOut) {
          const r = await fetch(
            `/api/jobs/presign?bucket=${encodeURIComponent(
              parsedOut.bucket
            )}&object=${encodeURIComponent(parsedOut.object)}`,
            { credentials: 'include' }
          )
          const d = await r.json()
          if (!r.ok) throw new Error(d.error || 'Failed to presign dubbed')
          dubbed = d.url
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

  // Fetch transcripts once job is completed
  useEffect(() => {
    // Check for both 'succeeded' and 'completed' states
    const isCompleted = job?.state === 'succeeded' || job?.state === 'completed'
    if (!job || !isCompleted || transcriptsLoading) return
    if (transcripts.englishSegments.length > 0) return // Already loaded

    async function fetchTranscripts() {
      try {
        setTranscriptsLoading(true)
        const res = await fetch(`/api/jobs/${job.id}/transcripts`, {
          credentials: 'include',
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Failed to fetch transcripts')

        setTranscripts({
          english: data.english || '',
          swahili: data.swahili || '',
          englishSegments: data.english_segments || [],
          swahiliSegments: data.swahili_segments || [],
        })
      } catch (err) {
        console.error('Failed to fetch transcripts', err)
      } finally {
        setTranscriptsLoading(false)
      }
    }

    fetchTranscripts()
  }, [job, transcriptsLoading, transcripts.englishSegments.length])

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
    <div className="min-h-screen bg-slate-50">
      {/* Header with back button */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard/jobs')}
              className="text-slate-600 hover:text-slate-900"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">
                Job Details
              </h1>
              <p className="text-xs text-slate-500">Job ID: {job?.id || jobId}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={refresh}
              className="text-xs px-3 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Original Video - At the top */}
          {originalUrl && (
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">
                Original Video
              </h2>
              <video
                src={originalUrl}
                controls
                className="w-full rounded-lg shadow bg-black"
              />
            </div>
          )}

          {/* STATE BADGE */}
          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border border-slate-200 shadow-sm bg-white gap-2">
            <span className={`px-2 py-0.5 rounded-full ${stateBadgeClass}`}>
              {job.state}
            </span>

            {/* Retry count badge */}
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

          {/* FULL CHAIN PIPELINE TRACKER */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-900">
                Pipeline Status
              </h2>
              {urlLoading && (
                <span className="text-[11px] text-slate-400">
                  Preparing video URLs…
                </span>
              )}
            </div>

            <PipelineTracker
              job={job}
              loading={loading}
              error={error}
              onRetry={handleRetry}
            />
          </div>

          {/* URL error */}
          {urlError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {urlError}
            </div>
          )}

          {/* Maestra-style Layout: Transcripts + Dubbed Video */}
          {(job?.state === 'succeeded' || job?.state === 'completed') && dubbedUrl ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ height: 'calc(100vh - 450px)' }}>
              {/* Left Panel: Transcript Viewer */}
              <div className="lg:col-span-1 border border-slate-200 rounded-lg overflow-hidden bg-white flex flex-col" style={{ height: '100%' }}>
                <TranscriptViewer
                  englishSegments={transcripts.englishSegments}
                  swahiliSegments={transcripts.swahiliSegments}
                  currentTime={currentTime}
                  onSegmentClick={(time) => setCurrentTime(time)}
                  hideOriginal={hideOriginal}
                  autoScroll={autoScroll}
                  onHideOriginalChange={setHideOriginal}
                  onAutoScrollChange={setAutoScroll}
                />
              </div>

              {/* Right Panel: Dubbed Video Player */}
              <div className="lg:col-span-2 flex flex-col" style={{ height: '100%' }}>
                <div className="bg-white border border-slate-200 rounded-lg p-4 h-full flex flex-col">
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-slate-900 mb-2">
                      Dubbed Video
                    </h3>
                    <p className="text-xs text-slate-600">
                      AI-generated Swahili voiceover synchronized with the original video timeline.
                    </p>
                  </div>

                  {urlError && (
                    <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                      {urlError}
                    </div>
                  )}

                  <div className="flex-1 flex flex-col min-h-0">
                    <VideoPlayer
                      videoUrl={dubbedUrl}
                      currentTime={currentTime}
                      onTimeUpdate={setCurrentTime}
                      onSeek={setCurrentTime}
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Processing or No Output State */
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
              {urlLoading || loading ? (
                <div className="space-y-3">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto" />
                  <p className="text-sm text-slate-500">
                    Preparing video URLs…
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-slate-600">
                    {job?.state === 'completed' || job?.state === 'succeeded'
                      ? 'Loading dubbed video...'
                      : job?.state === 'failed'
                      ? 'Pipeline failed — no output generated.'
                      : 'Dubbed output will appear here once the pipeline finishes.'}
                  </p>
                  <p className="text-xs text-slate-500">
                    Current state:{' '}
                    <span className="font-medium">{job?.state || '—'}</span>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
