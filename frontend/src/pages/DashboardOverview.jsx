// frontend/src/pages/DashboardOverview.jsx
import useAuth from '../hooks/useAuth'
import { Link } from 'react-router-dom'

export default function DashboardOverview() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Welcome back, {user?.display_name || user?.email || 'creator'}
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Use the sidebar to upload new videos, track your dubbing jobs, and{' '}
          {isAdmin ? 'monitor all activity across the system.' : 'review your past dubbing runs.'}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800">
            Start a new dubbing job
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Upload a new educational video and run it through the full pipeline:
            ASR → MT → TTS → Mix → Mux.
          </p>
          <Link
            to="/dashboard/upload"
            className="inline-flex mt-3 text-xs px-3 py-2 rounded-lg bg-sky-600 text-white font-medium hover:bg-sky-700"
          >
            Go to Upload →
          </Link>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-800">
            Review recent jobs
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Quickly jump into the jobs table to see statuses, retries, and open
            detailed views.
          </p>
          <Link
            to={isAdmin ? '/dashboard/admin/jobs' : '/dashboard/jobs'}
            className="inline-flex mt-3 text-xs px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            Open jobs table →
          </Link>
        </div>
      </div>
    </div>
  )
}
