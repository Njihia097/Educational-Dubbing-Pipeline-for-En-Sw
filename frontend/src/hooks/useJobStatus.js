// frontend/src/hooks/useJobStatus.js
import { useEffect, useRef, useState } from 'react'

export default function useJobStatus(jobId, { pollIntervalMs = 2500 } = {}) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!jobId) return
    let cancelled = false

    async function fetchStatus() {
      try {
        const res = await fetch(`/api/jobs/status/${jobId}`, {
          credentials: 'include',
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Failed to fetch job status')

        if (!cancelled) {
          setStatus({
            id: data.id,
            state: data.state,
            current_step: data.current_step,
            progress: data.progress ?? data.meta?.progress ?? null,
            steps: data.steps || [],
            meta: data.meta || {},
            input_s3_uri: data.input_s3_uri,
            output_s3_uri: data.output_s3_uri,
            created_at: data.created_at,
            started_at: data.started_at,
            finished_at: data.finished_at,

            retry_count: data.retry_count || 0,
            last_error_message: data.last_error_message || null,
          })
          setError('')
        }

        if (['completed', 'succeeded', 'failed', 'cancelled'].includes(data.state)) {
          clearInterval(intervalRef.current)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchStatus()
    intervalRef.current = setInterval(fetchStatus, pollIntervalMs)

    return () => {
      cancelled = true
      clearInterval(intervalRef.current)
    }
  }, [jobId, pollIntervalMs])

  return {
    job: status,
    status,
    loading,
    error,
    refresh: () => {
      if (!jobId) return
      fetch(`/api/jobs/status/${jobId}`, { credentials: 'include' })
        .then((res) => res.json())
        .then((data) =>
          setStatus((prev) => ({
            ...(prev || {}),
            ...data,
          }))
        )
    },
  }
}
