// frontend/src/pages/UploadPage.jsx
import { useState } from 'react'
import useAuth from '../hooks/useAuth'
import JobStatusPanel from '../components/JobStatusPanel'

export default function UploadPage() {
  const { user } = useAuth()
  const [file, setFile] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [jobInfo, setJobInfo] = useState(null) // { job_id, task_id, uri }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (!file) {
      setError('Please choose a video file first.')
      return
    }
    if (!user) {
      setError('You must be logged in to upload.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('owner_id', user.id)
    formData.append('project_id', 'auto') // use backend auto-project logic

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

      setJobInfo({
        job_id: data.job_id,
        task_id: data.task_id,
        uri: data.uri,
      })
    } catch (err) {
      console.error('Upload failed', err)
      setError(err.message || 'Upload failed')
      setJobInfo(null)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold text-slate-900 mb-2">
        Upload a video for dubbing
      </h2>
      <p className="text-sm text-slate-500 mb-6">
        Select a source video. The system will run ASR → translation → TTS → mixing
        and produce a dubbed output.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4 bg-white border border-slate-200 rounded-xl p-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Video file
          </label>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700 hover:file:bg-sky-100"
          />
          <p className="mt-1 text-xs text-slate-400">
            Supported formats depend on FFmpeg in your backend container.
          </p>
        </div>

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
          {submitting ? 'Uploading…' : 'Upload & start dubbing'}
        </button>
      </form>

      {/* Job status / polling area */}
      {jobInfo && (
        <div className="mt-8">
          <JobStatusPanel jobId={jobInfo.job_id} />
        </div>
      )}
    </div>
  )
}
