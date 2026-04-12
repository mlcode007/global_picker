import http from './request'

/** 云手机创建、健康检查等会调外部/ADB，常超过默认 15s，需单独放宽 */
const CP_LONG_MS = 180000
const CP_MEDIUM_MS = 120000

export const cloudPhoneApi = {
  getPoolStats: () => http.get('/cloud-phone/pool/stats'),
  listPool: (params) => http.get('/cloud-phone/pool/list', { params }),
  manualScale: (count) =>
    http.post('/cloud-phone/pool/scale', { count }, { timeout: CP_LONG_MS }),
  acquire: () => http.post('/cloud-phone/acquire', {}, { timeout: CP_MEDIUM_MS }),
  release: (force = false) =>
    http.post('/cloud-phone/release', { force }, { timeout: CP_MEDIUM_MS }),
  getMyPhone: () => http.get('/cloud-phone/my-phone'),
  checkHealth: (phoneId) =>
    http.get('/cloud-phone/health', {
      params: { phone_id: phoneId },
      timeout: CP_MEDIUM_MS,
    }),
  removePhone: (phoneId) =>
    http.delete(`/cloud-phone/pool/remove/${phoneId}`, { timeout: CP_MEDIUM_MS }),
  /** 远程操控页 URL，供 XingJieSdk.init({ url }) 使用 */
  getLiveUrl: (phoneId) =>
    http.get('/cloud-phone/live-url', {
      params: { phone_id: phoneId },
      timeout: CP_MEDIUM_MS,
    }),
}
