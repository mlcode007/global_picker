<template>
  <div class="activation-page">
    <div class="activation-card">
      <div class="card-header">
        <h2>兑换激活码</h2>
        <p>输入您购买的激活码，立即开通会员服务</p>
      </div>

      <div class="card-body">
        <div class="input-group">
          <label>激活码</label>
          <input
            v-model="code"
            type="text"
            placeholder="请输入激活码，如 AB3-CD4-EF5-GH6"
            class="code-input"
            @keyup.enter="redeem"
          />
        </div>

        <button
          class="redeem-btn"
          :disabled="loading || !code.trim()"
          @click="redeem"
        >
          {{ loading ? '兑换中...' : '立即兑换' }}
        </button>

        <div v-if="result" class="result-box" :class="result.success ? 'success' : 'error'">
          <div class="result-icon">{{ result.success ? '✓' : '✗' }}</div>
          <div class="result-text">{{ result.message }}</div>
          <div v-if="result.success && result.data" class="result-detail">
            <p>会员等级：{{ result.data.tier_name }}</p>
            <p>有效期至：{{ formatDate(result.data.expires_at) }}</p>
          </div>
        </div>
      </div>

      <div class="card-footer">
        <p>还没有激活码？</p>
        <a href="https://www.globalpicker.com" target="_blank" class="link">前往官网购买</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

const code = ref('')
const loading = ref(false)
const result = ref(null)

const redeem = async () => {
  if (!code.value.trim()) {
    message.warning('请输入激活码')
    return
  }

  loading.value = true
  result.value = null

  try {
    const res = await request.post('/activation/redeem', { code: code.value.trim() })
    result.value = {
      success: true,
      message: res.message || '兑换成功',
      data: res.data,
    }
    message.success(res.message || '兑换成功')
    code.value = ''
  } catch (err) {
    result.value = {
      success: false,
      message: err.response?.data?.detail || err.message || '兑换失败',
    }
    message.error(err.response?.data?.detail || '兑换失败')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}
</script>

<style scoped>
.activation-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.activation-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 480px;
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  padding: 32px;
  text-align: center;
}

.card-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
}

.card-header p {
  margin: 0;
  font-size: 14px;
  opacity: 0.9;
}

.card-body {
  padding: 32px;
}

.input-group {
  margin-bottom: 24px;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.code-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  font-family: monospace;
  letter-spacing: 1px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.code-input:focus {
  outline: none;
  border-color: #6366f1;
}

.redeem-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.redeem-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
}

.redeem-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-box {
  margin-top: 24px;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.result-box.success {
  background: #f0fdf4;
  border: 1px solid #86efac;
}

.result-box.error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
}

.result-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.result-box.success .result-icon {
  color: #16a34a;
}

.result-box.error .result-icon {
  color: #dc2626;
}

.result-text {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.result-box.success .result-text {
  color: #16a34a;
}

.result-box.error .result-text {
  color: #dc2626;
}

.result-detail {
  font-size: 14px;
  color: #666;
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
  margin-top: 12px;
}

.result-detail p {
  margin: 4px 0;
}

.card-footer {
  background: #f9fafb;
  padding: 20px 32px;
  text-align: center;
  border-top: 1px solid #e5e7eb;
}

.card-footer p {
  margin: 0 0 8px;
  font-size: 14px;
  color: #666;
}

.card-footer .link {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.card-footer .link:hover {
  text-decoration: underline;
}
</style>
