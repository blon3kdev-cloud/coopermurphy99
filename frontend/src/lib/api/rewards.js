import { apiCall } from './client'

export function getVip() {
  return apiCall('/rewards/vip')
}

export function claimBonus(kind) {
  return apiCall('/rewards/vip/claim', {
    method: 'POST',
    body: JSON.stringify({ kind }),
  })
}

export function getReferral() {
  return apiCall('/rewards/referral')
}

export function claimReferralTier(tier) {
  return apiCall('/rewards/referral/claim', {
    method: 'POST',
    body: JSON.stringify({ tier }),
  })
}

export function attachReferral(ref) {
  return apiCall('/rewards/referral/attach', {
    method: 'POST',
    body: JSON.stringify({ ref }),
  })
}

export function redeemCode(code) {
  return apiCall('/rewards/redeem', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}
