<template>
  <div class="cloud-phone">
    <a-page-header title="云手机管理" ghost>
      <template #extra>
        <a-button v-if="myPhone" @click="showReleaseDialog = true" danger>释放云手机</a-button>
        <a-button v-else type="primary" @click="acquirePhone" :loading="acquiring">获取云手机</a-button>
        <a-button @click="refresh">刷新</a-button>
      </template>
    </a-page-header>
    
    <!-- 统计卡片 -->
    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :lg="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="云手机总数" :value="stats?.total || 0">
            <template #prefix><PhoneOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="可用数量" :value="stats?.available || 0" value-style="color: #3f8600">
            <template #prefix><CheckCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="已绑定" :value="stats?.bound || 0" value-style="color: #1677ff">
            <template #prefix><DisconnectOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card class="stat-card" hoverable>
          <a-statistic title="离线数量" :value="stats?.offline || 0" value-style="color: #cf1322">
            <template #prefix><FireOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>
    
    <!-- 我的云手机 -->
    <a-card title="我的云手机" class="my-phone-card" style="margin-top: 16px">
      <div v-if="myPhone" class="my-phone-content">
        <div class="phone-info">
          <div class="phone-id">
            <PhoneOutlined style="color: #1677ff; font-size: 24px; margin-right: 8px" />
            <span class="id-text">{{ myPhone.phone_id }}</span>
          </div>
          <div class="phone-meta">
            <a-tag color="processing">已绑定</a-tag>
            <span class="bind-time">绑定时间: {{ formatTime(myPhone.bind_at) }}</span>
          </div>
        </div>
        <div class="phone-actions">
          <a-button type="primary" @click="checkPhoneHealth">检查状态</a-button>
          <a-button @click="showReleaseDialog = true" danger>释放</a-button>
        </div>
      </div>
      <div v-else class="no-phone">
        <DisconnectOutlined style="font-size: 48px; color: #d9d9d9; margin-bottom: 16px" />
        <p class="empty-text">您还没有绑定云手机</p>
        <a-button type="primary" @click="acquirePhone" :loading="acquiring">
          <template #icon><PhoneOutlined /></template>
          获取云手机
        </a-button>
      </div>
    </a-card>
    
    <!-- 云手机池列表 -->
    <a-card title="云手机池" class="pool-list-card" style="margin-top: 16px">
      <template #extra>
        <a-space>
          <a-input-search v-model:value="poolSearch" placeholder="搜索手机ID" style="width: 200px" />
          <a-button @click="manualScale(1)">扩容1台</a-button>
          <a-button @click="recoverOffline" type="default">恢复离线</a-button>
        </a-space>
      </template>
      
      <a-table
        :data-source="poolList"
        :columns="poolColumns"
        :pagination="poolPagination"
        :loading="poolLoading"
        :scroll="{ x: 800 }"
        row-key="phone_id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-button type="link" size="small" @click="checkPhoneHealth(record.phone_id)">检查</a-button>
          </template>
        </template>
      </a-table>
    </a-card>
    
    <!-- 释放确认对话框 -->
    <a-modal
      v-model:open="showReleaseDialog"
      title="释放云手机"
      @ok="releasePhone"
      @cancel="showReleaseDialog = false"
      :confirm-loading="releasing"
    >
      <p>确定要释放云手机 <strong>{{ myPhone?.phone_id }}</strong> 吗？</p>
      <p style="color: #cf1322; margin-top: 16px;">
        ⚠️ 释放后将失去对该云手机的控制权，且可能需要重新排队获取。
      </p>
    </a-modal>
    
    <!-- 健康检查对话框 -->
    <a-modal
      v-model:open="showHealthDialog"
      title="云手机状态"
      @cancel="showHealthDialog = false"
      width="500px"
    >
      <a-descriptions v-if="healthInfo" bordered :column="1">
        <a-descriptions-item label="手机ID">{{ healthInfo.phone_id }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="healthInfo.is_healthy ? 'success' : 'error'">
            {{ healthInfo.is_healthy ? '正常' : '异常' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="检查时间">{{ formatTime(new Date()) }}</a-descriptions-item>
      </a-descriptions>
      <div v-else class="loading-health">
        <a-spin tip="检查中..." />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  PhoneOutlined,
  CheckCircleOutlined,
  FireOutlined,
  DisconnectOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { cloudPhoneApi } from '@/api/cloudPhone'

const stats = ref({})
const myPhone = ref(null)
const poolList = ref([])
const poolLoading = ref(false)
const poolSearch = ref('')
const poolPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
})

const showReleaseDialog = ref(false)
const showHealthDialog = ref(false)
const releasing = ref(false)
const healthInfo = ref(null)

const acquiring = computed(() => false)
const releasingComputed = computed(() => releasing.value)

const poolColumns = [
  { title: '手机ID', dataIndex: 'phone_id', key: 'phone_id', width: 180 },
  { title: '状态', key: 'status', width: 100 },
  { title: '实例类型', dataIndex: 'instance_type', key: 'instance_type', width: 120 },
  { title: '规格', key: 'spec', width: 200 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 80, fixed: 'right' },
]

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getStatusColor(status) {
  const map = {
    available: 'success',
    bound: 'processing',
    offline: 'error',
    maintenance: 'warning',
  }
  return map[status] || 'default'
}

function getStatusText(status) {
  const map = {
    available: '可用',
    bound: '已绑定',
    offline: '离线',
    maintenance: '维护中',
  }
  return map[status] || status
}

async function fetchStats() {
  try {
    const statsResponse = await cloudPhoneApi.getPoolStats()
    stats.value = statsResponse || {}
    
    try {
      const myPhoneResponse = await cloudPhoneApi.getMyPhone()
      if (myPhoneResponse && myPhoneResponse.phone_id) {
        myPhone.value = myPhoneResponse
      } else {
        myPhone.value = null
        message.warning('您还没有绑定云手机')
      }
    } catch (e) {
      myPhone.value = null
    }
    
    await fetchPoolList()
  } catch (e) {
    console.error('加载云手机数据失败:', e)
    message.error('加载云手机数据失败')
  }
}

async function fetchPoolList() {
  try {
    const params = { 
      page: poolPagination.value.current, 
      page_size: poolPagination.value.pageSize 
    }
    if (poolSearch.value) params.search = poolSearch.value
    
    const response = await cloudPhoneApi.listPool(params)
    if (response && response.items) {
      poolList.value = response.items
      poolPagination.value.total = response.total || 0
    }
  } catch (e) {
    console.error('加载云手机池列表失败:', e)
    message.error('加载云手机池列表失败')
  }
}

async function refresh() {
  await fetchStats()
  message.success('刷新成功')
}

async function acquirePhone() {
  try {
    // 先检查用户是否已有云手机
    if (myPhone.value) {
      message.warning('您已经绑定了云手机，无法再次获取')
      return
    }
    
    const response = await cloudPhoneApi.acquire()
    if (response && response.phone_id) {
      message.success('云手机分配成功')
      await fetchStats()
    } else {
      message.warning('云手机资源紧张，请稍后再试')
    }
  } catch (e) {
    console.error('获取云手机失败:', e)
    message.error('获取云手机失败')
  }
}

async function releasePhone() {
  try {
    const response = await cloudPhoneApi.release()
    message.success('云手机已释放')
    showReleaseDialog.value = false
    await fetchStats()
  } catch (e) {
    console.error('释放云手机失败:', e)
    message.error('释放云手机失败')
  }
}

async function checkPhoneHealth(phoneId) {
  try {
    const response = await cloudPhoneApi.checkHealth(phoneId || myPhone.value?.phone_id)
    if (response) {
      healthInfo.value = response
      showHealthDialog.value = true
    }
  } catch (e) {
    console.error('检查云手机状态失败:', e)
    message.error('检查云手机状态失败')
  }
}

async function manualScale(count) {
  try {
    const response = await cloudPhoneApi.manualScale(count)
    message.success(`成功扩容 ${count} 台云手机`)
    await fetchStats()
  } catch (e) {
    console.error('扩容云手机失败:', e)
    message.error('扩容云手机失败')
  }
}

async function recoverOffline() {
  try {
    const response = await cloudPhoneApi.recover()
    message.success('恢复成功')
    await fetchStats()
  } catch (e) {
    console.error('恢复云手机失败:', e)
    message.error('恢复云手机失败')
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.cloud-phone {
  padding: 24px;
  min-height: 100%;
}

.stat-card {
  text-align: center;
}

.my-phone-card {
  text-align: center;
}

.my-phone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px;
}

.phone-info {
  margin-bottom: 24px;
}

.phone-id {
  font-size: 24px;
  font-weight: bold;
  color: #1677ff;
  margin-bottom: 12px;
}

.id-text {
  font-family: 'Courier New', monospace;
}

.phone-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.bind-time {
  color: #8c8c8c;
}

.phone-actions {
  display: flex;
  gap: 12px;
}

.no-phone {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px 24px;
}

.empty-text {
  color: #8c8c8c;
  margin-bottom: 24px;
  font-size: 16px;
}

.pool-list-card {
  min-height: 400px;
}

.loading-health {
  display: flex;
  justify-content: center;
  padding: 48px;
}
</style>
