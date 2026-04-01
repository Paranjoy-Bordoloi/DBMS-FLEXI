import { Link, useLocation, useNavigate } from 'react-router-dom'
import { clearToken } from '../lib/api'

const links = [
  { to: '/search', label: 'Search Flights' },
  { to: '/book', label: 'Book Ticket' },
  { to: '/manage', label: 'Manage Booking' },
  { to: '/admin', label: 'Admin Dashboard' },
]

export default function TopNav({ me }) {
  const location = useLocation()
  const navigate = useNavigate()

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
    <header className="top-nav">
      <div className="brand-wrap">
        <p className="brand-kicker">Airline Reservation System</p>
        <h1 className="brand-title">Passenger Console</h1>
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
      </nav>
      <div className="user-chip">
        <span>{me?.email || 'Not signed in'}</span>
        <button type="button" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </header>
  )
}
