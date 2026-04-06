import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../lib/api'

const initialForm = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  passport_number: '',
  date_of_birth: '',
  password: '',
  address: '',
}

function isPasswordComplex(password) {
  if (password.length < 8) {
    return false
  }
  const hasUpper = /[A-Z]/.test(password)
  const hasLower = /[a-z]/.test(password)
  const hasDigit = /\d/.test(password)
  const hasSpecial = /[^A-Za-z0-9]/.test(password)
  return hasUpper && hasLower && hasDigit && hasSpecial
}

function getPasswordRules(password) {
  return {
    minLength: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  }
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function isValidPhone(phone) {
  return /^\+?[0-9]{10,15}$/.test(phone)
}

function getApiErrorMessage(err) {
  const detail = err?.response?.data?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const combined = detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(' | ')
    if (combined) {
      return combined
    }
  }

  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string') {
      return detail.msg
    }
    return 'Signup request validation failed. Please review all fields.'
  }

  return 'Could not create account. Please check your details.'
}

export default function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const passwordRules = getPasswordRules(form.password)
  const emailValid = isValidEmail(form.email)
  const phoneValid = isValidPhone(form.phone)
  const canSubmit =
    form.first_name.trim() &&
    form.last_name.trim() &&
    form.passport_number.trim() &&
    form.date_of_birth &&
    emailValid &&
    phoneValid &&
    isPasswordComplex(form.password)

  function setField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (!isPasswordComplex(form.password)) {
      setError('Password must be at least 8 characters and include upper, lower, digit, and special character.')
      return
    }

    setLoading(true)

    try {
      const payload = {
        ...form,
        address: form.address || null,
      }
      await register(payload)
      setMessage('Account created successfully. Redirecting to login...')
      navigate('/login', {
        replace: true,
        state: {
          signupEmail: form.email,
          signupSuccess: 'Account created. Please sign in.',
        },
      })
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page page-login">
      <section className="auth-card">
        <p className="eyebrow">Create Account</p>
        <h2>Sign up as a passenger</h2>
        <p className="subtle">Password must be at least 8 characters and include upper, lower, digit, and special character.</p>

        <form className="grid-form" onSubmit={handleSubmit}>
          <label>
            First Name
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => setField('first_name', e.target.value)}
              required
            />
          </label>

          <label>
            Last Name
            <input
              type="text"
              value={form.last_name}
              onChange={(e) => setField('last_name', e.target.value)}
              required
            />
          </label>

          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(e) => setField('email', e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <ul className="rule-list">
            <li className={emailValid ? 'rule valid' : 'rule invalid'}>
              {emailValid ? 'Valid email format' : 'Enter a valid email (example@domain.com)'}
            </li>
          </ul>

          <label>
            Phone
            <input
              type="text"
              value={form.phone}
              onChange={(e) => setField('phone', e.target.value)}
              autoComplete="tel"
              required
            />
          </label>
          <ul className="rule-list">
            <li className={phoneValid ? 'rule valid' : 'rule invalid'}>
              {phoneValid ? 'Valid phone number' : 'Use 10 to 15 digits (optional leading +)'}
            </li>
          </ul>

          <label>
            Passport Number
            <input
              type="text"
              value={form.passport_number}
              onChange={(e) => setField('passport_number', e.target.value)}
              autoComplete="off"
              required
            />
          </label>

          <label>
            Date of Birth
            <input
              type="date"
              value={form.date_of_birth}
              onChange={(e) => setField('date_of_birth', e.target.value)}
              required
            />
          </label>

          <label style={{ gridColumn: '1 / -1' }}>
            Address (optional)
            <input
              type="text"
              value={form.address}
              onChange={(e) => setField('address', e.target.value)}
            />
          </label>

          <label style={{ gridColumn: '1 / -1' }}>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(e) => setField('password', e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <ul className="rule-list" style={{ gridColumn: '1 / -1' }}>
            <li className={passwordRules.minLength ? 'rule valid' : 'rule invalid'}>At least 8 characters</li>
            <li className={passwordRules.upper ? 'rule valid' : 'rule invalid'}>Contains uppercase letter</li>
            <li className={passwordRules.lower ? 'rule valid' : 'rule invalid'}>Contains lowercase letter</li>
            <li className={passwordRules.digit ? 'rule valid' : 'rule invalid'}>Contains number</li>
            <li className={passwordRules.special ? 'rule valid' : 'rule invalid'}>Contains special character</li>
          </ul>

          {error ? <p className="error-msg" style={{ gridColumn: '1 / -1' }}>{error}</p> : null}
          {message ? <p className="success-msg" style={{ gridColumn: '1 / -1' }}>{message}</p> : null}

          <button type="submit" disabled={loading || !canSubmit} style={{ gridColumn: '1 / -1' }}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  )
}
