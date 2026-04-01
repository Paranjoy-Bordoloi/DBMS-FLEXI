import { useEffect, useState } from 'react'
import { fetchAdminDashboardSummary } from '../lib/api'

function StatCard({ label, value }) {
  return (
    <article className="stat-card">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
    </article>
  )
}

export default function AdminDashboardPage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadSummary() {
    setLoading(true)
    setError('')

    try {
      const data = await fetchAdminDashboardSummary()
      setSummary(data)
    } catch (err) {
      setSummary(null)
      setError(err?.response?.data?.detail || 'Failed to fetch admin dashboard summary.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSummary()
  }, [])

  return (
    <main className="page">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Admin Dashboard</h2>
            <p className="subtle">Data source: Java/Tomcat service (`/admin/dashboard/summary`).</p>
          </div>
          <button type="button" onClick={loadSummary} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {error ? <p className="error-msg">{error}</p> : null}

        {summary ? (
          <div className="stats-grid">
            <StatCard label="Total Bookings" value={summary.total_bookings} />
            <StatCard label="Confirmed Bookings" value={summary.confirmed_bookings} />
            <StatCard label="Total Revenue" value={`INR ${summary.total_revenue}`} />
            <StatCard
              label="Average Occupancy"
              value={`${summary.average_occupancy_percent}%`}
            />
          </div>
        ) : loading ? (
          <p className="subtle">Loading dashboard summary...</p>
        ) : null}
      </section>
    </main>
  )
}
