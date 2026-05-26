import { apiCall } from './client'

export async function blikConfirmExchange(token) {
  return apiCall('/blik/confirm/exchange', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function blikConfirmSession() {
  return apiCall('/blik/confirm/session')
}

export async function blikConfirmUpload(file) {
  const fd = new FormData()
  fd.append('file', file)
  return apiCall('/blik/confirm/upload', {
    method: 'POST',
    body: fd,
  })
}
