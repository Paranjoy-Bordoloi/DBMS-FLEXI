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

export async function cancelBooking(pnr, reason) {
  const response = await api.post(`/bookings/${pnr}/cancel`, { reason })
  return response.data
}

export async function fetchAdminDashboardSummary() {
  const response = await adminApi.get('/dashboard/summary')
  return response.data
}
