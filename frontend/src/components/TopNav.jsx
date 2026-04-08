import { Link, useLocation, useNavigate } from 'react-router-dom'

const links = [
  { to: '/search', label: 'Book Flight' },
  { to: '/manage', label: 'Manage Booking' },
]

function getUserIdentity(email) {
  if (!email) {
    return { initials: 'NA', title: 'Not signed in' }
  }

  const local = email.split('@')[0]
  const parts = local.split(/[._-]/).filter(Boolean)
  const initials = parts.length > 1
    ? `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
    : (local.slice(0, 2) || 'US').toUpperCase()

  const title = parts.length
    ? parts.map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
    : local

  return { initials, title }
}

export default function TopNav({ me, onLogout }) {
  const location = useLocation()
  const navigate = useNavigate()
  const identity = getUserIdentity(me?.email)

  function handleLogout() {
    onLogout()
    navigate('/login')
  }

  return (
    <header className="top-nav">
      <div className="nav-top">
        <div className="brand-wrap">
          <p className="brand-kicker">Airline Reservation System</p>
          <h1 className="brand-title">Passenger Console</h1>
        </div>

        <div className="account-pill">
          <div className="account-avatar">{identity.initials}</div>
          <div className="account-copy">
            <p className="account-title">{identity.title}</p>
            <p className="account-email">{me?.email || 'Not signed in'}</p>
          </div>
          <button type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      <nav className="link-row">
        {links.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={location.pathname === item.to ? 'nav-link active' : 'nav-link'}
          >
            {item.label}
          </Link>
        ))}
        {me?.role === 'Admin' ? (
          <Link
            to="/admin"
            className={location.pathname === '/admin' ? 'nav-link active' : 'nav-link'}
          >
            Admin Dashboard
          </Link>
        ) : null}
      </nav>
    </header>
  )
}
