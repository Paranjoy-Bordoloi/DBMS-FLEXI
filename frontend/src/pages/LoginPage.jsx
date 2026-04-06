import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { fetchMe, login, saveToken, saveUser } from '../lib/api'

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const signupEmail = location.state?.signupEmail
    const signupSuccess = location.state?.signupSuccess
    if (signupEmail) {
      setEmail(signupEmail)
    }
    if (signupSuccess) {
      setMessage(signupSuccess)
    }
  }, [location.state])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')
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
          {message ? <p className="success-msg">{message}</p> : null}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="auth-switch">
          New user? <Link to="/signup">Create a passenger account</Link>
        </p>
      </section>
    </main>
  )
}
