import axios from 'axios'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

// Create a new axios instance for each user to prevent token sharing
export function createApiInstance() {
  const instance = axios.create({ baseURL: API_BASE })
  return instance
}

export const api = createApiInstance()

export function setAuth(token) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// Function to clear auth and create fresh instance
export function clearAuth() {
  delete api.defaults.headers.common['Authorization']
  // Create a fresh API instance to ensure no cross-user contamination
  Object.assign(api, createApiInstance())
}