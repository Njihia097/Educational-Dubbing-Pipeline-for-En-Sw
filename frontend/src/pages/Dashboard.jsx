// frontend/src/pages/Dashboard.jsx
import { useContext } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { AuthContext } from '../auth/AuthContext'
import RoleGate from '../components/RoleGate'

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

  const baseLinkClasses =
    'flex items-center px-3 py-2 rounded-lg transition-colors'

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
          {/* Overview */}
          <NavLink
            to="/dashboard"
            end
            className={({ isActive }) =>
              [
                baseLinkClasses,
                isActive
                  ? 'bg-sky-50 text-sky-700'
                  : 'text-slate-700 hover:bg-slate-100',
              ].join(' ')
            }
          >
            Overview
          </NavLink>

          {/* Upload & dubbing */}
          <NavLink
            to="/dashboard/upload"
            className={({ isActive }) =>
              [
                baseLinkClasses,
                isActive
                  ? 'bg-sky-50 text-sky-700'
                  : 'text-slate-700 hover:bg-slate-100',
              ].join(' ')
            }
          >
            Upload & Dubbing
          </NavLink>

          {/* Creator jobs */}
          <NavLink
            to="/dashboard/jobs"
            className={({ isActive }) =>
              [
                baseLinkClasses,
                isActive
                  ? 'bg-sky-50 text-sky-700'
                  : 'text-slate-700 hover:bg-slate-100',
              ].join(' ')
            }
          >
            My Jobs
          </NavLink>

          {/* Admin-only section */}
          <RoleGate roles={['admin']}>
            <div className="mt-4 mb-1 text-[11px] uppercase tracking-wide text-slate-400 px-3">
              Admin
            </div>

            <NavLink
              to="/dashboard/admin/overview"
              className={({ isActive }) =>
                [
                  baseLinkClasses,
                  isActive
                    ? 'bg-amber-50 text-amber-800'
                    : 'text-slate-700 hover:bg-slate-100',
                ].join(' ')
              }
            >
              System Overview
            </NavLink>

            <NavLink
              to="/dashboard/admin/monitoring"
              className={({ isActive }) =>
                [
                  baseLinkClasses,
                  isActive
                    ? 'bg-amber-50 text-amber-800'
                    : 'text-slate-700 hover:bg-slate-100',
                ].join(' ')
              }
            >
              Worker Monitoring
            </NavLink>

            <NavLink
              to="/dashboard/admin/jobs"
              className={({ isActive }) =>
                [
                  baseLinkClasses,
                  isActive
                    ? 'bg-amber-50 text-amber-800'
                    : 'text-slate-700 hover:bg-slate-100',
                ].join(' ')
              }
            >
              All Jobs
            </NavLink>
          </RoleGate>
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
        </header>

        <section className="p-6">
          {/* Nested route content: Overview / Upload / Jobs / Admin views */}
          <Outlet />
        </section>
      </main>
    </div>
  )
}
