import { ReactNode, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '../services/api'

interface ProtectedRouteProps {
  children: ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)

  useEffect(() => {
    let cancelled = false

    const token = typeof window !== 'undefined' ? window.localStorage.getItem('authToken') : null
    if (!token) {
      setIsAuthenticated(false)
      setLoading(false)
      return
    }

    // Ensure Authorization header is set for verification request
    try {
      if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } catch (err) {
      console.warn('Could not set Authorization header before verify:', err)
    }

    // Verify token with backend: GET /api/auth/me
    api
      .get('/auth/me')
      .then(() => {
        if (cancelled) return
        setIsAuthenticated(true)
      })
      .catch((err) => {
        if (cancelled) return
        console.warn('Token verification failed:', err)
        // Clean local auth if verification fails
        try {
          window.localStorage.removeItem('authToken')
          window.localStorage.removeItem('auth')
          window.localStorage.removeItem('username')
        } catch (e) {
          /* ignore */
        }
        setIsAuthenticated(false)
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return null

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}
