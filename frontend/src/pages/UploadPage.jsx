// frontend/src/pages/UploadPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import useJobStatus from '../hooks/useJobStatus'
import JobStatusPanel from '../components/JobStatusPanel'
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

export default function UploadPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [file, setFile] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  // Initialize jobInfo from localStorage if available
  const [jobInfo, setJobInfo] = useState(() => {
    const savedJobId = localStorage.getItem('current_job_id')
    return savedJobId ? { job_id: savedJobId } : null
  })
  const [previewUrl, setPreviewUrl] = useState(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  // Job status and video URLs
  const { job, loading: jobLoading } = useJobStatus(jobInfo?.job_id, {
    pollIntervalMs: 2500,
  })
  const [dubbedUrl, setDubbedUrl] = useState(null)
  const [urlError, setUrlError] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)

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

  // Check if job is active (running or queued)
  const isJobActive = job?.state === 'running' || job?.state === 'queued'
  const isJobProcessing = submitting || isJobActive

  // Save job_id to localStorage when job is created
  useEffect(() => {
    if (jobInfo?.job_id) {
      localStorage.setItem('current_job_id', jobInfo.job_id)
    } else {
      // Only clear if jobInfo is explicitly set to null (not on job completion)
      // This allows completed jobs to persist across reloads
      if (jobInfo === null) {
        localStorage.removeItem('current_job_id')
      }
    }
  }, [jobInfo])

  function handleFile(e) {
    // Prevent file change if job is processing
    if (isJobProcessing) {
      e.preventDefault()
      return
    }

    const f = e.target.files?.[0]
    setFile(f)
    setPreviewUrl(f ? URL.createObjectURL(f) : null)

    // Reset previous job state if new file chosen
    setJobInfo(null)
    setDubbedUrl(null)
    setUrlError('')
    setTranscripts({
      english: '',
      swahili: '',
      englishSegments: [],
      swahiliSegments: [],
    })
    setCurrentTime(0)
  }

  async function handleCancel() {
    if (!jobInfo?.job_id) return

    setCancelling(true)
    setUrlError('') // Clear any previous errors
    try {
      const res = await fetch(`/api/jobs/${jobInfo.job_id}/cancel`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to cancel job')

      // Show success message briefly before clearing
      setUrlError('') // Clear errors
      
      // Wait a moment to show the success state
      await new Promise(resolve => setTimeout(resolve, 500))

      // Clear job state completely
      setJobInfo(null)
      setDubbedUrl(null)
      setUrlError('')
      setTranscripts({
        english: '',
        swahili: '',
        englishSegments: [],
        swahiliSegments: [],
      })
      setCurrentTime(0)
      setFile(null)
      setPreviewUrl(null)
      setShowCancelConfirm(false)
      
      // Clear from localStorage to stop polling
      localStorage.removeItem('current_job_id')
      
    } catch (err) {
      console.error('Failed to cancel job', err)
      setUrlError(err.message || 'Failed to cancel job')
    } finally {
      setCancelling(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (!user) {
      setError('You must be logged in.')
      return
    }
    if (!file) {
      setError('Please select a video file.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('owner_id', user.id)
    formData.append('project_id', 'auto')

    setSubmitting(true)

    try {
      const res = await fetch('/api/jobs/create', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || 'Failed to create job')
      }

      // Store job info
      setJobInfo({
        job_id: data.job_id,
        task_id: data.task_id,
        uri: data.uri,
      })
      setDubbedUrl(null)
      setUrlError('')
      setTranscripts({
        english: '',
        swahili: '',
        englishSegments: [],
        swahiliSegments: [],
      })

    } catch (err) {
      console.error(err)
      setError(err.message || 'Upload failed')
      setJobInfo(null)
    } finally {
      setSubmitting(false)
    }
  }

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

  // Fetch DUBBED video URL once output_s3_uri becomes available
  useEffect(() => {
    // Check both direct output_s3_uri and meta.output_s3_uri
    const outputUri = job?.output_s3_uri || job?.meta?.output_s3_uri
    
    if (!job) return
    if (!outputUri) {
      // Debug: log when job is completed but no output URI
      if (job.state === 'completed' || job.state === 'succeeded') {
        console.log('[UploadPage] Job completed but no output_s3_uri yet', {
          state: job.state,
          output_s3_uri: job.output_s3_uri,
          meta: job.meta,
        })
      }
      return
    }
    if (dubbedUrl) return

    async function fetchDubbed() {
      console.log('[UploadPage] Fetching presigned URL for:', outputUri)
      try {
        setUrlLoading(true)
        setUrlError('')

        const parsed = parseS3Uri(outputUri)
        if (!parsed) {
          console.warn('Failed to parse output_s3_uri:', outputUri)
          return
        }

        const res = await fetch(
          `/api/jobs/presign?bucket=${encodeURIComponent(
            parsed.bucket,
          )}&object=${encodeURIComponent(parsed.object)}`,
          { credentials: 'include' },
        )
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Failed to presign dubbed video URL')

        setDubbedUrl(data.url)
      } catch (err) {
        console.error('Failed to presign dubbed URL', err)
        setUrlError(err.message || 'Failed to prepare dubbed video URL')
      } finally {
        setUrlLoading(false)
      }
    }

    fetchDubbed()
  }, [job, dubbedUrl])

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header with back button */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
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
            <h1 className="text-lg font-semibold text-slate-900">
              Upload & Dubbing
            </h1>
          </div>
        </div>
      </header>

      {/* Main content - full width */}
      <main className="p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-slate-800 mb-2">
            Upload a Video for Dubbing
          </h2>
          <p className="text-sm text-slate-500">
            The pipeline will run: ASR → Punctuation → Translation → TTS → Mixing → Muxing.
          </p>
        </div>

      {/* Upload Form - Only show if no active job or job is cancelled/failed */}
      {(!jobInfo || job?.state === 'cancelled' || job?.state === 'failed') && (
      <form
        onSubmit={handleSubmit}
        className="space-y-4 bg-white border border-slate-200 rounded-xl p-5 shadow-sm"
      >
        {/* File Input */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Video File
          </label>

          <input
            type="file"
            accept="video/*"
            onChange={handleFile}
            disabled={isJobProcessing}
            className="block w-full text-slate-800 file:mr-3 file:rounded-lg file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700 hover:file:bg-sky-200 disabled:opacity-50 disabled:cursor-not-allowed"
          />

          <p className="mt-1 text-xs text-slate-400">
            Supported formats depend on FFmpeg in backend.
          </p>

          {/* Local preview (immediate feedback) */}
          {previewUrl && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 mb-1">Local preview:</p>
              <video
                src={previewUrl}
                controls
                className="rounded-lg border border-slate-200 w-full bg-black"
                style={{ maxHeight: '60vh' }}
              />
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={isJobProcessing}
            className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Uploading…' : isJobActive ? 'Processing…' : 'Upload & Start Dubbing'}
          </button>
        </div>
      </form>
      )}

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Cancel Dubbing Process?
            </h3>
            <p className="text-sm text-slate-600 mb-6">
              Are you sure you want to cancel the current dubbing process? This action cannot be undone and any progress will be lost.
            </p>
            
            {/* Loading indicator during cancellation */}
            {cancelling && (
              <div className="mb-4 flex items-center gap-2 text-sm text-slate-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                <span>Cancelling job...</span>
              </div>
            )}
            
            {/* Error message */}
            {urlError && !cancelling && (
              <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                {urlError}
              </div>
            )}
            
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowCancelConfirm(false)
                  setUrlError('')
                }}
                disabled={cancelling}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 disabled:opacity-50"
              >
                Dismiss
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={cancelling}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {cancelling ? 'Cancelling…' : 'Yes, Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Job Processing and Results */}
      {jobInfo && (
        <div className="mt-8 space-y-6">
          {/* Action buttons row */}
          <div className="flex items-center justify-between">
            {/* Cancel button - only show when job is active (running/queued) */}
            {isJobActive && (
              <button
                type="button"
                onClick={() => setShowCancelConfirm(true)}
                disabled={cancelling}
                className="inline-flex items-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {cancelling ? 'Cancelling…' : 'Cancel Dubbing'}
              </button>
            )}

            {/* Show "Start New Job" button for completed/cancelled/failed jobs */}
            {(job?.state === 'succeeded' || job?.state === 'completed' || job?.state === 'cancelled' || job?.state === 'failed') && (
              <div className="ml-auto">
                <button
                  type="button"
                  onClick={() => {
                    setJobInfo(null)
                    setFile(null)
                    setPreviewUrl(null)
                    setDubbedUrl(null)
                    setUrlError('')
                    setTranscripts({
                      english: '',
                      swahili: '',
                      englishSegments: [],
                      swahiliSegments: [],
                    })
                    setCurrentTime(0)
                    localStorage.removeItem('current_job_id')
                  }}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  Start New Job
                </button>
              </div>
            )}
          </div>

          {/* Phase tracker / status */}
          <JobStatusPanel jobId={jobInfo.job_id} />

          {/* Maestra-style Layout: Transcripts + Video */}
          {(job?.state === 'succeeded' || job?.state === 'completed') && dubbedUrl ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ height: 'calc(100vh - 300px)' }}>
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

              {/* Right Panel: Video Player */}
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
            /* Processing State */
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
              {urlLoading || jobLoading ? (
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
                      : 'Dubbed output will appear here once the pipeline finishes.'}
                  </p>
                  <p className="text-xs text-slate-500">
                    Current state:{' '}
                    <span className="font-medium">{job?.state || '—'}</span>
                  </p>
                  {job?.output_s3_uri || job?.meta?.output_s3_uri ? (
                    <p className="text-xs text-slate-400 mt-2">
                      Output URI found, generating presigned URL...
                    </p>
                  ) : (
                    <p className="text-xs text-slate-400 mt-2">
                      Waiting for output URI...
                    </p>
                  )}
                  {urlError && (
                    <p className="text-xs text-red-600 mt-2">{urlError}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      </main>
    </div>
  )
}
