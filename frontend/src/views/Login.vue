<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">Global Picker</h1>
        <p class="login-subtitle">跨平台选品比价系统</p>
      </div>

      <a-tabs v-model:activeKey="loginMode" centered>
        <a-tab-pane key="sms" tab="短信登录">
          <a-form :model="smsForm" @finish="handleSmsLogin" layout="vertical">
            <a-form-item name="phone" :rules="[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]">
              <a-input v-model:value="smsForm.phone" placeholder="请输入手机号" size="large" :maxlength="11">
                <template #prefix><MobileOutlined /></template>
              </a-input>
            </a-form-item>

            <a-form-item name="code" :rules="[{ required: true, message: '请输入验证码' }]">
              <div style="display: flex; gap: 12px;">
                <a-input v-model:value="smsForm.code" placeholder="短信验证码" size="large" :maxlength="6" style="flex: 1;">
                  <template #prefix><SafetyOutlined /></template>
                </a-input>
                <a-button
                  size="large"
                  :disabled="smsCooldown > 0 || !smsForm.phone || !/^1[3-9]\d{9}$/.test(smsForm.phone)"
                  :loading="sendingCode"
                  @click="handleSendCode('login')"
                  style="min-width: 120px;"
                >
                  {{ smsCooldown > 0 ? `${smsCooldown}s 后重发` : '获取验证码' }}
                </a-button>
              </div>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="loading" block size="large">
                登 录
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="password" tab="密码登录">
          <a-form :model="pwdForm" @finish="handlePwdLogin" layout="vertical">
            <a-form-item name="username" :rules="[{ required: true, message: '请输入手机号/用户名' }]">
              <a-input v-model:value="pwdForm.username" placeholder="手机号 / 用户名" size="large">
                <template #prefix><UserOutlined /></template>
              </a-input>
            </a-form-item>

            <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
              <a-input-password v-model:value="pwdForm.password" placeholder="密码" size="large">
                <template #prefix><LockOutlined /></template>
              </a-input-password>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="loading" block size="large">
                登 录
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>

      <div class="login-footer">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { MobileOutlined, SafetyOutlined, UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginMode = ref('sms')
const loading = ref(false)
const sendingCode = ref(false)
const smsCooldown = ref(0)

const smsForm = reactive({ phone: '', code: '' })
const pwdForm = reactive({ username: '', password: '' })

let cooldownTimer = null
function startCooldown() {
  smsCooldown.value = 60
  cooldownTimer = setInterval(() => {
    smsCooldown.value--
    if (smsCooldown.value <= 0) clearInterval(cooldownTimer)
  }, 1000)
}

async function handleSendCode(purpose) {
  sendingCode.value = true
  try {
    const res = await authApi.sendSmsCode(smsForm.phone, purpose)
    if (res?.dev_code) {
      smsForm.code = res.dev_code
      message.success('开发模式：验证码已自动填入')
    } else {
      message.success('验证码已发送')
    }
    startCooldown()
  } catch {
    // error handled by interceptor
  } finally {
    sendingCode.value = false
  }
}

async function handleSmsLogin() {
  loading.value = true
  try {
    await authStore.smsLogin(smsForm.phone, smsForm.code)
    message.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handlePwdLogin() {
  loading.value = true
  try {
    await authStore.passwordLogin(pwdForm.username, pwdForm.password)
    message.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 40px 36px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 4px;
}
.login-subtitle {
  font-size: 14px;
  color: #999;
  margin: 0;
}
.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}
.login-footer a {
  color: #667eea;
  font-weight: 600;
  margin-left: 4px;
}
</style>
