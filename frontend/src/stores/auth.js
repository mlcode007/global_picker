import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

const TOKEN_KEY = 'gp_token'
const USER_KEY = 'gp_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

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
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function smsLogin(phone, code) {
    const res = await authApi.smsLogin(phone, code)
    setAuth(res.access_token, res.user)
    return res
  }

  async function passwordLogin(username, password) {
    const res = await authApi.passwordLogin(username, password)
    setAuth(res.access_token, res.user)
    return res
  }

  async function register(data) {
    const res = await authApi.register(data)
    setAuth(res.access_token, res.user)
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
    setAuth,
    clearAuth,
  }
})
