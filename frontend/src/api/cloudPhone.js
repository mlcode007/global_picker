import http from './request'

export const cloudPhoneApi = {
  getPoolStats: () => http.get('/cloud-phone/pool/stats'),
  listPool: (params) => http.get('/cloud-phone/pool/list', { params }),
  manualScale: (count) => http.post('/cloud-phone/pool/scale', { count }),
  acquire: () => http.post('/cloud-phone/acquire'),
  release: (force = false) => http.post('/cloud-phone/release', { force }),
  getMyPhone: () => http.get('/cloud-phone/my-phone'),
  recoverOffline: () => http.post('/cloud-phone/recover'),
  checkHealth: (phoneId) => http.get('/cloud-phone/health', { params: { phone_id: phoneId } }),
}
