import { useEffect, useState } from 'react'
import { cancelBooking, fetchCurrentBookings, retrieveBooking } from '../lib/api'

export default function ManageBookingPage() {
  const [pnr, setPnr] = useState(localStorage.getItem('ars_last_pnr') || '')
  const [lastName, setLastName] = useState('')
  const [reason, setReason] = useState('Change of travel plan')
  const [myBookings, setMyBookings] = useState([])
  const [retrieved, setRetrieved] = useState(null)
  const [cancelResult, setCancelResult] = useState(null)
  const [error, setError] = useState('')
  const [loadingCurrent, setLoadingCurrent] = useState(true)
  const [loadingRetrieve, setLoadingRetrieve] = useState(false)
  const [loadingCancel, setLoadingCancel] = useState(false)

  useEffect(() => {
    let active = true
    setLoadingCurrent(true)
    fetchCurrentBookings()
      .then((rows) => {
        if (!active) {
          return
        }
        setMyBookings(Array.isArray(rows) ? rows : [])

        const remembered = localStorage.getItem('ars_last_pnr')
        if (remembered && Array.isArray(rows)) {
          const match = rows.find((item) => item.booking_reference === remembered)
          if (match) {
            const extractedLast = String(match.passenger_name || '').trim().split(' ').filter(Boolean).slice(-1)[0] || ''
            setPnr(match.booking_reference)
            setLastName(extractedLast)
            setRetrieved(match)
          }
        }
      })
      .catch((err) => {
        if (!active) {
          return
        }
        setMyBookings([])
        setError(err?.response?.data?.detail || 'Could not load your current bookings.')
      })
      .finally(() => {
        if (active) {
          setLoadingCurrent(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  function selectBooking(booking) {
    const extractedLast = String(booking.passenger_name || '').trim().split(' ').filter(Boolean).slice(-1)[0] || ''
    setPnr(booking.booking_reference)
    setLastName(extractedLast)
    setRetrieved(booking)
    setCancelResult(null)
    localStorage.setItem('ars_last_pnr', booking.booking_reference)
  }

  async function handleRetrieve(event) {
    event.preventDefault()
    setError('')
    setCancelResult(null)
    setLoadingRetrieve(true)

    try {
      const data = await retrieveBooking(pnr, lastName)
      setRetrieved(data)
      localStorage.setItem('ars_last_pnr', data.booking_reference)
    } catch (err) {
      setRetrieved(null)
      setError(err?.response?.data?.detail || 'Retrieve booking failed.')
    } finally {
      setLoadingRetrieve(false)
    }
  }

  async function handleCancel(event) {
    event.preventDefault()
    setError('')
    setLoadingCancel(true)

    try {
      const data = await cancelBooking(pnr, reason)
      setCancelResult(data)
    } catch (err) {
      setCancelResult(null)
      setError(err?.response?.data?.detail || 'Cancellation failed.')
    } finally {
      setLoadingCancel(false)
    }
  }

  return (
    <main className="page">
      <section className="panel panel-hero">
        <p className="page-kicker">Booking Control</p>
        <h2>Manage Booking</h2>

        <h3>Your Current Bookings</h3>
        {loadingCurrent ? <p className="subtle">Loading your bookings...</p> : null}
        {!loadingCurrent && myBookings.length === 0 ? (
          <p className="subtle">No active upcoming bookings found. You can still retrieve by PNR below.</p>
        ) : null}
        {myBookings.length > 0 ? (
          <div className="result-list">
            {myBookings.map((booking) => (
              <article className="flight-card" key={booking.booking_reference}>
                <div className="flight-meta">
                  <p className="flight-number">PNR {booking.booking_reference}</p>
                  <p>{booking.flight_number}</p>
                  <p>
                    {booking.seat_number} | {booking.class_type} | {booking.booking_status}
                  </p>
                  <p>Departure: {new Date(booking.departure_time).toLocaleString()}</p>
                  <p>Total: INR {booking.total_amount}</p>
                </div>
                <button type="button" onClick={() => selectBooking(booking)}>
                  Select
                </button>
              </article>
            ))}
          </div>
        ) : null}

        <h3>Retrieve By PNR</h3>

        <form className="grid-form" onSubmit={handleRetrieve}>
          <label>
            PNR
            <input value={pnr} onChange={(e) => setPnr(e.target.value)} required />
          </label>

          <label>
            Last Name
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} required />
          </label>

          <button type="submit" disabled={loadingRetrieve}>
            {loadingRetrieve ? 'Retrieving...' : 'Retrieve Booking'}
          </button>
        </form>

        {retrieved ? (
          <div className="result-card">
            <p>
              {retrieved.passenger_name} | {retrieved.flight_number}
            </p>
            <p>
              Seat {retrieved.seat_number} | {retrieved.class_type} | {retrieved.booking_status}
            </p>
            <p>Total: INR {retrieved.total_amount}</p>
          </div>
        ) : null}

        <form className="grid-form" onSubmit={handleCancel}>
          <label>
            Cancellation Reason
            <input value={reason} onChange={(e) => setReason(e.target.value)} required />
          </label>

          <button type="submit" disabled={loadingCancel || !pnr}>
            {loadingCancel ? 'Cancelling...' : 'Cancel Booking'}
          </button>
        </form>

        {cancelResult ? (
          <div className="success-box">
            <p>Booking status: {cancelResult.booking_status}</p>
            <p>Refund amount: INR {cancelResult.refund_amount}</p>
            <p>Refund status: {cancelResult.refund_status}</p>
          </div>
        ) : null}

        {error ? <p className="error-msg">{error}</p> : null}
      </section>
    </main>
  )
}
