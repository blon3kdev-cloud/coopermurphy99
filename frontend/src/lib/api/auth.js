import { apiCall } from './client'

export function verifyOtp(provider, code) {
  return apiCall('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ provider, code }),
  })
}

export function register(provider) {
  return apiCall('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ provider }),
  })
}

export function logout() {
  return apiCall('/auth/logout', { method: 'POST' })
}

export function getSession() {
  return apiCall('/auth/session')
}

export function devLoginEnabled() {
  return apiCall('/auth/dev-enabled')
}

export function devLogin(code) {
  return apiCall('/auth/dev-login', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}
