import { apiCall } from './client'

export function getBalance() {
  return apiCall('/wallet/balance')
}

export function requestDeposit(payload) {
  return apiCall('/wallet/deposit', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  })
}

export function requestWithdraw(payload) {
  return apiCall('/wallet/withdraw', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  })
}
