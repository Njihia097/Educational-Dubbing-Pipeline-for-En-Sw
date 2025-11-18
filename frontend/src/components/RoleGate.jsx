// frontend/src/components/RoleGate.jsx
import { useContext } from 'react'
import { AuthContext } from '../auth/AuthContext'

export default function RoleGate({ roles, children }) {
  const { user } = useContext(AuthContext)

  if (!user) return null
  if (!roles.includes(user.role)) return null

  return children
}
