import { useEffect, useState } from 'react'
import {
  cancelFlightOperation,
  fetchAdminBookings,
  fetchAdminDashboardSummary,
  fetchOperationsAircraftUtilization,
  fetchOperationsAuditLogs,
  fetchOperationsCrewUtilization,
  retimeFlightOperation,
  swapAircraftOperation,
} from '../lib/api'

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
  const [aircraftUtil, setAircraftUtil] = useState([])
  const [crewUtil, setCrewUtil] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [adminBookings, setAdminBookings] = useState([])

  const [bookingStatus, setBookingStatus] = useState('')
  const [bookingFlightId, setBookingFlightId] = useState('')
  const [bookingPassengerId, setBookingPassengerId] = useState('')
  const [bookingPassengerEmail, setBookingPassengerEmail] = useState('')
  const [bookingLimit, setBookingLimit] = useState('200')

  const [opsFlightId, setOpsFlightId] = useState('')
  const [cancelReason, setCancelReason] = useState('Weather and operational constraints')
  const [autoReaccommodate, setAutoReaccommodate] = useState(true)
  const [reaccommodationWindow, setReaccommodationWindow] = useState('24')

  const [retimeDeparture, setRetimeDeparture] = useState('')
  const [retimeArrival, setRetimeArrival] = useState('')
  const [retimeReason, setRetimeReason] = useState('Airport congestion adjustments')

  const [newAircraftId, setNewAircraftId] = useState('')
  const [swapReason, setSwapReason] = useState('Equipment rotation')

  const [opResult, setOpResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingOps, setLoadingOps] = useState(false)
  const [loadingBookings, setLoadingBookings] = useState(false)
  const [error, setError] = useState('')
  const [bookingError, setBookingError] = useState('')

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

  async function loadOperationsData() {
    try {
      const [aircraftRows, crewRows, logs] = await Promise.all([
        fetchOperationsAircraftUtilization(14),
        fetchOperationsCrewUtilization(14),
        fetchOperationsAuditLogs(30),
      ])
      setAircraftUtil(aircraftRows)
      setCrewUtil(crewRows)
      setAuditLogs(logs)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to fetch operations metrics.')
    }
  }

  async function loadAdminBookings(filters = {}) {
    setLoadingBookings(true)
    setBookingError('')

    try {
      const params = {
        ...(filters.status ? { status: filters.status } : {}),
        ...(filters.flight_id ? { flight_id: Number(filters.flight_id) } : {}),
        ...(filters.passenger_id ? { passenger_id: Number(filters.passenger_id) } : {}),
        ...(filters.passenger_email ? { passenger_email: filters.passenger_email } : {}),
        limit: Number(filters.limit || 200),
      }
      const rows = await fetchAdminBookings(params)
      setAdminBookings(Array.isArray(rows) ? rows : [])
    } catch (err) {
      setAdminBookings([])
      setBookingError(err?.response?.data?.detail || 'Failed to fetch bookings.')
    } finally {
      setLoadingBookings(false)
    }
  }

  async function handleBookingFilter(event) {
    event.preventDefault()
    await loadAdminBookings({
      status: bookingStatus,
      flight_id: bookingFlightId,
      passenger_id: bookingPassengerId,
      passenger_email: bookingPassengerEmail.trim(),
      limit: bookingLimit,
    })
  }

  async function handleClearBookingFilter() {
    setBookingStatus('')
    setBookingFlightId('')
    setBookingPassengerId('')
    setBookingPassengerEmail('')
    setBookingLimit('200')
    await loadAdminBookings({ limit: 200 })
  }

  async function handleCancelFlight(event) {
    event.preventDefault()
    if (!opsFlightId) {
      setError('Flight ID is required for disruption actions.')
      return
    }
    setLoadingOps(true)
    setError('')
    setOpResult(null)

    try {
      const data = await cancelFlightOperation(Number(opsFlightId), {
        reason: cancelReason,
        auto_reaccommodate: autoReaccommodate,
        max_hours_window: Number(reaccommodationWindow),
      })
      setOpResult(data)
      await loadSummary()
      await loadOperationsData()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Cancel and reaccommodation failed.')
    } finally {
      setLoadingOps(false)
    }
  }

  async function handleRetimeFlight(event) {
    event.preventDefault()
    if (!opsFlightId || !retimeDeparture || !retimeArrival) {
      setError('Flight ID, new departure, and new arrival are required for retime.')
      return
    }
    setLoadingOps(true)
    setError('')
    setOpResult(null)

    try {
      const data = await retimeFlightOperation(Number(opsFlightId), {
        new_departure_time: new Date(retimeDeparture).toISOString(),
        new_arrival_time: new Date(retimeArrival).toISOString(),
        reason: retimeReason,
      })
      setOpResult(data)
      await loadOperationsData()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Retime failed.')
    } finally {
      setLoadingOps(false)
    }
  }

  async function handleSwapAircraft(event) {
    event.preventDefault()
    if (!opsFlightId || !newAircraftId) {
      setError('Flight ID and new aircraft ID are required for swap.')
      return
    }
    setLoadingOps(true)
    setError('')
    setOpResult(null)

    try {
      const data = await swapAircraftOperation(Number(opsFlightId), {
        new_aircraft_id: Number(newAircraftId),
        reason: swapReason,
      })
      setOpResult(data)
      await loadOperationsData()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Aircraft swap failed.')
    } finally {
      setLoadingOps(false)
    }
  }

  useEffect(() => {
    loadSummary()
    loadOperationsData()
    loadAdminBookings({ limit: 200 })
  }, [])

  return (
    <main className="page">
      <section className="panel panel-hero">
        <div className="panel-header">
          <div>
            <p className="page-kicker">Operations Snapshot</p>
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

        <h3>Booking Explorer</h3>
        <form className="grid-form" onSubmit={handleBookingFilter}>
          <label>
            Status
            <select value={bookingStatus} onChange={(e) => setBookingStatus(e.target.value)}>
              <option value="">All</option>
              <option value="Pending">Pending</option>
              <option value="Confirmed">Confirmed</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </label>
          <label>
            Flight ID
            <input
              type="number"
              min="1"
              value={bookingFlightId}
              onChange={(e) => setBookingFlightId(e.target.value)}
              placeholder="For example 12"
            />
          </label>
          <label>
            Passenger ID
            <input
              type="number"
              min="1"
              value={bookingPassengerId}
              onChange={(e) => setBookingPassengerId(e.target.value)}
              placeholder="For example 3"
            />
          </label>
          <label>
            Passenger Email
            <input
              value={bookingPassengerEmail}
              onChange={(e) => setBookingPassengerEmail(e.target.value)}
              placeholder="name@email.com"
            />
          </label>
          <label>
            Limit
            <input
              type="number"
              min="1"
              max="5000"
              value={bookingLimit}
              onChange={(e) => setBookingLimit(e.target.value)}
            />
          </label>
          <button type="submit" disabled={loadingBookings}>
            {loadingBookings ? 'Filtering...' : 'Apply Filters'}
          </button>
          <button type="button" onClick={handleClearBookingFilter} disabled={loadingBookings}>
            Clear Filters
          </button>
        </form>

        {bookingError ? <p className="error-msg">{bookingError}</p> : null}
        {loadingBookings ? <p className="subtle">Loading filtered bookings...</p> : null}
        {!loadingBookings && adminBookings.length === 0 ? (
          <p className="subtle">No bookings found for the current filter combination.</p>
        ) : null}
        {adminBookings.length > 0 ? (
          <div className="result-list">
            {adminBookings.map((booking) => (
              <article className="flight-card" key={booking.booking_reference}>
                <div className="flight-meta">
                  <p className="flight-number">PNR {booking.booking_reference} • {booking.flight_number}</p>
                  <p>
                    {booking.passenger_first_name} {booking.passenger_last_name} ({booking.passenger_email})
                  </p>
                  <p>
                    Flight ID {booking.flight_id} • {booking.origin_code} to {booking.destination_code}
                  </p>
                  <p>
                    {booking.seat_number} | {booking.class_type} | {booking.status}
                  </p>
                  <p>Booked: {new Date(booking.booking_date).toLocaleString()}</p>
                  <p>Departure: {new Date(booking.departure_time).toLocaleString()}</p>
                  <p>Total: INR {booking.total_amount}</p>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        <h3>Flight Disruption Console</h3>
        <form className="grid-form" onSubmit={handleCancelFlight}>
          <label>
            Flight ID
            <input value={opsFlightId} onChange={(e) => setOpsFlightId(e.target.value)} required />
          </label>
          <label>
            Cancellation Reason
            <input value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} required />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={autoReaccommodate}
              onChange={(e) => setAutoReaccommodate(e.target.checked)}
            />
            Auto-reaccommodate affected bookings
          </label>
          <label>
            Reaccommodation Window (hours)
            <input
              type="number"
              min="1"
              max="72"
              value={reaccommodationWindow}
              onChange={(e) => setReaccommodationWindow(e.target.value)}
            />
          </label>
          <button type="submit" disabled={loadingOps}>
            {loadingOps ? 'Processing...' : 'Cancel Flight + Reaccommodate'}
          </button>
        </form>

        <form className="grid-form" onSubmit={handleRetimeFlight}>
          <label>
            New Departure
            <input type="datetime-local" value={retimeDeparture} onChange={(e) => setRetimeDeparture(e.target.value)} required />
          </label>
          <label>
            New Arrival
            <input type="datetime-local" value={retimeArrival} onChange={(e) => setRetimeArrival(e.target.value)} required />
          </label>
          <label>
            Retime Reason
            <input value={retimeReason} onChange={(e) => setRetimeReason(e.target.value)} required />
          </label>
          <button type="submit" disabled={loadingOps || !opsFlightId}>
            {loadingOps ? 'Updating...' : 'Retime Flight'}
          </button>
        </form>

        <form className="grid-form" onSubmit={handleSwapAircraft}>
          <label>
            New Aircraft ID
            <input value={newAircraftId} onChange={(e) => setNewAircraftId(e.target.value)} required />
          </label>
          <label>
            Swap Reason
            <input value={swapReason} onChange={(e) => setSwapReason(e.target.value)} required />
          </label>
          <button type="submit" disabled={loadingOps || !opsFlightId}>
            {loadingOps ? 'Swapping...' : 'Swap Aircraft'}
          </button>
        </form>

        {opResult ? (
          <div className="success-box">
            <p>{opResult.message || 'Operation completed successfully.'}</p>
            {opResult.moved_bookings !== undefined ? <p>Moved bookings: {opResult.moved_bookings}</p> : null}
            {opResult.failed_bookings !== undefined ? <p>Failed bookings: {opResult.failed_bookings}</p> : null}
          </div>
        ) : null}

        <h3>Aircraft Utilization (Next 14 Days)</h3>
        {aircraftUtil.length === 0 ? (
          <p className="subtle">No aircraft utilization data available.</p>
        ) : (
          <div className="result-list">
            {aircraftUtil.slice(0, 10).map((row) => (
              <article className="flight-card" key={row.aircraft_id}>
                <div className="flight-meta">
                  <p className="flight-number">Aircraft #{row.aircraft_id} ({row.registration_number})</p>
                  <p>Scheduled Flights: {row.scheduled_flights}</p>
                  <p>Utilization Hours: {row.utilization_hours}</p>
                </div>
              </article>
            ))}
          </div>
        )}

        <h3>Crew Utilization (Next 14 Days)</h3>
        {crewUtil.length === 0 ? (
          <p className="subtle">No crew utilization data available.</p>
        ) : (
          <div className="result-list">
            {crewUtil.slice(0, 10).map((row) => (
              <article className="flight-card" key={row.employee_id}>
                <div className="flight-meta">
                  <p className="flight-number">{row.employee_name} ({row.role})</p>
                  <p>Assigned Flights: {row.assigned_flights}</p>
                  <p>Utilization Hours: {row.utilization_hours}</p>
                </div>
              </article>
            ))}
          </div>
        )}

        <h3>Operational Audit Log</h3>
        {auditLogs.length === 0 ? (
          <p className="subtle">No recent operational actions found.</p>
        ) : (
          <div className="result-list">
            {auditLogs.map((entry) => (
              <article className="flight-card" key={entry.audit_id}>
                <div className="flight-meta">
                  <p className="flight-number">{entry.action_type} • {entry.entity_type} {entry.entity_id}</p>
                  <p>Status: {entry.action_status}</p>
                  <p>Actor User ID: {entry.actor_user_id}</p>
                  <p>Time: {new Date(entry.created_at).toLocaleString()}</p>
                  {entry.action_notes ? <p>Notes: {entry.action_notes}</p> : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
