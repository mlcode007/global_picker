import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

const TOKEN_KEY = 'gp_token'
const USER_KEY = 'gp_user'
const REFRESH_INTERVAL = 30 * 60 * 1000 // 30 分钟自动续期

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  let refreshTimer = null

  const isLoggedIn = computed(() => !!token.value)
  const displayName = computed(() => {
    if (!user.value) return ''
    return user.value.display_name || user.value.contact_name || user.value.company_name || user.value.phone || ''
  })

  function setAuth(accessToken, userInfo) {
    token.value = accessToken
    user.value = userInfo
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
  }

  function clearAuth() {
    stopAutoRefresh()
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function refreshToken() {
    try {
      const res = await authApi.refreshToken()
      if (res && res.access_token) {
        token.value = res.access_token
        localStorage.setItem(TOKEN_KEY, res.access_token)
      }
    } catch {
      // 刷新失败说明 token 已过期，清除登录状态
      clearAuth()
    }
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    refreshTimer = setInterval(refreshToken, REFRESH_INTERVAL)
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  async function smsLogin(phone, code) {
    const res = await authApi.smsLogin(phone, code)
    setAuth(res.access_token, res.user)
    startAutoRefresh()
    return res
  }

  async function passwordLogin(username, password) {
    const res = await authApi.passwordLogin(username, password)
    setAuth(res.access_token, res.user)
    startAutoRefresh()
    return res
  }

  async function register(data) {
    const res = await authApi.register(data)
    setAuth(res.access_token, res.user)
    startAutoRefresh()
    return res
  }

  async function fetchMe() {
    try {
      const userInfo = await authApi.getMe()
      user.value = userInfo
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
    } catch {
      clearAuth()
    }
  }

  function logout() {
    clearAuth()
    router.push('/login')
  }

  return {
    token,
    user,
    isLoggedIn,
    displayName,
    smsLogin,
    passwordLogin,
    register,
    fetchMe,
    logout,
    refreshToken,
    startAutoRefresh,
    stopAutoRefresh,
    setAuth,
    clearAuth,
  }
})
