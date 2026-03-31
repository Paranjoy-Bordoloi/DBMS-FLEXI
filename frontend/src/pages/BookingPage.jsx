import { useEffect, useMemo, useState } from 'react'
import { createBooking, fetchMe, lockSeat } from '../lib/api'

export default function BookingPage() {
  const [me, setMe] = useState(null)
  const [flightId, setFlightId] = useState(localStorage.getItem('ars_selected_flight_id') || '1')
  const [seatNumber, setSeatNumber] = useState('15A')
  const [classType, setClassType] = useState('Economy')
  const [paymentMethod, setPaymentMethod] = useState('UPI')
  const [transactionReference, setTransactionReference] = useState(`TXN-${Date.now()}`)
  const [taxAmount, setTaxAmount] = useState('500')
  const [serviceCharge, setServiceCharge] = useState('150')
  const [lockResult, setLockResult] = useState(null)
  const [bookingResult, setBookingResult] = useState(null)
  const [error, setError] = useState('')
  const [loadingLock, setLoadingLock] = useState(false)
  const [loadingBooking, setLoadingBooking] = useState(false)

  useEffect(() => {
    let active = true
    fetchMe()
      .then((data) => {
        if (active) {
          setMe(data)
        }
      })
      .catch(() => {
        if (active) {
          setError('Session expired. Please login again.')
        }
      })
    return () => {
      active = false
    }
  }, [])

  const userId = useMemo(() => me?.user_id || '', [me])
  const passengerId = useMemo(() => me?.passenger_id || '', [me])

  async function handleSeatLock(event) {
    event.preventDefault()
    if (!userId) {
      setError('User not loaded. Please refresh page.')
      return
    }

    setError('')
    setLoadingLock(true)
    setLockResult(null)

    try {
      const result = await lockSeat({
        user_id: Number(userId),
        flight_id: Number(flightId),
        seat_number: seatNumber,
        lock_minutes: 10,
      })
      setLockResult(result)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Seat lock failed.')
    } finally {
      setLoadingLock(false)
    }
  }

  async function handleCreateBooking(event) {
    event.preventDefault()
    if (!userId || !passengerId) {
      setError('User profile missing passenger information.')
      return
    }

    setError('')
    setLoadingBooking(true)
    setBookingResult(null)

    try {
      const result = await createBooking({
        passenger_id: Number(passengerId),
        user_id: Number(userId),
        flight_id: Number(flightId),
        seat_number: seatNumber,
        class_type: classType,
        payment_method: paymentMethod,
        transaction_reference: transactionReference,
        tax_amount: Number(taxAmount),
        service_charge: Number(serviceCharge),
      })
      setBookingResult(result)
      localStorage.setItem('ars_last_pnr', result.booking_reference)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Booking failed.')
    } finally {
      setLoadingBooking(false)
    }
  }

  return (
    <main className="page">
      <section className="panel">
        <h2>Create Booking</h2>
        <p className="subtle">
          Signed in as {me?.email || 'loading...'} | User ID: {userId || '-'} | Passenger ID: {passengerId || '-'}
        </p>

        <form className="grid-form" onSubmit={handleSeatLock}>
          <label>
            Flight ID
            <input value={flightId} onChange={(e) => setFlightId(e.target.value)} required />
          </label>

          <label>
            Seat Number
            <input value={seatNumber} onChange={(e) => setSeatNumber(e.target.value.toUpperCase())} required />
          </label>

          <button type="submit" disabled={loadingLock}>
            {loadingLock ? 'Locking...' : '1. Lock Seat'}
          </button>
        </form>

        {lockResult ? (
          <p className="success-msg">
            Seat locked until {new Date(lockResult.expires_at).toLocaleTimeString()}
          </p>
        ) : null}

        <form className="grid-form" onSubmit={handleCreateBooking}>
          <label>
            Class Type
            <select value={classType} onChange={(e) => setClassType(e.target.value)}>
              <option value="Economy">Economy</option>
              <option value="Business">Business</option>
              <option value="First">First</option>
            </select>
          </label>

          <label>
            Payment Method
            <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="UPI">UPI</option>
              <option value="CreditCard">Credit Card</option>
              <option value="DebitCard">Debit Card</option>
              <option value="NetBanking">Net Banking</option>
              <option value="Wallet">Wallet</option>
            </select>
          </label>

          <label>
            Transaction Reference
            <input
              value={transactionReference}
              onChange={(e) => setTransactionReference(e.target.value)}
              required
            />
          </label>

          <label>
            Tax Amount
            <input type="number" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} min="0" />
          </label>

          <label>
            Service Charge
            <input type="number" value={serviceCharge} onChange={(e) => setServiceCharge(e.target.value)} min="0" />
          </label>

          <button type="submit" disabled={loadingBooking}>
            {loadingBooking ? 'Booking...' : '2. Confirm Booking'}
          </button>
        </form>

        {error ? <p className="error-msg">{error}</p> : null}
        {bookingResult ? (
          <div className="success-box">
            <p>Booking Created</p>
            <p>PNR: {bookingResult.booking_reference}</p>
            <p>Booking ID: {bookingResult.booking_id}</p>
            <p>Total: INR {bookingResult.total_amount}</p>
          </div>
        ) : null}
      </section>
    </main>
  )
}
