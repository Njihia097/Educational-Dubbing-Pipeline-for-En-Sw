// frontend/src/utils/jobActions.js

export async function retryJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/retry`, {
    method: 'POST',
    credentials: 'include',
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(data.error || 'Retry failed')
  }

  return data
}

export async function fetchJobLogs(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/logs`, {
    method: 'GET',
    credentials: 'include',
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(data.error || 'Failed to fetch job logs')
  }

  return data
}

export async function bulkRetryFailed() {
  const res = await fetch('/api/jobs/admin/retry_failed', {
    method: 'POST',
    credentials: 'include',
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(data.error || 'Bulk retry failed')
  }

  return data
}
