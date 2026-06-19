import http from './request'

export const discountApi = {
  // 用户：校验折扣码，返回调整后价格
  validate: (code, tier) => http.post('/discount/validate', { code, tier }),

  // 管理员：折扣码管理
  list: (tier) => http.get('/discount/admin/codes', { params: tier ? { tier } : {} }),
  create: (payload) => http.post('/discount/admin/codes', payload),
  update: (id, payload) => http.put(`/discount/admin/codes/${id}`, payload),
  remove: (id) => http.delete(`/discount/admin/codes/${id}`),
}
