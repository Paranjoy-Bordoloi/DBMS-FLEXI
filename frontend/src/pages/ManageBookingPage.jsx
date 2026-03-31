import { useState } from 'react'
import { cancelBooking, retrieveBooking } from '../lib/api'

export default function ManageBookingPage() {
  const [pnr, setPnr] = useState(localStorage.getItem('ars_last_pnr') || '')
  const [lastName, setLastName] = useState('User')
  const [reason, setReason] = useState('Change of travel plan')
  const [retrieved, setRetrieved] = useState(null)
  const [cancelResult, setCancelResult] = useState(null)
  const [error, setError] = useState('')
  const [loadingRetrieve, setLoadingRetrieve] = useState(false)
  const [loadingCancel, setLoadingCancel] = useState(false)

  async function handleRetrieve(event) {
    event.preventDefault()
    setError('')
    setCancelResult(null)
    setLoadingRetrieve(true)

    try {
      const data = await retrieveBooking(pnr, lastName)
      setRetrieved(data)
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
      <section className="panel">
        <h2>Manage Booking</h2>

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
