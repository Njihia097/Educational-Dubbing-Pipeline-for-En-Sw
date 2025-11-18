// frontend/src/pages/Dashboard.jsx
import { useContext } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { AuthContext } from '../auth/AuthContext'

export default function Dashboard() {
  const { user, logout } = useContext(AuthContext)
  const navigate = useNavigate()

  const roleLabel = user?.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
    : 'User'

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="px-4 py-4 border-b border-slate-200">
          <Link to="/dashboard" className="block">
            <div className="text-xs uppercase tracking-wide text-slate-400">
              {roleLabel}
            </div>
            <div className="font-semibold text-slate-900">
              {user?.display_name || user?.email || 'Dashboard'}
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1 text-sm">
          <NavLink
            to="/dashboard"
            end
            className={({ isActive }) =>
              [
                'flex items-center px-3 py-2 rounded-lg transition-colors',
                isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-100',
              ].join(' ')
            }
          >
            Overview
          </NavLink>

          <NavLink
            to="/dashboard/upload"
            className={({ isActive }) =>
              [
                'flex items-center px-3 py-2 rounded-lg transition-colors',
                isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-700 hover:bg-slate-100',
              ].join(' ')
            }
          >
            Upload & Dubbing
          </NavLink>

          {/* Future: Jobs, History, Admin tools, etc. */}
        </nav>

        <div className="px-4 py-4 border-t border-slate-200">
          <button
            type="button"
            onClick={handleLogout}
            className="w-full inline-flex items-center justify-center rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1">
        <header className="h-14 border-b border-slate-200 px-6 flex items-center justify-between bg-white">
          <h1 className="text-sm font-semibold text-slate-900">
            {roleLabel} dashboard
          </h1>
          {/* Optional: global actions, filters, etc. */}
        </header>

        <section className="p-6">
          {/* Nested route content: Overview / Upload / etc. */}
          <Outlet />
        </section>
      </main>
    </div>
  )
}
