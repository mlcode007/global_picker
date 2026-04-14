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
      @ok="confirmRecharge"
      @cancel="showRechargeDialog = false"
      :confirm-loading="loading.recharge"
    >
      <a-form :model="rechargeForm" layout="vertical">
        <a-form-item label="充值金额">
          <a-input-number v-model:value="rechargeForm.amount" :min="100" :step="100" placeholder="请输入充值金额" />
          <div style="margin-top: 8px; color: #999; font-size: 12px">
            1元 = 100积分
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { UserOutlined, UploadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
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
const loading = ref({
  userInfo: false,
  points: false,
  cloudPhone: false,
  transactions: false,
  saveProfile: false,
  recharge: false
})

const showEditDialog = ref(false)
const showRechargeDialog = ref(false)
const showPointsDetail = ref(false)

const editForm = ref({})
const rechargeForm = ref({ amount: 100 })

const transactionPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

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
    // 假设后端返回 total，这里简化处理
    // transactionPagination.value.total = response.total
  } catch (e) {
    console.error('获取交易记录失败:', e)
    message.error('获取交易记录失败')
  } finally {
    loading.value.transactions = false
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
    // 更新 authStore 中的用户信息
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
  showRechargeDialog.value = true
}

async function confirmRecharge() {
  if (!rechargeForm.value.amount || rechargeForm.value.amount <= 0) {
    message.warning('请输入有效的充值金额')
    return
  }
  
  loading.value.recharge = true
  try {
    const response = await pointsApi.recharge(rechargeForm.value.amount)
    message.success('充值成功')
    showRechargeDialog.value = false
    await fetchPointsInfo()
    await fetchTransactions()
  } catch (e) {
    console.error('充值失败:', e)
    message.error('充值失败')
  } finally {
    loading.value.recharge = false
  }
}

function exportTransactions() {
  // 导出交易记录的逻辑
  message.info('导出功能开发中')
}

function handleAvatarUpload(file) {
  // 验证文件类型和大小
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
  
  return false // 阻止默认上传，使用 custom-request
}

async function uploadAvatar(options) {
  // 这里应该实现图片上传逻辑
  // 简化处理，直接设置一个示例头像
  editForm.value.avatar = 'https://randomuser.me/api/portraits/men/32.jpg'
  options.onSuccess()
  message.success('头像上传成功')
}

onMounted(async () => {
  await fetchUserInfo()
  await fetchPointsInfo()
  await fetchCloudPhoneInfo()
  await fetchTransactions()
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
</style>