// frontend/src/pages/UploadPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import useJobStatus from '../hooks/useJobStatus'
import JobStatusPanel from '../components/JobStatusPanel'

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
  const [jobInfo, setJobInfo] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)

  // For original vs dubbed comparison
  const { job, loading: jobLoading } = useJobStatus(jobInfo?.job_id, {
    pollIntervalMs: 2500,
  })
  const [originalUrl, setOriginalUrl] = useState(null)
  const [dubbedUrl, setDubbedUrl] = useState(null)
  const [urlError, setUrlError] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)

  function handleFile(e) {
    const f = e.target.files?.[0]
    setFile(f)
    setPreviewUrl(f ? URL.createObjectURL(f) : null)

    // Reset previous job state if new file chosen
    setJobInfo(null)
    setOriginalUrl(null)
    setDubbedUrl(null)
    setUrlError('')
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

      // Store job info and let inline status & comparison take over
      setJobInfo({
        job_id: data.job_id,
        task_id: data.task_id,
        uri: data.uri,
      })
      setOriginalUrl(null)
      setDubbedUrl(null)
      setUrlError('')

    } catch (err) {
      console.error(err)
      setError(err.message || 'Upload failed')
      setJobInfo(null)
    } finally {
      setSubmitting(false)
    }
  }

  // Fetch ORIGINAL video URL once input_s3_uri becomes available
  useEffect(() => {
    if (!job || !job.input_s3_uri || originalUrl) return

    async function fetchOriginal() {
      try {
        setUrlLoading(true)
        setUrlError('')

        const parsed = parseS3Uri(job.input_s3_uri)
        if (!parsed) return

        const res = await fetch(
          `/api/jobs/presign?bucket=${encodeURIComponent(
            parsed.bucket,
          )}&object=${encodeURIComponent(parsed.object)}`,
          { credentials: 'include' },
        )
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Failed to presign original video URL')

        setOriginalUrl(data.url)
      } catch (err) {
        console.error('Failed to presign original URL', err)
        setUrlError(err.message || 'Failed to prepare original video URL')
      } finally {
        setUrlLoading(false)
      }
    }

    fetchOriginal()
  }, [job, originalUrl])

  // Fetch DUBBED video URL once output_s3_uri becomes available
  useEffect(() => {
    if (!job || !job.output_s3_uri || dubbedUrl) return

    async function fetchDubbed() {
      try {
        setUrlLoading(true)
        setUrlError('')

        const parsed = parseS3Uri(job.output_s3_uri)
        if (!parsed) return

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
    <div className="max-w-5xl mx-auto">
      <h2 className="text-xl font-semibold text-slate-800 mb-3">
        Upload a Video for Dubbing
      </h2>
      <p className="text-sm text-slate-500 mb-6">
        The pipeline will run: ASR → Punctuation → Translation → TTS → Mixing → Muxing.
      </p>

      {/* Upload Form */}
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
            className="block w-full text-slate-800 file:mr-3 file:rounded-lg file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700 hover:file:bg-sky-200"
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
                className="rounded-lg border border-slate-200 w-full max-h-64 bg-black"
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

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60"
        >
          {submitting ? 'Uploading…' : 'Upload & Start Dubbing'}
        </button>
      </form>

      {/* Inline progress + side-by-side comparison */}
      {jobInfo && (
        <div className="mt-8 space-y-6">
          {/* Phase tracker / status */}
          <JobStatusPanel jobId={jobInfo.job_id} />

          {/* Side-by-side Original vs Dubbed */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between gap-2 mb-4">
              <h3 className="text-sm font-semibold text-slate-900">
                Original vs Dubbed preview
              </h3>
              {(urlLoading || jobLoading) && (
                <span className="text-[11px] text-slate-400">
                  Preparing video URLs…
                </span>
              )}
            </div>

            {urlError && (
              <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                {urlError}
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              {/* Original */}
              <div>
                <h4 className="text-xs font-medium text-slate-700 mb-2">
                  Original video
                </h4>
                {originalUrl ? (
                  <video
                    controls
                    className="w-full aspect-video rounded-lg bg-black"
                    src={originalUrl}
                  />
                ) : (
                  <p className="text-xs text-slate-500">
                    Original video URL not ready yet. Once the job is registered,
                    the original will appear here.
                  </p>
                )}
              </div>

              {/* Dubbed */}
              <div>
                <h4 className="text-xs font-medium text-slate-700 mb-2">
                  Dubbed video
                </h4>
                {dubbedUrl ? (
                  <video
                    controls
                    className="w-full aspect-video rounded-lg bg-black"
                    src={dubbedUrl}
                  />
                ) : (
                  <p className="text-xs text-slate-500">
                    Dubbed output will appear here once the pipeline finishes.
                    Current state:{' '}
                    <span className="font-medium">
                      {job?.state || '—'}

                    </span>
                  </p>
                )}
              </div>
            </div>

            

            {/* Optional deep dive button */}
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => navigate(`/dashboard/job/${jobInfo.job_id}`)}
                className="px-4 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              >
                Open Job Detail →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
