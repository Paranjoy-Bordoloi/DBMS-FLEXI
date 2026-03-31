import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchMe, login, saveToken, saveUser } from '../lib/api'

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('testuser1@example.com')
  const [password, setPassword] = useState('Test@1234')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const tokenResponse = await login({ email, password })
      saveToken(tokenResponse.access_token)
      const me = await fetchMe()
      saveUser(me)
      onLogin(me)

      const next = location.state?.from || '/search'
      navigate(next, { replace: true })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed. Please check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page page-login">
      <section className="auth-card">
        <p className="eyebrow">Welcome Back</p>
        <h2>Sign in to continue booking</h2>
        <p className="subtle">Use your registered passenger credentials.</p>

        <form className="stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          {error ? <p className="error-msg">{error}</p> : null}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </section>
    </main>
  )
}
