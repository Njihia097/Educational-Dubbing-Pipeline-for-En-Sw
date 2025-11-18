// frontend/src/auth/AuthContext.jsx
import { createContext, useEffect, useState } from 'react'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount, fetch current user
  useEffect(() => {
    let cancelled = false

    async function fetchMe() {
      try {
        const res = await fetch('/api/auth/me', {
          credentials: 'include',
        })
        const data = await res.json()
        if (!cancelled) {
          setUser(data.user || null)
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to fetch /me', err)
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchMe()
    return () => {
      cancelled = true
    }
  }, [])

  async function login(email, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })

    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.error || 'Login failed')
    }

    setUser(data.user)
    return data.user
  }

  async function register({ email, password, display_name }) {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password, display_name }),
    })

    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.error || 'Registration failed')
    }

    setUser(data.user)
    return data.user
  }

  async function logout() {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } finally {
      setUser(null)
    }
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
