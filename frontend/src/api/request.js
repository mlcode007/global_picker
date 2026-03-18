import axios from 'axios'
import { message } from 'ant-design-vue'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.response.use(
  res => {
    const data = res.data
    if (data.code !== 0) {
      message.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data.data
  },
  err => {
    const status = err.response?.status
    const serverMsg = err.response?.data?.message || err.response?.data?.detail

    // 409 重复冲突：不弹全局错误，抛出带 status 的 Error 让调用方处理
    if (status === 409) {
      const e = new Error(serverMsg || '资源已存在')
      e.status = 409
      return Promise.reject(e)
    }

    message.error(serverMsg || err.message || '网络错误')
    return Promise.reject(err)
  }
)

export default http
