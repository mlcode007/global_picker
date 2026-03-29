<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h1 class="register-title">创建账号</h1>
        <p class="register-subtitle">Global Picker 跨平台选品比价系统</p>
      </div>

      <a-form :model="form" @finish="handleRegister" layout="vertical">
        <a-form-item label="手机号" name="phone" :rules="[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]">
          <a-input v-model:value="form.phone" placeholder="请输入手机号" size="large" :maxlength="11">
            <template #prefix><MobileOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="验证码" name="code" :rules="[{ required: true, message: '请输入验证码' }]">
          <div style="display: flex; gap: 12px;">
            <a-input v-model:value="form.code" placeholder="短信验证码" size="large" :maxlength="6" style="flex: 1;">
              <template #prefix><SafetyOutlined /></template>
            </a-input>
            <a-button
              size="large"
              :disabled="smsCooldown > 0 || !form.phone || !/^1[3-9]\d{9}$/.test(form.phone)"
              :loading="sendingCode"
              @click="handleSendCode"
              style="min-width: 120px;"
            >
              {{ smsCooldown > 0 ? `${smsCooldown}s 后重发` : '获取验证码' }}
            </a-button>
          </div>
        </a-form-item>

        <a-form-item label="公司名称" name="company_name" :rules="[{ required: true, message: '请输入公司名称' }, { min: 2, message: '公司名称至少2个字符' }]">
          <a-input v-model:value="form.company_name" placeholder="请输入公司名称" size="large">
            <template #prefix><BankOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="联系人姓名" name="contact_name">
          <a-input v-model:value="form.contact_name" placeholder="选填" size="large">
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="登录密码" name="password" extra="选填，设置后可使用密码登录">
          <a-input-password v-model:value="form.password" placeholder="选填，至少6位" size="large">
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>

        <a-form-item label="业务类型" name="business_type">
          <a-select v-model:value="form.business_type" size="large">
            <a-select-option value="cross_border">跨境电商</a-select-option>
            <a-select-option value="wholesale">批发贸易</a-select-option>
            <a-select-option value="retail">零售电商</a-select-option>
            <a-select-option value="other">其他</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="目标市场" name="target_regions">
          <a-select v-model:value="form.target_regions" mode="multiple" placeholder="选择目标市场地区" size="large">
            <a-select-option value="PH">菲律宾 (PH)</a-select-option>
            <a-select-option value="MY">马来西亚 (MY)</a-select-option>
            <a-select-option value="TH">泰国 (TH)</a-select-option>
            <a-select-option value="SG">新加坡 (SG)</a-select-option>
            <a-select-option value="ID">印度尼西亚 (ID)</a-select-option>
            <a-select-option value="VN">越南 (VN)</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block size="large">
            注 册
          </a-button>
        </a-form-item>
      </a-form>

      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { MobileOutlined, SafetyOutlined, UserOutlined, LockOutlined, BankOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const sendingCode = ref(false)
const smsCooldown = ref(0)

const form = reactive({
  phone: '',
  code: '',
  company_name: '',
  contact_name: '',
  password: '',
  business_type: 'cross_border',
  target_regions: [],
})

let cooldownTimer = null
function startCooldown() {
  smsCooldown.value = 60
  cooldownTimer = setInterval(() => {
    smsCooldown.value--
    if (smsCooldown.value <= 0) clearInterval(cooldownTimer)
  }, 1000)
}

async function handleSendCode() {
  sendingCode.value = true
  try {
    const res = await authApi.sendSmsCode(form.phone, 'register')
    if (res?.dev_code) {
      form.code = res.dev_code
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

async function handleRegister() {
  if (form.password && form.password.length < 6) {
    message.error('密码至少6位')
    return
  }
  loading.value = true
  try {
    const payload = { ...form }
    if (!payload.password) delete payload.password
    if (!payload.contact_name) delete payload.contact_name
    if (!payload.target_regions?.length) delete payload.target_regions
    await authStore.register(payload)
    message.success('注册成功')
    router.push('/')
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 0;
}
.register-card {
  width: 480px;
  padding: 40px 36px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
.register-header {
  text-align: center;
  margin-bottom: 28px;
}
.register-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 4px;
}
.register-subtitle {
  font-size: 14px;
  color: #999;
  margin: 0;
}
.register-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #666;
}
.register-footer a {
  color: #667eea;
  font-weight: 600;
  margin-left: 4px;
}
</style>
