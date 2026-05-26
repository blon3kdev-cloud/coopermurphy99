import { apiCall } from './client'

export function getSiteStatus() {
  return apiCall('/site/status')
}
