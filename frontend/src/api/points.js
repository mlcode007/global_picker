import http from './request'

export const pointsApi = {
  getPoints: () => http.get('/points'),
  getTransactions: (params) => http.get('/points/transactions', { params }),
  checkPoints: (amount) => http.post('/points/check', { amount }),
  recharge: (amount) => http.post('/points/recharge', { amount }),
  createPayment: (points) => http.post('/payment/alipay/create', { points }),
  queryPayment: (out_trade_no) => http.post('/payment/alipay/query', { out_trade_no }),
  getPaymentOrders: (params) => http.get('/payment/orders', { params }),
  confirmPayment: (out_trade_no) => http.post('/payment/confirm', { out_trade_no }),
}