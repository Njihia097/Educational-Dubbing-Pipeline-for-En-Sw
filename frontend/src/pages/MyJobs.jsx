// frontend/src/pages/MyJobs.jsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { retryJob, fetchJobLogs } from '../utils/jobActions'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import SearchBar from '../components/SearchBar'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString()
}

export default function MyJobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [search, setSearch] = useState('')
  const [stateFilter, setStateFilter] = useState('') // all
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)

  async function loadJobs(opts = {}) {
    const { nextPage = page, searchTerm = search, state = stateFilter } = opts

    try {
      setLoading(true)
      setError('')

      const params = new URLSearchParams()
      params.set('page', String(nextPage))
      params.set('page_size', String(pageSize))
      if (searchTerm) params.set('search', searchTerm)
      if (state) params.set('state', state)

      const res = await fetch(`/api/jobs/my?${params.toString()}`, {
        credentials: 'include',
      })
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || 'Failed to load jobs')
      }

      setJobs(data.jobs || [])
      setPage(data.page || nextPage)
      setTotal(data.total || 0)
    } catch (err) {
      console.error('MyJobs fetch error', err)
      setError(err.message || 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs({ nextPage: 1 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // whenever search / stateFilter changes, reset to page 1
  useEffect(() => {
    loadJobs({ nextPage: 1, searchTerm: search, state: stateFilter })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, stateFilter])

  const handlePageChange = (nextPage) => {
    loadJobs({ nextPage })
  }

  async function handleExportLogs(jobId) {
    try {
      const data = await fetchJobLogs(jobId)
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `job-${jobId}-logs.json`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert('Failed to export logs: ' + err.message)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-base font-semibold text-slate-900">My Jobs</h2>
        <p className="text-xs text-slate-500 mt-1">
          All dubbing jobs you have created, most recent first.
        </p>
      </div>

      {/* Filters + search */}
      <SearchBar
        value={search}
        onChange={setSearch}
        placeholder="Search by video name or job ID…"
      >
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-2 py-1 text-xs bg-white"
        >
          <option value="">All states</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </SearchBar>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading && jobs.length === 0 ? (
        <div className="text-sm text-slate-500">Loading jobs…</div>
      ) : jobs.length === 0 ? (
        <div className="text-sm text-slate-500">
          You have no jobs yet.{' '}
          <Link to="/dashboard/upload" className="text-sky-600 underline">
            Upload a video
          </Link>{' '}
          to get started.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    Job ID
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    Video
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    State
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    Progress
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    Retries
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">
                    Created
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-slate-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-mono text-[11px] text-slate-700">
                      {job.id.slice(0, 8)}…
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {job.video_name || '—'}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge state={job.state} />
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {typeof job.progress === 'number'
                        ? `${job.progress}%`
                        : '—'}
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {job.retry_count || 0}
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {formatDate(job.created_at)}
                    </td>
                    <td className="px-3 py-2 text-right space-x-2">
                      {/* OPEN Job */}
                      <Link
                        to={`/dashboard/job/${job.id}`}
                        className="inline-flex text-[11px] px-2 py-1 rounded-md border border-slate-200 hover:bg-slate-50 text-slate-700"
                      >
                        Open →
                      </Link>

                      {/* EXPORT LOGS */}
                      <button
                        type="button"
                        onClick={() => handleExportLogs(job.id)}
                        className="inline-flex text-[11px] px-2 py-1 rounded-md border border-slate-200 hover:bg-slate-50 text-slate-700"
                      >
                        Logs
                      </button>

                      {/* RETRY BUTTON (only if terminal state) */}
                      {['failed', 'cancelled', 'succeeded', 'completed'].includes(
                        job.state
                      ) && (
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await retryJob(job.id)
                              await loadJobs({ nextPage: page })
                            } catch (err) {
                              // eslint-disable-next-line no-alert
                              alert('Retry failed: ' + err.message)
                            }
                          }}
                          className="inline-flex text-[11px] px-2 py-1 rounded-md bg-amber-500 text-white hover:bg-amber-600"
                        >
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  )
}
