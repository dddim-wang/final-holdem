import axios from 'axios'

const defaultApiBase =
  typeof window === 'undefined' ? 'http://localhost:5000' : window.location.origin

export const API_BASE = import.meta.env.VITE_API_BASE || defaultApiBase

export const api = axios.create({ baseURL: API_BASE })

export function setAuth(token) {
  if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  else delete api.defaults.headers.common['Authorization']
}