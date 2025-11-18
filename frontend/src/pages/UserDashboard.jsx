// frontend/src/pages/UserDashboard.jsx
import useAuth from '../hooks/useAuth'

export default function UserDashboard() {
  const { user, logout } = useAuth()
  const roleLabel = user?.role || 'user'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
          <h1 className="text-base font-semibold text-slate-900">
            Educational Dubbing – {roleLabel} dashboard
          </h1>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-xs text-slate-500">
                {user.display_name || user.email} ({user.role})
              </span>
            )}
            <button
              className="text-xs font-medium text-slate-600 hover:text-slate-900"
              onClick={logout}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-5xl px-4 py-10">
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center">
            <p className="text-2xl font-semibold text-slate-900 mb-2">
              {roleLabel} dashboard
            </p>
            <p className="text-sm text-slate-500">
              This is your placeholder dashboard. We&apos;ll plug in real dubbing features
              and project views in the next phase.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
