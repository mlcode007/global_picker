<template>
  <div class="membership">
    <a-page-header title="会员中心" ghost />

    <!-- 当前会员状态 -->
    <a-card style="margin-bottom: 16px">
      <a-row :gutter="16" align="middle">
        <a-col :span="12">
          <div class="current-tier">
            <span class="tier-label">当前会员</span>
            <a-tag :color="tierColorMap[membershipStatus.tier]" class="tier-tag">
              {{ tierNameMap[membershipStatus.tier] }}
            </a-tag>
            <span v-if="membershipStatus.expires_at" class="tier-expire">
              到期时间：{{ formatDate(membershipStatus.expires_at) }}
            </span>
          </div>
        </a-col>
        <a-col :span="12">
          <div class="quota-info">
            <span>今日采集：{{ membershipStatus.quota?.today_count || 0 }} / {{ formatCollectLimit(membershipStatus.quota?.daily_limit) }}</span>
            <a-progress
              :percent="quotaPercent"
              :status="quotaPercent >= 100 ? 'exception' : 'active'"
              :stroke-color="quotaPercent >= 80 ? '#ff4d4f' : '#1677ff'"
              style="margin-top: 4px"
            />
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- 会员套餐 -->
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="8" v-for="plan in plans" :key="plan.tier">
        <a-card
          :class="['plan-card', { 'plan-card--current': plan.tier === membershipStatus.tier }]"
          hoverable
        >
          <div class="plan-header">
            <h3 class="plan-name">{{ tierNameMap[plan.tier] }}</h3>
            <div class="plan-price">
              <span class="price-amount">{{ plan.price || 0 }}</span>
              <span class="price-unit">元/月</span>
            </div>
          </div>
          <a-divider />
          <div class="plan-features">
            <div class="feature-item">
              <CheckCircleOutlined v-if="true" style="color: #52c41a; margin-right: 8px" />
              <span>每日采集 {{ formatCollectLimit(plan.daily_collect) }}</span>
            </div>
            <div class="feature-item">
              <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
              <span>拍照购 不限</span>
            </div>
            <div class="feature-item">
              <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
              <span>1688比价</span>
            </div>
            <div class="feature-item">
              <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
              <span>报表导出</span>
            </div>
            <div class="feature-item">
              <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
              <span>利润计算</span>
            </div>
            <div class="feature-item">
              <CheckCircleOutlined style="color: #52c41a; margin-right: 8px" />
              <span>数据看板</span>
            </div>
          </div>
          <a-divider />
          <a-button
            v-if="plan.tier === 'free'"
            disabled
            block
          >
            当前方案
          </a-button>
          <a-button
            v-else-if="plan.tier === membershipStatus.tier && !membershipStatus.is_expired"
            type="primary"
            block
            @click="openBuyMembership(plan.tier)"
          >
            续费
          </a-button>
          <a-button
            v-else
            type="primary"
            block
            @click="openBuyMembership(plan.tier)"
          >
            立即购买
          </a-button>
        </a-card>
      </a-col>
    </a-row>

    <!-- 云手机订阅 -->
    <a-card title="云手机订阅" style="margin-top: 16px">
      <a-row :gutter="16" align="middle">
        <a-col :span="6">
          <a-statistic title="当前订阅" :value="membershipStatus.cloud_phone_subscriptions || 0" suffix="台" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="已开通" :value="membershipStatus.cloud_phone_provisioned || 0" suffix="台" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="价格" :value="cloudPhoneInfo.price" prefix="¥" suffix="/月/台" />
        </a-col>
        <a-col :span="6">
          <a-space>
            <a-button type="primary" @click="showCloudPhoneBuy = true">
              购买云手机
            </a-button>
            <a-button @click="router.push('/cloud-phone')">前往开通</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 确认购买会员（含折扣码）弹窗 -->
    <a-modal
      v-model:open="showBuyConfirm"
      :title="`购买${tierNameMap[buyTier]}`"
      :confirm-loading="creatingOrder"
      ok-text="去支付"
      @ok="confirmBuyMembership"
      @cancel="closeBuyConfirm"
    >
      <a-form layout="vertical">
        <a-form-item label="折扣码（可选）">
          <a-space-compact style="width: 100%">
            <a-input
              v-model:value="discountCodeInput"
              placeholder="输入折扣码可享专属价格"
              allow-clear
              @change="resetDiscount"
            />
            <a-button :loading="validatingCode" @click="applyDiscountCode">应用</a-button>
          </a-space-compact>
          <div v-if="discountApplied" style="margin-top: 8px; color: #52c41a; font-size: 13px">
            ✓ 折扣码已应用，专属价 ¥{{ discountApplied.price }}
          </div>
        </a-form-item>
        <a-form-item label="应付金额">
          <div>
            <span
              v-if="discountApplied"
              style="text-decoration: line-through; color: #999; margin-right: 8px"
            >
              ¥{{ basePrice }}
            </span>
            <span style="font-size: 24px; color: #1677ff; font-weight: bold">
              ¥{{ finalPrice }}
            </span>
            <span style="color: #999; margin-left: 8px">/月</span>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 购买会员弹窗 -->
    <a-modal
      v-model:open="showPaymentModal"
      title="会员购买"
      :footer="null"
      @cancel="cancelPayment"
      width="500px"
    >
      <div v-if="!qrCodeUrl" class="payment-loading">
        <a-spin tip="生成支付二维码..." />
      </div>
      <div v-else class="qr-code-container">
        <div class="qr-code-header">
          <h3>请使用支付宝扫码支付</h3>
          <div class="payment-info">
            <span class="payment-amount">¥{{ paymentInfo.amount }}</span>
          </div>
        </div>
        <div class="qr-code-wrapper">
          <qrcode-vue :value="qrCodeUrl" :size="240" level="H" />
        </div>
        <a-alert
          :message="paymentStatusText"
          :type="paymentStatusType"
          show-icon
          style="margin-top: 16px"
        />
      </div>
    </a-modal>

    <!-- 购买云手机弹窗 -->
    <a-modal
      v-model:open="showCloudPhoneBuy"
      title="购买云手机"
      @ok="handleBuyCloudPhone"
      :confirm-loading="buyingCloudPhone"
    >
      <a-form layout="vertical">
        <a-form-item label="购买数量">
          <a-input-number v-model:value="cloudPhoneQuantity" :min="1" :max="maxBuyQuantity" />
          <div style="margin-top: 8px; color: #999; font-size: 12px">
            ¥{{ cloudPhoneInfo.price }}/月/台（开通后起算 30 天），当前已订阅 {{ membershipStatus.cloud_phone_subscriptions || 0 }} 台，最多 {{ membershipStatus.cloud_phone_max || 5 }} 台
          </div>
          <div style="margin-top: 4px; color: #999; font-size: 12px">
            续费请在「云手机管理」设备列表中对已开通设备操作；到期后需重新购买并开通。
          </div>
        </a-form-item>
        <a-form-item label="应付金额">
          <span style="font-size: 24px; color: #1677ff; font-weight: bold">
            ¥{{ cloudPhoneInfo.price * cloudPhoneQuantity }}
          </span>
          <span style="color: #999; margin-left: 8px">/月</span>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import QrcodeVue from 'qrcode.vue'
import { membershipApi } from '@/api/membership'
import { discountApi } from '@/api/discount'

const router = useRouter()

const membershipStatus = ref({
  tier: 'free',
  expires_at: null,
  is_expired: false,
  daily_collect_limit: 50,
  quota: { today_count: 0, daily_limit: 50 },
  cloud_phone_subscriptions: 0,
  cloud_phone_provisioned: 0,
  cloud_phone_available_slots: 0,
  cloud_phone_max: 5,
})
const plans = ref([])
const cloudPhoneInfo = ref({ price: 100, max: 5 })

const showPaymentModal = ref(false)
const showCloudPhoneBuy = ref(false)
const qrCodeUrl = ref('')
const paymentInfo = ref({ amount: 0, out_trade_no: '' })
const paymentStatus = ref('pending')
const buyingCloudPhone = ref(false)
const cloudPhoneQuantity = ref(1)
let queryTimer = null

// 购买确认 / 折扣码
const showBuyConfirm = ref(false)
const buyTier = ref('basic')
const discountCodeInput = ref('')
const discountApplied = ref(null)
const validatingCode = ref(false)
const creatingOrder = ref(false)

const tierNameMap = { free: '免费版', basic: '基础版', pro: '专业版' }
const tierColorMap = { free: 'default', basic: 'blue', pro: 'gold' }

const basePrice = computed(() => {
  const plan = plans.value.find((p) => p.tier === buyTier.value)
  return plan ? plan.price : 0
})

const finalPrice = computed(() => {
  if (discountApplied.value) return discountApplied.value.price
  return basePrice.value
})

const quotaPercent = computed(() => {
  const q = membershipStatus.value.quota
  if (!q || !q.daily_limit) return 0
  return Math.round((q.today_count / q.daily_limit) * 100)
})

const maxBuyQuantity = computed(() => {
  const max = membershipStatus.value.cloud_phone_max || 5
  const current = membershipStatus.value.cloud_phone_subscriptions || 0
  return Math.max(0, max - current)
})

const paymentStatusText = computed(() => {
  const map = { pending: '等待支付中...', paid: '支付成功！', closed: '订单已关闭', failed: '支付失败' }
  return map[paymentStatus.value] || '等待支付中...'
})

const paymentStatusType = computed(() => {
  const map = { pending: 'info', paid: 'success', closed: 'warning', failed: 'error' }
  return map[paymentStatus.value] || 'info'
})

function formatCollectLimit(val) {
  return (!val || val >= 999999) ? '不限' : val
}

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function fetchStatus() {
  try {
    membershipStatus.value = await membershipApi.getStatus()
  } catch (e) {
    console.error('获取会员状态失败:', e)
  }
}

async function fetchPlans() {
  try {
    const data = await membershipApi.getPlans()
    plans.value = data.plans
    cloudPhoneInfo.value = data.cloud_phone
  } catch (e) {
    console.error('获取套餐信息失败:', e)
  }
}

function openBuyMembership(tier) {
  buyTier.value = tier
  discountCodeInput.value = ''
  discountApplied.value = null
  showBuyConfirm.value = true
}

function closeBuyConfirm() {
  showBuyConfirm.value = false
}

function resetDiscount() {
  discountApplied.value = null
}

async function applyDiscountCode() {
  const code = discountCodeInput.value.trim()
  if (!code) {
    message.warning('请输入折扣码')
    return
  }
  validatingCode.value = true
  try {
    const data = await discountApi.validate(code, buyTier.value)
    discountApplied.value = data
    message.success('折扣码可用')
  } catch (e) {
    discountApplied.value = null
    const detail = e.response?.data?.detail
    message.error(detail || '折扣码无效')
  } finally {
    validatingCode.value = false
  }
}

async function confirmBuyMembership() {
  creatingOrder.value = true
  try {
    const code = discountApplied.value ? discountCodeInput.value.trim() : null
    const data = await membershipApi.createMembershipPayment(buyTier.value, code)
    showBuyConfirm.value = false
    showPaymentModal.value = true
    qrCodeUrl.value = data.qr_code
    paymentInfo.value = { amount: data.amount, out_trade_no: data.out_trade_no }
    paymentStatus.value = 'pending'
    startPaymentQuery(data.out_trade_no)
  } catch (e) {
    console.error('创建会员订单失败:', e)
    const detail = e.response?.data?.detail
    message.error(detail || '创建订单失败')
  } finally {
    creatingOrder.value = false
  }
}

async function handleBuyCloudPhone() {
  if (cloudPhoneQuantity.value < 1) {
    message.warning('请选择购买数量')
    return
  }

  buyingCloudPhone.value = true
  try {
    const data = await membershipApi.createCloudPhonePayment(cloudPhoneQuantity.value)
    showCloudPhoneBuy.value = false

    // 弹出支付二维码
    showPaymentModal.value = true
    qrCodeUrl.value = data.qr_code
    paymentInfo.value = { amount: data.amount, out_trade_no: data.out_trade_no }
    paymentStatus.value = 'pending'
    startPaymentQuery(data.out_trade_no)
  } catch (e) {
    console.error('创建云手机订单失败:', e)
    message.error('创建订单失败')
  } finally {
    buyingCloudPhone.value = false
  }
}

function startPaymentQuery(outTradeNo) {
  stopPaymentQuery()
  queryTimer = setInterval(async () => {
    try {
      const data = await membershipApi.queryPayment(outTradeNo)
      if (data.status === 'paid') {
        paymentStatus.value = 'paid'
        stopPaymentQuery()
        message.success('支付成功！')
        setTimeout(() => {
          cancelPayment()
          fetchStatus().then(() => {
            if ((membershipStatus.value.cloud_phone_available_slots || 0) > 0) {
              message.info('请前往云手机管理开通实例')
            }
          })
        }, 1500)
      } else if (data.status === 'TRADE_CLOSED') {
        paymentStatus.value = 'closed'
        stopPaymentQuery()
      }
    } catch (e) {
      console.error('查询支付状态失败:', e)
    }
  }, 3000)
}

function stopPaymentQuery() {
  if (queryTimer) {
    clearInterval(queryTimer)
    queryTimer = null
  }
}

function cancelPayment() {
  stopPaymentQuery()
  showPaymentModal.value = false
  qrCodeUrl.value = ''
  paymentStatus.value = 'pending'
}

onMounted(() => {
  fetchStatus()
  fetchPlans()
})

onUnmounted(() => {
  stopPaymentQuery()
})
</script>

<style scoped>
.plan-card {
  text-align: center;
  transition: all 0.3s;
}
.plan-card--current {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.2);
}
.plan-header {
  padding: 16px 0;
}
.plan-name {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}
.plan-price {
  color: #1677ff;
}
.price-amount {
  font-size: 36px;
  font-weight: 700;
}
.price-unit {
  font-size: 14px;
  margin-left: 4px;
}
.plan-features {
  text-align: left;
}
.feature-item {
  padding: 6px 0;
  font-size: 14px;
}
.current-tier {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tier-label {
  font-size: 16px;
  color: #666;
}
.tier-tag {
  font-size: 16px;
  padding: 4px 16px;
}
.tier-expire {
  font-size: 13px;
  color: #999;
}
.qr-code-container {
  text-align: center;
  padding: 16px 0;
}
.qr-code-header {
  margin-bottom: 16px;
}
.payment-amount {
  font-size: 28px;
  font-weight: 700;
  color: #1677ff;
}
.qr-code-wrapper {
  display: flex;
  justify-content: center;
  margin: 16px 0;
}
.payment-loading {
  text-align: center;
  padding: 40px 0;
}
</style>
