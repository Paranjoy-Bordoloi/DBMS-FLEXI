import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import ProtectedRoute from './components/ProtectedRoute'
import TopNav from './components/TopNav'
import { clearToken, fetchMe, getSavedUser, saveUser } from './lib/api'
import BookingPage from './pages/BookingPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import LoginPage from './pages/LoginPage'
import ManageBookingPage from './pages/ManageBookingPage'
import SearchPage from './pages/SearchPage'

function App() {
  const [me, setMe] = useState(getSavedUser())
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    let active = true

    async function bootstrap() {
      const token = localStorage.getItem('ars_token')
      if (!token) {
        setBooting(false)
        return
      }

      try {
        const profile = await fetchMe()
        if (active) {
          setMe(profile)
          saveUser(profile)
        }
      } catch {
        clearToken()
        if (active) {
          setMe(null)
        }
      } finally {
        if (active) {
          setBooting(false)
        }
      }
    }

    bootstrap()

    return () => {
      active = false
    }
  }, [])

  if (booting) {
    return <div className="boot-screen">Loading application...</div>
  }

  return (
    <BrowserRouter>
      {me ? <TopNav me={me} /> : null}
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={setMe} />} />
        <Route
          path="/search"
          element={
            <ProtectedRoute>
              <SearchPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/book"
          element={
            <ProtectedRoute>
              <BookingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/manage"
          element={
            <ProtectedRoute>
              <ManageBookingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={me ? '/search' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
