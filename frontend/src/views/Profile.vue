<template>
  <div class="profile">
    <a-page-header title="个人主页" ghost />
    
    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <!-- 个人信息卡片 -->
      <a-col :xs="24" :lg="8">
        <a-card class="profile-card" hoverable>
          <template #cover>
            <div class="profile-cover">
              <a-avatar 
                :size="80" 
                :src="userInfo.avatar"
                style="border: 4px solid #fff;"
              >
                <template #icon>
                  <UserOutlined />
                </template>
              </a-avatar>
            </div>
          </template>
          <div class="profile-info">
            <h2 class="profile-name">{{ userInfo.display_name || userInfo.username || '用户' }}</h2>
            <p class="profile-company">{{ userInfo.company_name || '未设置公司' }}</p>
            <p class="profile-contact">{{ userInfo.contact_name || '未设置联系人' }}</p>
            <a-divider />
            <div class="profile-meta">
              <div class="meta-item">
                <span class="meta-label">手机号</span>
                <span class="meta-value">{{ userInfo.phone || '未设置' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">业务类型</span>
                <span class="meta-value">{{ businessTypeMap[userInfo.business_type] || '未设置' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">目标区域</span>
                <span class="meta-value">{{ userInfo.target_regions ? userInfo.target_regions.join(', ') : '未设置' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">角色</span>
                <span class="meta-value">{{ roleMap[userInfo.role] || '未设置' }}</span>
              </div>
            </div>
            <a-divider />
            <div class="profile-actions">
              <a-button type="primary" @click="editProfile">编辑资料</a-button>
            </div>
          </div>
        </a-card>
      </a-col>
      
      <!-- 积分信息卡片 -->
      <a-col :xs="24" :lg="8">
        <a-card class="points-card" hoverable>
          <a-statistic title="当前积分" :value="userPoints" prefix="分">
            <template #suffix>
              <a-button type="link" @click="showPointsDetail = true">明细</a-button>
            </template>
          </a-statistic>
          <a-divider />
          <div class="points-summary">
            <div class="points-item">
              <span class="points-label">总获取</span>
              <span class="points-value">{{ pointsDetail.total_earned }} 分</span>
            </div>
            <div class="points-item">
              <span class="points-label">总消耗</span>
              <span class="points-value">{{ pointsDetail.total_consumed }} 分</span>
            </div>
          </div>
          <a-divider />
          <div class="points-actions">
            <a-button @click="rechargePoints" type="default">积分充值</a-button>
          </div>
        </a-card>
      </a-col>
      
      <!-- 云手机信息卡片 -->
      <a-col :xs="24" :lg="8">
        <a-card class="cloud-phone-card" hoverable>
          <a-statistic title="云手机数量" :value="cloudPhoneCount" prefix="手机">
            <template #suffix>
              <a-button type="link" @click="$router.push('/cloud-phone')">管理</a-button>
            </template>
          </a-statistic>
          <a-divider />
          <div class="cloud-phone-info" v-if="myCloudPhone">
            <div class="phone-item">
              <span class="phone-label">已绑定</span>
              <span class="phone-value">{{ myCloudPhone.phone_id }}</span>
            </div>
            <div class="phone-item">
              <span class="phone-label">绑定时间</span>
              <span class="phone-value">{{ formatTime(myCloudPhone.bind_at) }}</span>
            </div>
          </div>
          <div class="cloud-phone-empty" v-else>
            <p>您还没有绑定云手机</p>
            <a-button type="primary" @click="$router.push('/cloud-phone')">获取云手机</a-button>
          </div>
        </a-card>
      </a-col>
    </a-row>
    
    <!-- 积分交易记录 -->
    <a-card class="transactions-card" style="margin-top: 16px">
      <template #title>
        <div class="card-title">
          <span>积分交易记录</span>
          <a-button type="link" @click="exportTransactions">导出记录</a-button>
        </div>
      </template>
      <a-table
        :data-source="transactions"
        :columns="transactionColumns"
        :pagination="transactionPagination"
        :loading="loading.transactions"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag :color="record.type === 'earn' ? 'green' : 'blue'">
              {{ record.type === 'earn' ? '获取' : '消耗' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'amount'">
            <span :style="{ color: record.type === 'earn' ? '#52c41a' : '#1677ff' }">
              {{ record.type === 'earn' ? '+' : '-' }}{{ record.amount }} 分
            </span>
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>
        </template>
      </a-table>
    </a-card>
    
    <!-- 支付记录 -->
    <a-card class="payment-orders-card" style="margin-top: 16px">
      <template #title>
        <div class="card-title">
          <span>支付记录</span>
        </div>
      </template>
      <a-table
        :data-source="paymentOrders"
        :columns="paymentOrderColumns"
        :pagination="paymentOrderPagination"
        :loading="loading.paymentOrders"
        row-key="id"
        @change="handlePaymentOrderPageChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="paymentStatusColorMap[record.status]">
              {{ paymentStatusMap[record.status] }}
            </a-tag>
          </template>
          <template v-if="column.key === 'amount'">
            ¥{{ record.amount }}
          </template>
          <template v-if="column.key === 'points'">
            +{{ record.points }} 分
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>
          <template v-if="column.key === 'paid_at'">
            {{ record.paid_at ? formatTime(record.paid_at) : '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-button 
              v-if="record.status === 'pending'" 
              type="link" 
              size="small" 
              @click="confirmOrderPayment(record.out_trade_no)"
            >
              确认支付
            </a-button>
            <span v-else style="color: #999">-</span>
          </template>
        </template>
      </a-table>
    </a-card>
    
    <!-- 编辑资料对话框 -->
    <a-modal
      v-model:open="showEditDialog"
      title="编辑资料"
      @ok="saveProfile"
      @cancel="showEditDialog = false"
      :confirm-loading="loading.saveProfile"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item label="姓名">
          <a-input v-model:value="editForm.display_name" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item label="公司名称">
          <a-input v-model:value="editForm.company_name" placeholder="请输入公司名称" />
        </a-form-item>
        <a-form-item label="联系人">
          <a-input v-model:value="editForm.contact_name" placeholder="请输入联系人" />
        </a-form-item>
        <a-form-item label="业务类型">
          <a-select v-model:value="editForm.business_type" placeholder="请选择业务类型">
            <a-select-option value="cross_border">跨境电商</a-select-option>
            <a-select-option value="wholesale">批发</a-select-option>
            <a-select-option value="retail">零售</a-select-option>
            <a-select-option value="other">其他</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标区域">
          <a-select v-model:value="editForm.target_regions" mode="multiple" placeholder="请选择目标区域">
            <a-select-option value="PH">菲律宾</a-select-option>
            <a-select-option value="MY">马来西亚</a-select-option>
            <a-select-option value="TH">泰国</a-select-option>
            <a-select-option value="SG">新加坡</a-select-option>
            <a-select-option value="ID">印度尼西亚</a-select-option>
            <a-select-option value="VN">越南</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="头像">
          <a-upload
            :show-upload-list="false"
            :before-upload="handleAvatarUpload"
            :custom-request="uploadAvatar"
          >
            <a-button>
              <UploadOutlined /> 上传头像
            </a-button>
          </a-upload>
          <div v-if="editForm.avatar" style="margin-top: 8px">
            <a-image :src="editForm.avatar" :width="80" :height="80" />
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
    
    <!-- 积分充值对话框 -->
    <a-modal
      v-model:open="showRechargeDialog"
      title="积分充值"
      @cancel="cancelRecharge"
      :footer="null"
      width="600px"
    >
      <div v-if="!qrCodeUrl" class="recharge-form">
        <a-form :model="rechargeForm" layout="vertical">
          <a-form-item label="充值金额（元）">
            <a-input-number 
              v-model:value="rechargeForm.amount" 
              :min="1" 
              :max="10000" 
              :step="1" 
              placeholder="请输入充值金额"
              style="width: 100%"
            />
            <div style="margin-top: 8px; color: #999; font-size: 12px">
              1元 = 1积分，最低充值1元
            </div>
          </a-form-item>
          
          <a-form-item label="快捷金额">
            <a-space wrap>
              <a-button @click="rechargeForm.amount = 10">10元</a-button>
              <a-button @click="rechargeForm.amount = 50">50元</a-button>
              <a-button @click="rechargeForm.amount = 100">100元</a-button>
              <a-button @click="rechargeForm.amount = 500">500元</a-button>
            </a-space>
          </a-form-item>
          
          <a-form-item>
            <a-button 
              type="primary" 
              @click="generateQRCode" 
              :loading="loading.recharge"
              block
              size="large"
            >
              充值
            </a-button>
          </a-form-item>
        </a-form>
      </div>
      
      <div v-else class="qr-code-container">
        <div class="qr-code-header">
          <h3>请使用支付宝扫码支付</h3>
          <div class="payment-info">
            <span class="payment-amount">¥{{ paymentInfo.amount }}</span>
            <span class="payment-points">可获得 {{ paymentInfo.points }} 积分</span>
          </div>
        </div>
        
        <div class="qr-code-wrapper">
          <qrcode-vue :value="qrCodeUrl" :size="280" level="H" />
        </div>
        
        <div class="qr-code-footer">
          <a-alert 
            :message="paymentStatusText" 
            :type="paymentStatusType"
            show-icon
            style="margin-bottom: 16px"
          />
          <a-button @click="cancelRecharge" block>
            取消支付
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { UserOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import QrcodeVue from 'qrcode.vue'
import { userApi } from '@/api/user'
import { pointsApi } from '@/api/points'
import { cloudPhoneApi } from '@/api/cloudPhone'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const userInfo = ref({})
const userPoints = ref(0)
const pointsDetail = ref({ total_earned: 0, total_consumed: 0 })
const myCloudPhone = ref(null)
const cloudPhoneCount = ref(0)
const transactions = ref([])
const paymentOrders = ref([])
const loading = ref({
  userInfo: false,
  points: false,
  cloudPhone: false,
  transactions: false,
  paymentOrders: false,
  saveProfile: false,
  recharge: false
})

const showEditDialog = ref(false)
const showRechargeDialog = ref(false)
const showPointsDetail = ref(false)

const editForm = ref({})
const rechargeForm = ref({ amount: 10 })

const qrCodeUrl = ref('')
const paymentInfo = ref({ amount: 0, points: 0, out_trade_no: '' })
const paymentStatus = ref('pending')
let queryTimer = null
let paymentRefreshTimer = null

const transactionPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

const paymentOrderPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

const paymentStatusMap = {
  pending: '待支付',
  paid: '已支付',
  closed: '已关闭',
  failed: '支付失败'
}

const paymentStatusColorMap = {
  pending: 'default',
  paid: 'success',
  closed: 'warning',
  failed: 'error'
}

const paymentOrderColumns = [
  { title: '订单号', dataIndex: 'out_trade_no', key: 'out_trade_no', width: 180 },
  { title: '支付金额', dataIndex: 'amount', key: 'amount', width: 100 },
  { title: '获得积分', dataIndex: 'points', key: 'points', width: 100 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  { title: '支付时间', dataIndex: 'paid_at', key: 'paid_at', width: 160 },
  { title: '操作', key: 'action', width: 120 },
]

const businessTypeMap = {
  cross_border: '跨境电商',
  wholesale: '批发',
  retail: '零售',
  other: '其他'
}

const roleMap = {
  admin: '管理员',
  editor: '编辑',
  viewer: '查看者'
}

const transactionColumns = [
  { title: '交易类型', dataIndex: 'type', key: 'type' },
  { title: '积分数量', dataIndex: 'amount', key: 'amount' },
  { title: '交易原因', dataIndex: 'reason', key: 'reason' },
  { title: '关联ID', dataIndex: 'related_id', key: 'related_id' },
  { title: '交易时间', dataIndex: 'created_at', key: 'created_at' }
]

const paymentStatusText = computed(() => {
  const statusMap = {
    pending: '等待支付中...',
    paid: '支付成功！',
    closed: '订单已关闭',
    failed: '支付失败'
  }
  return statusMap[paymentStatus.value] || '等待支付中...'
})

const paymentStatusType = computed(() => {
  const typeMap = {
    pending: 'info',
    paid: 'success',
    closed: 'warning',
    failed: 'error'
  }
  return typeMap[paymentStatus.value] || 'info'
})

function formatTime(iso) {
  if (!iso) return '-'  
  const d = new Date(iso)
  return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

async function fetchUserInfo() {
  loading.value.userInfo = true
  try {
    const response = await userApi.getUserInfo()
    userInfo.value = response
    editForm.value = { ...response }
  } catch (e) {
    console.error('获取用户信息失败:', e)
    message.error('获取用户信息失败')
  } finally {
    loading.value.userInfo = false
  }
}

async function fetchPointsInfo() {
  loading.value.points = true
  try {
    const response = await pointsApi.getPoints()
    userPoints.value = response.points
    pointsDetail.value = {
      total_earned: response.total_earned,
      total_consumed: response.total_consumed
    }
  } catch (e) {
    console.error('获取积分信息失败:', e)
  } finally {
    loading.value.points = false
  }
}

async function fetchCloudPhoneInfo() {
  loading.value.cloudPhone = true
  try {
    const response = await cloudPhoneApi.getMyPhone()
    if (response && response.phone_id) {
      myCloudPhone.value = response
      cloudPhoneCount.value = 1
    } else {
      myCloudPhone.value = null
      cloudPhoneCount.value = 0
    }
  } catch (e) {
    console.error('获取云手机信息失败:', e)
    myCloudPhone.value = null
    cloudPhoneCount.value = 0
  } finally {
    loading.value.cloudPhone = false
  }
}

async function fetchTransactions() {
  loading.value.transactions = true
  try {
    const params = {
      limit: transactionPagination.value.pageSize,
      offset: (transactionPagination.value.current - 1) * transactionPagination.value.pageSize
    }
    const response = await pointsApi.getTransactions(params)
    transactions.value = response
  } catch (e) {
    console.error('获取交易记录失败:', e)
    message.error('获取交易记录失败')
  } finally {
    loading.value.transactions = false
  }
}

async function fetchPaymentOrders() {
  loading.value.paymentOrders = true
  try {
    const params = {
      page: paymentOrderPagination.value.current,
      page_size: paymentOrderPagination.value.pageSize
    }
    const response = await pointsApi.getPaymentOrders(params)
    paymentOrders.value = response.orders
    paymentOrderPagination.value.total = response.total
  } catch (e) {
    console.error('获取支付记录失败:', e)
    message.error('获取支付记录失败')
  } finally {
    loading.value.paymentOrders = false
  }
}

function handlePaymentOrderPageChange(pagination) {
  paymentOrderPagination.value.current = pagination.current
  paymentOrderPagination.value.pageSize = pagination.pageSize
  fetchPaymentOrders()
}

async function confirmOrderPayment(outTradeNo) {
  try {
    const response = await pointsApi.confirmPayment(outTradeNo)
    message.success(response.msg)
    fetchPaymentOrders()
    fetchPointsInfo()
  } catch (e) {
    console.error('确认支付失败:', e)
    message.error('确认支付失败')
  }
}

function editProfile() {
  editForm.value = { ...userInfo.value }
  showEditDialog.value = true
}

async function saveProfile() {
  loading.value.saveProfile = true
  try {
    const response = await userApi.updateUserInfo(editForm.value)
    message.success('资料更新成功')
    showEditDialog.value = false
    await fetchUserInfo()
    authStore.user = userInfo.value
    localStorage.setItem('gp_user', JSON.stringify(userInfo.value))
  } catch (e) {
    console.error('更新资料失败:', e)
    message.error('更新资料失败')
  } finally {
    loading.value.saveProfile = false
  }
}

function rechargePoints() {
  qrCodeUrl.value = ''
  paymentStatus.value = 'pending'
  rechargeForm.value = { amount: 10 }
  showRechargeDialog.value = true
}

async function generateQRCode() {
  if (!rechargeForm.value.amount || rechargeForm.value.amount < 1) {
    message.warning('请输入有效的充值金额（最低1元）')
    return
  }
  
  loading.value.recharge = true
  try {
    const points = rechargeForm.value.amount
    const response = await pointsApi.createPayment(points)
    
    qrCodeUrl.value = response.qr_code
    paymentInfo.value = {
      amount: response.amount,
      points: response.points,
      out_trade_no: response.out_trade_no
    }
    
    startPaymentQuery(response.out_trade_no)
  } catch (e) {
    console.error('生成二维码失败:', e)
    message.error('生成二维码失败')
  } finally {
    loading.value.recharge = false
  }
}

function startPaymentQuery(outTradeNo) {
  stopPaymentQuery()
  
  queryTimer = setInterval(async () => {
    try {
      const response = await pointsApi.queryPayment(outTradeNo)
      
      const status = response.status
      
      if (status === 'paid') {
        paymentStatus.value = 'paid'
        stopPaymentQuery()
        message.success('支付成功！')
        
        setTimeout(() => {
          cancelRecharge()
          fetchPointsInfo()
          fetchTransactions()
          fetchPaymentOrders()
        }, 1500)
      } else if (status === 'TRADE_CLOSED') {
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

function cancelRecharge() {
  stopPaymentQuery()
  qrCodeUrl.value = ''
  paymentStatus.value = 'pending'
  showRechargeDialog.value = false
}

function exportTransactions() {
  message.info('导出功能开发中')
}

function handleAvatarUpload(file) {
  const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png'
  const isLt2M = file.size / 1024 / 1024 < 2
  
  if (!isJpgOrPng) {
    message.error('只能上传 JPG 或 PNG 图片')
    return false
  }
  if (!isLt2M) {
    message.error('图片大小不能超过 2MB')
    return false
  }
  
  return false
}

async function uploadAvatar(options) {
  editForm.value.avatar = 'https://randomuser.me/api/portraits/men/32.jpg'
  options.onSuccess()
  message.success('头像上传成功')
}

onMounted(async () => {
  await fetchUserInfo()
  await fetchPointsInfo()
  await fetchCloudPhoneInfo()
  await fetchTransactions()
  await fetchPaymentOrders()
  
  paymentRefreshTimer = setInterval(() => {
    fetchPaymentOrders()
  }, 10000)
})

onUnmounted(() => {
  stopPaymentQuery()
  if (paymentRefreshTimer) {
    clearInterval(paymentRefreshTimer)
    paymentRefreshTimer = null
  }
})
</script>

<style scoped>
.profile {
  padding: 24px;
  min-height: 100%;
}

.profile-card {
  border-radius: 10px;
  overflow: hidden;
}

.profile-cover {
  height: 120px;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  display: flex;
  justify-content: center;
  align-items: flex-end;
  padding-bottom: 16px;
}

.profile-info {
  text-align: center;
  padding: 24px;
}

.profile-name {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.profile-company {
  color: #666;
  margin-bottom: 4px;
}

.profile-contact {
  color: #999;
  margin-bottom: 16px;
}

.profile-meta {
  text-align: left;
  margin-top: 16px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.meta-label {
  color: #999;
}

.meta-value {
  color: #333;
  font-weight: 500;
}

.profile-actions {
  margin-top: 16px;
}

.points-card,
.cloud-phone-card {
  border-radius: 10px;
  height: 100%;
}

.points-summary,
.cloud-phone-info {
  text-align: left;
}

.points-item,
.phone-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.points-label,
.phone-label {
  color: #999;
}

.points-value,
.phone-value {
  color: #333;
  font-weight: 500;
}

.cloud-phone-empty {
  text-align: center;
  padding: 16px 0;
}

.cloud-phone-empty p {
  color: #999;
  margin-bottom: 16px;
}

.transactions-card {
  border-radius: 10px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recharge-form {
  padding: 16px 0;
}

.qr-code-container {
  text-align: center;
  padding: 24px 0;
}

.qr-code-header {
  margin-bottom: 24px;
}

.qr-code-header h3 {
  margin: 0 0 16px 0;
  color: #333;
}

.payment-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.payment-amount {
  font-size: 32px;
  font-weight: bold;
  color: #ff4d4f;
}

.payment-points {
  font-size: 14px;
  color: #666;
}

.qr-code-wrapper {
  display: inline-block;
  padding: 16px;
  background: #fff;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  margin-bottom: 24px;
}

.qr-code-footer {
  margin-top: 16px;
}
</style>