import { useEffect, useMemo, useState } from 'react'
import { createBooking, fetchMe, fetchSeatMap, lockSeat } from '../lib/api'

export default function BookingPage() {
  const [me, setMe] = useState(null)
  const [flightId, setFlightId] = useState(localStorage.getItem('ars_selected_flight_id') || '1')
  const [seatNumber, setSeatNumber] = useState('15A')
  const [randomAllotment, setRandomAllotment] = useState(false)
  const [useSeatLock, setUseSeatLock] = useState(false)
  const [classType, setClassType] = useState('Economy')
  const [paymentMethod, setPaymentMethod] = useState('UPI')
  const [transactionReference, setTransactionReference] = useState(`TXN-${Date.now()}`)
  const [taxAmount, setTaxAmount] = useState('500')
  const [serviceCharge, setServiceCharge] = useState('150')
  const [lockResult, setLockResult] = useState(null)
  const [seatMap, setSeatMap] = useState([])
  const [loadingSeatMap, setLoadingSeatMap] = useState(false)
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

  useEffect(() => {
    let active = true

    async function loadSeatMap() {
      if (!flightId || randomAllotment) {
        if (active) {
          setSeatMap([])
        }
        return
      }

      setLoadingSeatMap(true)
      try {
        const data = await fetchSeatMap(Number(flightId), classType)
        if (active) {
          setSeatMap(data?.seats || [])
        }
      } catch (err) {
        if (active) {
          setSeatMap([])
          setError(err?.response?.data?.detail || 'Could not load seat map.')
        }
      } finally {
        if (active) {
          setLoadingSeatMap(false)
        }
      }
    }

    loadSeatMap()
    return () => {
      active = false
    }
  }, [flightId, classType, randomAllotment])

  const userId = useMemo(() => me?.user_id || '', [me])
  const passengerId = useMemo(() => me?.passenger_id || '', [me])

  async function handleSeatLock(event) {
    event.preventDefault()
    if (!userId) {
      setError('User not loaded. Please refresh page.')
      return
    }

    if (randomAllotment) {
      setError('Seat lock is not available when random allotment is enabled.')
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

    if (!randomAllotment && !seatNumber.trim()) {
      setError('Seat number is required when random allotment is disabled.')
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
        seat_number: randomAllotment ? null : seatNumber,
        class_type: classType,
        payment_method: paymentMethod,
        transaction_reference: transactionReference,
        tax_amount: Number(taxAmount),
        service_charge: Number(serviceCharge),
        random_allotment: randomAllotment,
        use_seat_lock: useSeatLock,
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
      <section className="panel booking-hero">
        <p className="page-kicker">Reservation Workspace</p>
        <h2>Book Ticket</h2>
        <p className="subtle">
          Signed in as {me?.email || 'loading...'} | User ID: {userId || '-'} | Passenger ID: {passengerId || '-'}
        </p>
        <p className="subtle">Seat lock is optional and adds INR 200 convenience charge.</p>
      </section>

      <section className="panel">
        <h3>Seat Selection Mode</h3>
        <div className="toggle-row">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={randomAllotment}
              onChange={(e) => {
                setRandomAllotment(e.target.checked)
                if (e.target.checked) {
                  setUseSeatLock(false)
                  setLockResult(null)
                }
              }}
            />
            Random seat allotment from available seats
          </label>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={useSeatLock}
              onChange={(e) => setUseSeatLock(e.target.checked)}
              disabled={randomAllotment}
            />
            Use seat locking (+ INR 200)
          </label>
        </div>
      </section>

      <section className="panel">
        <h3>Optional Lock Step</h3>
        <form className="grid-form" onSubmit={handleSeatLock}>
          <label>
            Flight ID
            <input value={flightId} onChange={(e) => setFlightId(e.target.value)} required />
          </label>

          <label>
            Seat Number
            <input
              value={seatNumber}
              onChange={(e) => setSeatNumber(e.target.value.toUpperCase())}
              disabled={randomAllotment}
              required={!randomAllotment}
            />
          </label>

          <button type="submit" disabled={loadingLock || !useSeatLock || randomAllotment}>
            {loadingLock ? 'Locking...' : '1. Lock Seat'}
          </button>
        </form>

        {lockResult ? (
          <p className="success-msg">
            Seat locked until {new Date(lockResult.expires_at).toLocaleTimeString()}
          </p>
        ) : null}
      </section>

      <section className="panel">
        <h3>Payment & Confirmation</h3>
        <form className="grid-form" onSubmit={handleCreateBooking}>
          <label>
            Flight ID
            <input value={flightId} onChange={(e) => setFlightId(e.target.value)} required />
          </label>

          <label>
            Seat Number
            <input
              value={randomAllotment ? 'AUTO-ASSIGNED' : seatNumber}
              onChange={(e) => setSeatNumber(e.target.value.toUpperCase())}
              disabled={randomAllotment}
              required={!randomAllotment}
            />
          </label>

          <label>
            Class Type
            <select
              value={classType}
              onChange={(e) => {
                setClassType(e.target.value)
                if (!randomAllotment) {
                  setSeatNumber('')
                }
              }}
            >
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

        {!randomAllotment ? (
          <div className="seat-map-panel">
            <p className="subtle">Seat map ({classType})</p>
            {loadingSeatMap ? <p className="subtle">Loading seats...</p> : null}
            {!loadingSeatMap ? (
              <div className="seat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(54px, 1fr))', gap: '8px' }}>
                {seatMap
                  .filter((seat) => seat.cabin_class === classType)
                  .map((seat) => {
                    const unavailable = seat.status !== 'Available'
                    const selected = seatNumber === seat.seat_number
                    return (
                      <button
                        key={seat.seat_number}
                        type="button"
                        disabled={unavailable}
                        onClick={() => setSeatNumber(seat.seat_number)}
                        style={{
                          padding: '8px 6px',
                          borderRadius: '8px',
                          border: selected ? '2px solid #1b5e20' : '1px solid #b7c3d0',
                          background: unavailable ? '#f3f5f7' : selected ? '#d7f5df' : '#ffffff',
                          color: unavailable ? '#8b95a1' : '#1d2a35',
                        }}
                        title={`${seat.seat_number} • ${seat.seat_type} • ${seat.status}`}
                      >
                        {seat.seat_number}
                      </button>
                    )
                  })}
              </div>
            ) : null}
          </div>
        ) : null}

        {useSeatLock ? <p className="subtle">Lock surcharge will be included in total fare.</p> : null}

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
