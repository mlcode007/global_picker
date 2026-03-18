import http from './request'

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
  getDevices: () => http.get('/pdd/photo-search/devices'),
}

export const profitApi = {
  calculate: (data) => http.post('/profit/calculate', data),
  history: (productId) => http.get(`/profit/${productId}/history`),
  exchangeRates: () => http.get('/profit/exchange-rates'),
}

export const exportApi = {
  exportExcel: (ids) => {
    const params = ids?.length ? `?ids=${ids.join(',')}` : ''
    window.open(`/api/v1/export/products${params}`, '_blank')
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
