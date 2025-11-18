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
        if (!res.ok) {
          throw new Error(data.error || 'Failed to fetch job status')
        }

        if (!cancelled) {
          setStatus({
            state: data.state,
            progress: data.progress ?? data.meta?.progress ?? null,
            steps: data.steps || [],
            meta: data.meta || {},
          })
          setError('')
        }

        // Stop polling once job is completed or failed
        if (data.state === 'completed' || data.state === 'failed' || data.state === 'cancelled') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Job status fetch error', err)
          setError(err.message || 'Failed to fetch job status')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    // Initial fetch
    fetchStatus()

    // Set up polling
    intervalRef.current = setInterval(fetchStatus, pollIntervalMs)

    return () => {
      cancelled = true
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [jobId, pollIntervalMs])

  return { status, loading, error }
}
