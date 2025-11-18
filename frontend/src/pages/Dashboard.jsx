// frontend/src/pages/Dashboard.jsx
import { useContext } from 'react'
import { AuthContext } from '../auth/AuthContext'
import RoleGate from '../components/RoleGate'

export default function Dashboard() {
  const { user, logout } = useContext(AuthContext)

  return (
    <div className="min-h-screen p-6">
      <h1 className="text-3xl font-bold">
        {user.role.charAt(0).toUpperCase() + user.role.slice(1)} Dashboard
      </h1>

      <p className="mt-2 text-slate-600">Welcome, {user.display_name || user.email}</p>

      <button
        className="mt-4 px-4 py-2 bg-red-500 text-white rounded"
        onClick={logout}
      >
        Logout
      </button>

      {/* ------------------------------- */}
      {/* Admin-Only Features             */}
      {/* ------------------------------- */}
      <RoleGate roles={['admin']}>
        <div className="mt-8 p-4 bg-slate-100 rounded">
          <h2 className="text-xl font-semibold">Admin Tools</h2>
          <p className="text-slate-600">Only admins can see this block.</p>
        </div>
      </RoleGate>

      {/* ------------------------------- */}
      {/* Creator / User Features         */}
      {/* ------------------------------- */}
      <RoleGate roles={['creator', 'admin']}>
        <div className="mt-8 p-4 bg-slate-100 rounded">
          <h2 className="text-xl font-semibold">Creator Tools</h2>
          <p className="text-slate-600">This block is visible to creators + admins.</p>
        </div>
      </RoleGate>
    </div>
  )
}
