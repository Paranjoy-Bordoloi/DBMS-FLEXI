import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchFlights } from '../lib/api'

export default function SearchPage() {
  const navigate = useNavigate()
  const [originCode, setOriginCode] = useState('PNQ')
  const [destinationCode, setDestinationCode] = useState('DEL')
  const [travelDate, setTravelDate] = useState('2026-03-15')
  const [sortBy, setSortBy] = useState('price')
  const [sortOrder, setSortOrder] = useState('asc')
  const [flights, setFlights] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSearch(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await searchFlights({
        origin_code: originCode,
        destination_code: destinationCode,
        travel_date: travelDate,
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      setFlights(data)
    } catch (err) {
      setFlights([])
      setError(err?.response?.data?.detail || 'Failed to fetch flights.')
    } finally {
      setLoading(false)
    }
  }

  function handleSelectFlight(flightId) {
    localStorage.setItem('ars_selected_flight_id', String(flightId))
    navigate('/book')
  }

  return (
    <main className="page">
      <section className="panel">
        <h2>Flight Search</h2>
        <form className="grid-form" onSubmit={handleSearch}>
          <label>
            Origin
            <input
              value={originCode}
              onChange={(e) => setOriginCode(e.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>

          <label>
            Destination
            <input
              value={destinationCode}
              onChange={(e) => setDestinationCode(e.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>

          <label>
            Travel Date
            <input
              type="date"
              value={travelDate}
              onChange={(e) => setTravelDate(e.target.value)}
              required
            />
          </label>

          <label>
            Sort By
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="price">Price</option>
              <option value="duration">Duration</option>
            </select>
          </label>

          <label>
            Order
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </label>

          <button type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search Flights'}
          </button>
        </form>

        {error ? <p className="error-msg">{error}</p> : null}
      </section>

      <section className="panel">
        <h3>Results</h3>
        {flights.length === 0 ? (
          <p className="subtle">No flights yet. Run a search.</p>
        ) : (
          <div className="result-list">
            {flights.map((flight) => (
              <article className="flight-card" key={flight.flight_id}>
                <div>
                  <p className="flight-number">{flight.flight_number}</p>
                  <p>
                    {flight.origin_code} to {flight.destination_code}
                  </p>
                  <p>
                    Departs: {new Date(flight.departure_time).toLocaleString()}
                  </p>
                  <p>Price: INR {flight.price}</p>
                  <p>Available Seats: {flight.available_seats}</p>
                </div>
                <button type="button" onClick={() => handleSelectFlight(flight.flight_id)}>
                  Select Flight
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
