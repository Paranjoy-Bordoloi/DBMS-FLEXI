import axios from 'axios'

const PASSENGER_API_BASE_URL =
  import.meta.env.VITE_PASSENGER_API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'

const ADMIN_API_BASE_URL =
  import.meta.env.VITE_ADMIN_API_BASE_URL || 'http://localhost:8080/admin'

export const api = axios.create({
  baseURL: PASSENGER_API_BASE_URL,
  timeout: 15000,
})

export const adminApi = axios.create({
  baseURL: ADMIN_API_BASE_URL,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ars_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function saveToken(token) {
  localStorage.setItem('ars_token', token)
}

export function clearToken() {
  localStorage.removeItem('ars_token')
  localStorage.removeItem('ars_user')
}

export function getSavedUser() {
  const raw = localStorage.getItem('ars_user')
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function saveUser(user) {
  localStorage.setItem('ars_user', JSON.stringify(user))
}

export async function login(payload) {
  const response = await api.post('/auth/login', payload)
  return response.data
}

export async function register(payload) {
  const response = await api.post('/auth/register', payload)
  return response.data
}

export async function fetchMe() {
  const response = await api.get('/auth/me')
  return response.data
}

export async function searchFlights(params) {
  const response = await api.get('/flights/search', { params })
  return response.data
}

export async function fetchSeatMap(flightId, classType) {
  const response = await api.get(`/flights/${flightId}/seat-map`, {
    params: classType ? { class_type: classType } : undefined,
  })
  return response.data
}

export async function fetchAirports() {
  const response = await api.get('/airports')
  return response.data
}

export async function lockSeat(payload) {
  const response = await api.post('/bookings/seat-lock', payload)
  return response.data
}

export async function createBooking(payload) {
  const response = await api.post('/bookings', payload)
  return response.data
}

export async function retrieveBooking(pnr, lastName) {
  const response = await api.get('/bookings/retrieve', {
    params: { pnr, last_name: lastName },
  })
  return response.data
}

export async function fetchCurrentBookings() {
  const response = await api.get('/bookings/current')
  return response.data
}

export async function fetchAdminBookings(params = {}) {
  const response = await api.get('/admin/bookings', { params })
  return response.data
}

export async function cancelBooking(pnr, reason) {
  const response = await api.post(`/bookings/${pnr}/cancel`, { reason })
  return response.data
}

export async function changeBookingSeat(pnr, newSeatNumber) {
  const response = await api.post(`/bookings/${pnr}/change-seat`, {
    new_seat_number: newSeatNumber,
  })
  return response.data
}

export async function changeBookingFlight(pnr, payload) {
  const response = await api.post(`/bookings/${pnr}/change-flight`, payload)
  return response.data
}

export async function fetchAdminDashboardSummary() {
  const response = await adminApi.get('/dashboard/summary')
  return response.data
}

export async function fetchOperationsAircraftUtilization(nextDays = 14) {
  const response = await api.get('/admin/operations/utilization/aircraft', {
    params: { next_days: nextDays },
  })
  return response.data
}

export async function fetchOperationsCrewUtilization(nextDays = 14) {
  const response = await api.get('/admin/operations/utilization/crew', {
    params: { next_days: nextDays },
  })
  return response.data
}

export async function fetchOperationsAuditLogs(limit = 50) {
  const response = await api.get('/admin/operations/audit-logs', {
    params: { limit },
  })
  return response.data
}

export async function cancelFlightOperation(flightId, payload) {
  const response = await api.post(`/admin/operations/flights/${flightId}/cancel`, payload)
  return response.data
}

export async function retimeFlightOperation(flightId, payload) {
  const response = await api.post(`/admin/operations/flights/${flightId}/retime`, payload)
  return response.data
}

export async function swapAircraftOperation(flightId, payload) {
  const response = await api.post(`/admin/operations/flights/${flightId}/swap-aircraft`, payload)
  return response.data
}
