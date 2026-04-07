import { useEffect, useState } from 'react'
import {
  cancelBooking,
  changeBookingFlight,
  changeBookingSeat,
  fetchCurrentBookings,
  retrieveBooking,
} from '../lib/api'

export default function ManageBookingPage() {
  const [pnr, setPnr] = useState(localStorage.getItem('ars_last_pnr') || '')
  const [lastName, setLastName] = useState('')
  const [reason, setReason] = useState('Change of travel plan')
  const [myBookings, setMyBookings] = useState([])
  const [retrieved, setRetrieved] = useState(null)
  const [cancelResult, setCancelResult] = useState(null)
  const [serviceResult, setServiceResult] = useState(null)
  const [newSeatNumber, setNewSeatNumber] = useState('')
  const [newFlightId, setNewFlightId] = useState('')
  const [newFlightSeat, setNewFlightSeat] = useState('')
  const [error, setError] = useState('')
  const [loadingCurrent, setLoadingCurrent] = useState(true)
  const [loadingRetrieve, setLoadingRetrieve] = useState(false)
  const [loadingCancel, setLoadingCancel] = useState(false)
  const [loadingChangeSeat, setLoadingChangeSeat] = useState(false)
  const [loadingChangeFlight, setLoadingChangeFlight] = useState(false)

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
    setServiceResult(null)
    setNewSeatNumber(booking.seat_number || '')
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

  async function handleChangeSeat(event) {
    event.preventDefault()
    if (!pnr || !newSeatNumber.trim()) {
      setError('Select a booking and enter a seat number.')
      return
    }

    setError('')
    setLoadingChangeSeat(true)
    setServiceResult(null)
    try {
      const data = await changeBookingSeat(pnr, newSeatNumber.trim().toUpperCase())
      setServiceResult(data)
      const refreshed = await retrieveBooking(pnr, lastName)
      setRetrieved(refreshed)
      setMyBookings((prev) =>
        prev.map((row) =>
          row.booking_reference === pnr
            ? {
                ...row,
                seat_number: refreshed.seat_number,
                total_amount: refreshed.total_amount,
              }
            : row,
        ),
      )
    } catch (err) {
      setError(err?.response?.data?.detail || 'Seat change failed.')
    } finally {
      setLoadingChangeSeat(false)
    }
  }

  async function handleChangeFlight(event) {
    event.preventDefault()
    if (!pnr || !newFlightId.trim()) {
      setError('Select a booking and enter the target flight ID.')
      return
    }

    setError('')
    setLoadingChangeFlight(true)
    setServiceResult(null)
    try {
      const data = await changeBookingFlight(pnr, {
        new_flight_id: Number(newFlightId),
        ...(newFlightSeat.trim() ? { new_seat_number: newFlightSeat.trim().toUpperCase() } : {}),
      })
      setServiceResult(data)
      const refreshed = await retrieveBooking(pnr, lastName)
      setRetrieved(refreshed)
      setMyBookings((prev) =>
        prev.map((row) =>
          row.booking_reference === pnr
            ? {
                ...row,
                flight_number: refreshed.flight_number,
                seat_number: refreshed.seat_number,
                departure_time: refreshed.departure_time,
                total_amount: refreshed.total_amount,
              }
            : row,
        ),
      )
    } catch (err) {
      setError(err?.response?.data?.detail || 'Flight change failed.')
    } finally {
      setLoadingChangeFlight(false)
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

        <h3>Trip Service Actions</h3>
        <form className="grid-form" onSubmit={handleChangeSeat}>
          <label>
            New Seat Number
            <input
              value={newSeatNumber}
              onChange={(e) => setNewSeatNumber(e.target.value.toUpperCase())}
              placeholder="For example 14C"
              required
            />
          </label>
          <button type="submit" disabled={loadingChangeSeat || !pnr}>
            {loadingChangeSeat ? 'Updating...' : 'Change Seat'}
          </button>
        </form>

        <form className="grid-form" onSubmit={handleChangeFlight}>
          <label>
            New Flight ID
            <input value={newFlightId} onChange={(e) => setNewFlightId(e.target.value)} required />
          </label>
          <label>
            Preferred New Seat (optional)
            <input value={newFlightSeat} onChange={(e) => setNewFlightSeat(e.target.value.toUpperCase())} />
          </label>
          <button type="submit" disabled={loadingChangeFlight || !pnr}>
            {loadingChangeFlight ? 'Rebooking...' : 'Change Flight'}
          </button>
        </form>

        {serviceResult ? (
          <div className="success-box">
            <p>{serviceResult.message}</p>
            <p>Additional amount: INR {serviceResult.additional_amount}</p>
            <p>Updated total: INR {serviceResult.updated_total_amount}</p>
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
