import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
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

export async function fetchMe() {
  const response = await api.get('/auth/me')
  return response.data
}

export async function searchFlights(params) {
  const response = await api.get('/flights/search', { params })
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

export async function cancelBooking(pnr, reason) {
  const response = await api.post(`/bookings/${pnr}/cancel`, { reason })
  return response.data
}
