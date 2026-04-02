import { Navigate, useLocation } from 'react-router-dom'

export default function ProtectedRoute({ children, requiredRole = null }) {
  const token = localStorage.getItem('ars_token')
  const rawUser = localStorage.getItem('ars_user')
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (requiredRole) {
    let user = null
    try {
      user = rawUser ? JSON.parse(rawUser) : null
    } catch {
      user = null
    }

    if (!user || user.role !== requiredRole) {
      return <Navigate to="/search" replace />
    }
  }

  return children
}
