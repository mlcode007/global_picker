import axios from 'axios'
import { message } from 'ant-design-vue'

const TOKEN_KEY = 'gp_token'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  res => {
    const data = res.data
    if (data.code !== 0 && data.code !== -1) {
      message.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data.data
  },
  err => {
    const status = err.response?.status
    const rawDetail = err.response?.data?.detail
    const serverMsg = err.response?.data?.message
      || (typeof rawDetail === 'string' ? rawDetail : undefined)

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('gp_user')
      const currentPath = window.location.pathname
      if (currentPath !== '/login' && currentPath !== '/register') {
        message.warning('登录已过期，请重新登录')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }

    // 网关错误：多为上游 API 未启动、崩溃或反向代理配置错误
    if (status === 502 || status === 503 || status === 504) {
      message.error(
        '无法连接后端服务（网关 ' +
          status +
          '）。本地开发请确认已启动 API（如 uvicorn 监听 :8000）且与前端代理一致；线上环境请检查 Nginx/容器与健康检查。',
      )
      return Promise.reject(err)
    }

    if (status === 409) {
      const e = new Error(serverMsg || '资源已存在')
      e.status = 409
      return Promise.reject(e)
    }

    const isTimeout =
      err.code === 'ECONNABORTED' ||
      (typeof err.message === 'string' && err.message.toLowerCase().includes('timeout'))
    if (isTimeout) {
      message.error('请求超时，请稍后重试（云手机创建或检查耗时较长）')
      return Promise.reject(err)
    }

    if (!status && err.message === 'Network Error') {
      message.error('网络异常或后端未响应，请确认服务已启动后再试')
      return Promise.reject(err)
    }

    message.error(serverMsg || err.message || '网络错误')
    return Promise.reject(err)
  }
)

export default http
