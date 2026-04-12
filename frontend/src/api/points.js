import http from './request'

export const pointsApi = {
  getPoints: () => http.get('/points'),
  getTransactions: (params) => http.get('/points/transactions', { params }),
  checkPoints: (amount) => http.post('/points/check', { amount }),
  recharge: (amount) => http.post('/points/recharge', { amount }),
}