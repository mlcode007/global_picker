import axios from 'axios'
import { message } from 'ant-design-vue'
import http from './request'

const TOKEN_KEY = 'gp_token'

/** 导出文件较大时延长超时；不走通用 JSON 封装，直接下载二进制 */
const exportHttp = axios.create({
  baseURL: '/api/v1',
  timeout: 300000,
})

export const productApi = {
  list: (params) => http.get('/products', { params }),
  get: (id) => http.get(`/products/${id}`),
  create: (data) => http.post('/products', data),
  batchImport: (urls) => http.post('/products/batch', { urls }),
  update: (id, data) => http.patch(`/products/${id}`, data),
  remove: (id) => http.delete(`/products/${id}`),
}

export const pddApi = {
  getMatches: (productId) => http.get(`/pdd/matches/${productId}`),
  getMatchesBatch: (productIds) => http.get('/pdd/matches/batch', { params: { product_ids: productIds.join(',') } }),
  addMatch: (data) => http.post('/pdd/matches', data),
  updateMatch: (id, data) => http.patch(`/pdd/matches/${id}`, data),
  deleteMatch: (id) => http.delete(`/pdd/matches/${id}`),
}

export const photoSearchApi = {
  createTask: (data) => http.post('/pdd/photo-search/tasks', data),
  getTask: (taskId) => http.get(`/pdd/photo-search/tasks/${taskId}`),
  getTasksByProduct: (productId) => http.get(`/pdd/photo-search/tasks/product/${productId}`),
  retryTask: (taskId) => http.post(`/pdd/photo-search/tasks/${taskId}/retry`),
  cancelTask: (taskId) => http.post(`/pdd/photo-search/tasks/${taskId}/cancel`),
  getTaskLogs: (taskId) => http.get(`/pdd/photo-search/tasks/${taskId}/logs`),
  syncTaskImages: (taskId) => http.post(`/pdd/photo-search/tasks/${taskId}/sync-images`),
  getDevices: () => http.get('/pdd/photo-search/devices'),
}

export const profitApi = {
  calculate: (data) => http.post('/profit/calculate', data),
  history: (productId) => http.get(`/profit/${productId}/history`),
  exchangeRates: () => http.get('/profit/exchange-rates'),
}

function parseFilenameFromContentDisposition(cd) {
  if (!cd || typeof cd !== 'string') return 'tiktok_products.xlsx'
  const m = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"|filename=([^;\s]+)/i.exec(cd)
  const raw = m ? (m[1] || m[2] || m[3]) : null
  if (!raw) return 'tiktok_products.xlsx'
  try {
    return decodeURIComponent(raw.replace(/"/g, '').trim())
  } catch {
    return raw.replace(/"/g, '').trim()
  }
}

export const exportApi = {
  /**
   * @param {number[]|null} productIds 所选商品 ID；与 options.exportAll 二选一
   * @param {string[]|null|undefined} fields 字段 key；传 null/undefined 表示后端默认全部列
   * @param {{ exportAll?: boolean }} [options] exportAll 为 true 时导出当前账号全部商品
   */
  async exportProductsExcel(productIds, fields, options = {}) {
    const { exportAll = false } = options
    const token = localStorage.getItem(TOKEN_KEY)
    const headers = {}
    if (token) headers.Authorization = `Bearer ${token}`
    const body = exportAll
      ? { export_all: true, fields: fields ?? null }
      : { product_ids: productIds, fields: fields ?? null }
    try {
      const res = await exportHttp.post(
        '/export/products',
        body,
        { responseType: 'blob', headers },
      )
      const blob = res.data
      const cd = res.headers['content-disposition']
      const filename = parseFilenameFromContentDisposition(cd)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      message.success('导出成功，文件已开始下载')
    } catch (err) {
      const status = err.response?.status
      const data = err.response?.data

      if (status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem('gp_user')
        const path = window.location.pathname
        if (path !== '/login' && path !== '/register') {
          message.warning('登录已过期，请重新登录')
          window.location.href = '/login'
        }
        throw err
      }

      if (data instanceof Blob) {
        try {
          const text = await data.text()
          const j = JSON.parse(text)
          const detail = j.detail
          const msg = typeof detail === 'string'
            ? detail
            : (Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (j.message || '导出失败'))
          message.error(msg)
        } catch {
          message.error('导出失败')
        }
      } else {
        message.error(err.message || '导出失败')
      }
      throw err
    }
  },
}

export const taskApi = {
  queryBatch: (ids) => http.get('/tasks', { params: { ids: ids.join(',') } }),
  get: (id) => http.get(`/tasks/${id}`),
  retry: (id) => http.post(`/tasks/${id}/retry`),
}

export const settingsApi = {
  getConfig: () => http.get('/settings/crawl'),
  updateCookies: (cookies) => http.post('/settings/crawl/cookies', { tiktok_cookies: cookies }),
  updateProxy: (proxy) => http.post('/settings/crawl/proxy', { tiktok_proxy: proxy }),
  clearCookies: () => http.delete('/settings/crawl/cookies'),
}

export const dashboardApi = {
  getStats: () => http.get('/dashboard/stats'),
}
