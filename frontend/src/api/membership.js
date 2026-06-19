import http from './request'

export const membershipApi = {
  getStatus: () => http.get('/membership/status'),
  getPlans: () => http.get('/membership/plans'),
  createMembershipPayment: (tier, discountCode) =>
    http.post('/payment/alipay/membership', { tier, discount_code: discountCode || null }),
  createCloudPhonePayment: (quantity = 1) => http.post('/payment/alipay/cloud-phone', { quantity }),
  renewCloudPhonePayment: (phoneId) => http.post('/payment/alipay/cloud-phone/renew', { phone_id: phoneId }),
  queryPayment: (out_trade_no) => http.post('/payment/alipay/query', { out_trade_no }),
}
