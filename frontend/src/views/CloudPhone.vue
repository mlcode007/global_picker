<template>
  <div class="cloud-phone">
    <a-page-header title="云手机管理" ghost>
      <template #extra>
        <a-tag color="blue" style="margin-right: 16px;">积分: {{ userPoints }}</a-tag>
        <a-button v-if="myPhone" @click="showReleaseDialog = true" danger>释放云手机</a-button>
        <a-button @click="refresh" :loading="refreshing">刷新</a-button>
      </template>
    </a-page-header>

    <!-- 统计卡片 -->
    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :lg="8">
        <a-card class="stat-card" hoverable>
          <a-statistic title="云手机总数" :value="stats?.total || 0">
            <template #prefix><PhoneOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card class="stat-card" hoverable>
          <a-statistic title="可用数量" :value="stats?.available || 0" value-style="color: #3f8600">
            <template #prefix><CheckCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card class="stat-card" hoverable>
          <a-statistic title="不可用数量" :value="stats?.offline || 0" value-style="color: #cf1322">
            <template #prefix><FireOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 设备实时画面 -->
    <a-card class="live-section" style="margin-top: 16px">
      <template #title>
        <div class="live-title">
          <DesktopOutlined style="margin-right: 8px" />
          <span>设备实时画面</span>
          <a-tag v-if="availableDevices.length" color="success" style="margin-left: 12px">
            {{ availableDevices.length }} 台在线
          </a-tag>
        </div>
      </template>
      <template #extra>
        <a-space>
          <a-button size="small" @click="refreshLiveUrls" :loading="liveUrlLoading">
            <ReloadOutlined /> 刷新画面
          </a-button>
          <a-dropdown>
            <a-button size="small">
              <QuestionCircleOutlined /> 帮助
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item>
                  <a href="https://www.chinac.com/docs/help/anc/content/open/WebSDK" target="_blank">Web SDK 文档</a>
                </a-menu-item>
                <a-menu-item>
                  <a href="https://console.chinac.com/front/JsSdk/index.html" target="_blank">官方示例</a>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-space>
      </template>

      <!-- 加载中 -->
      <div v-if="initialLoading" class="live-loading">
        <a-spin size="large">
          <template #tip>
            <div style="margin-top: 16px; color: #8c8c8c">正在加载设备列表...</div>
          </template>
        </a-spin>
      </div>

      <!-- 无设备 -->
      <div v-else-if="poolList.length === 0" class="live-empty">
        <a-empty description="暂无云手机设备">
          <a-button type="primary" @click="manualScale(1)">创建云手机</a-button>
        </a-empty>
      </div>

      <!-- 无可用设备 -->
      <div v-else-if="availableDevices.length === 0" class="live-empty">
        <a-empty description="当前没有可用设备，请检查设备状态或稍后重试" />
      </div>

      <!-- 设备网格 -->
      <div v-else class="live-grid">
        <div
          v-for="device in availableDevices"
          :key="device.phone_id"
          class="device-card"
          :class="{ 'device-card--loading': liveUrlLoading && !liveUrlByPhone[device.phone_id] }"
        >
          <div class="device-header">
            <div class="device-info">
              <span class="device-name">{{ device.phone_name || device.phone_id }}</span>
              <a-tag :color="getStatusColor(device.status)" size="small">
                {{ getStatusText(device.status) }}
              </a-tag>
            </div>
            <div class="device-actions">
              <a-tooltip title="放大操控">
                <a-button
                  type="text"
                  size="small"
                  @click="openEnlarge(device.phone_id)"
                  :disabled="!liveUrlByPhone[device.phone_id] || enlargeOpening"
                  :loading="openingPhoneId === device.phone_id"
                >
                  <ExpandOutlined />
                </a-button>
              </a-tooltip>
            </div>
          </div>

          <div
            class="device-screen"
            :class="{ 'device-screen--blocked': enlargeOpening }"
            @click="!enlargeOpening && openEnlarge(device.phone_id)"
          >
            <div v-if="liveUrlLoading && !liveUrlByPhone[device.phone_id]" class="screen-loading">
              <a-spin tip="获取直播地址..." />
            </div>
            <div v-else-if="!liveUrlByPhone[device.phone_id]" class="screen-error">
              <ExclamationCircleOutlined style="font-size: 32px; color: #faad14" />
              <span>无法获取直播地址</span>
              <a-button size="small" type="link" @click.stop="retryLiveUrl(device.phone_id)">重试</a-button>
            </div>
            <template v-else>
              <div
                :id="previewContainerId(device.phone_id)"
                class="screen-player"
              />
              <div class="screen-overlay">
                <div class="overlay-hint">
                  <ExpandOutlined style="font-size: 32px" />
                  <span>点击进入操控</span>
                </div>
              </div>
            </template>
          </div>

          <div class="device-footer">
            <span class="device-id">{{ device.phone_id }}</span>
            <a-button
              type="primary"
              size="small"
              @click="openEnlarge(device.phone_id)"
              :disabled="!liveUrlByPhone[device.phone_id] || enlargeOpening"
              :loading="openingPhoneId === device.phone_id"
            >
              进入操控
            </a-button>
          </div>
        </div>
      </div>
    </a-card>

    <!-- 云手机池列表 -->
    <a-card title="云手机池" class="pool-list-card" style="margin-top: 16px">
      <template #extra>
        <a-space>
          <a-input-search v-model:value="poolSearch" placeholder="搜索手机ID" style="width: 200px" />
          <a-button type="primary" @click="manualScale(1)">扩容1台</a-button>
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
          <template v-if="column.key === 'created_at'">
            {{ formatTime(record.created_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="openEnlarge(record.phone_id)"
                :disabled="!isAvailableStatus(record.status) || enlargeOpening"
                :loading="openingPhoneId === record.phone_id"
              >
                操控
              </a-button>
              <a-button type="link" size="small" @click="checkPhoneHealth(record.phone_id)">检查</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 放大远程操控 Modal -->
    <a-modal
      v-model:open="liveModalOpen"
      :title="enlargedPhoneId ? `远程操控 — ${enlargedPhoneId}` : '远程操控'"
      width="min(480px, 96vw)"
      :footer="null"
      destroy-on-close
      centered
      @cancel="closeEnlarge"
    >
      <div class="modal-player-wrap">
        <div id="xingjie-modal-play" class="modal-player" />
      </div>
    </a-modal>

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
      :footer="null"
    >
      <a-descriptions v-if="healthInfo" bordered :column="1">
        <a-descriptions-item label="手机ID">{{ healthInfo.phone_id }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="healthInfo.is_healthy ? 'success' : 'error'">
            {{ healthInfo.is_healthy ? '正常' : '异常' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item v-if="healthInfo.status" label="具体状态">
          <a-tag :color="getStatusColor(healthInfo.status)">
            {{ getStatusText(healthInfo.status) }}
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  PhoneOutlined,
  CheckCircleOutlined,
  CheckCircleFilled,
  FireOutlined,
  DesktopOutlined,
  ReloadOutlined,
  QuestionCircleOutlined,
  ExpandOutlined,
  ExclamationCircleOutlined,
  MobileOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { cloudPhoneApi } from '@/api/cloudPhone'
import { pointsApi } from '@/api/points'
import {
  loadChinacJsSdk,
  createSdkInstance,
  destroySdkInstance,
  destroyChinacSdk,
  initChinacPlayer,
} from '@/utils/chinacWebSdk'

/** 每设备独立 SDK 实例；全局 XingJieSdk 单例只能绑一个 iframe */
const previewSdks = new Map()
let modalSdk = null

function destroyAllPreviewSdks() {
  previewSdks.forEach((sdk) => destroySdkInstance(sdk))
  previewSdks.clear()
}

/** 仅移除某一设备的列表预览（进入大屏时只应停这一路，其它设备继续播） */
function destroyPreviewSdkForPhone(phoneId) {
  const sdk = previewSdks.get(phoneId)
  if (sdk) {
    destroySdkInstance(sdk)
    previewSdks.delete(phoneId)
  }
  const host = document.getElementById(previewContainerId(phoneId))
  if (host) host.innerHTML = ''
}

function destroyModalSdkOnly() {
  destroySdkInstance(modalSdk)
  modalSdk = null
}

const stats = ref({})
const myPhone = ref(null)
const poolList = ref([])
const userPoints = ref(0)
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
const refreshing = ref(false)
const initialLoading = ref(true)

const liveUrlByPhone = ref({})
const liveUrlLoading = ref(false)
const liveModalOpen = ref(false)
const enlargedPhoneId = ref(null)
/** 防止连续点击重复进入弹窗 / 并发 init */
const enlargeOpening = ref(false)
const openingPhoneId = ref(null)
const closeEnlargeBusy = ref(false)

let pollingInterval = null

const availableDevices = computed(() =>
  poolList.value.filter((p) => isAvailableStatus(p.status)),
)

const poolColumns = [
  { title: '手机ID', dataIndex: 'phone_id', key: 'phone_id', width: 180 },
  { title: '状态', key: 'status', width: 100 },
  { title: '实例类型', dataIndex: 'instance_type', key: 'instance_type', width: 120 },
  { title: 'ADB端口', dataIndex: 'adb_host_port', key: 'adb_host_port', width: 150 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function getStatusColor(status) {
  const map = {
    available: 'success', ok: 'success',
    bound: 'processing',
    offline: 'default', off: 'default',
    maintenance: 'warning',
    deleted: 'error', del: 'error',
    adb_timeout: 'warning', timeout: 'warning', timeo: 'warning', to: 'warning',
  }
  return map[status] || 'default'
}

function isAvailableStatus(status) {
  return status === 'available' || status === 'ok'
}

function getStatusText(status) {
  const map = {
    available: '可用', ok: '可用',
    bound: '已绑定',
    offline: '离线', off: '离线',
    maintenance: '维护中',
    deleted: '已删除', del: '已删除',
    adb_timeout: 'ADB超时', timeout: 'ADB超时', timeo: 'ADB超时', to: 'ADB超时',
  }
  return map[status] || status
}

async function fetchPoolListOnly() {
  try {
    const params = {
      page: poolPagination.value.current,
      page_size: poolPagination.value.pageSize,
    }
    if (poolSearch.value) params.search = poolSearch.value

    const response = await cloudPhoneApi.listPool(params)
    if (response && response.items) {
      poolList.value = response.items
      poolPagination.value.total = response.total || 0
    }
  } catch (e) {
    console.error('加载云手机池列表失败:', e)
  }
}

async function hydrateLiveUrls() {
  const avail = poolList.value.filter((p) => isAvailableStatus(p.status))
  if (avail.length === 0) {
    liveUrlByPhone.value = {}
    return
  }

  liveUrlLoading.value = true
  try {
    const results = await Promise.allSettled(
      avail.map(async (p) => {
        const data = await cloudPhoneApi.getLiveUrl(p.phone_id)
        return { phoneId: p.phone_id, url: data?.url || null }
      }),
    )

    const urls = {}
    for (const r of results) {
      if (r.status === 'fulfilled' && r.value.url) {
        urls[r.value.phoneId] = r.value.url
      }
    }
    liveUrlByPhone.value = urls
  } catch (e) {
    console.error('获取直播地址失败:', e)
  } finally {
    liveUrlLoading.value = false
  }
}

function previewContainerId(phoneId) {
  return `preview-${String(phoneId).replace(/[^a-zA-Z0-9_-]/g, '_')}`
}

async function initPreviewPlayers() {
  if (liveModalOpen.value) return

  const list = availableDevices.value
  const urls = liveUrlByPhone.value

  if (list.length === 0 || Object.keys(urls).length === 0) return

  try {
    await loadChinacJsSdk()
    if (typeof window !== 'undefined' && !window.XingJieSdkObj) {
      console.error('XingJieSdkObj 不存在，无法多路预览')
      return
    }
  } catch (e) {
    console.error('加载 SDK 失败:', e)
    return
  }

  destroyAllPreviewSdks()
  await nextTick()
  for (const device of list) {
    const h = document.getElementById(previewContainerId(device.phone_id))
    if (h) h.innerHTML = ''
  }

  await nextTick()
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

  for (const device of list) {
    const url = urls[device.phone_id]
    if (!url) continue

    const containerId = previewContainerId(device.phone_id)
    const host = document.getElementById(containerId)
    if (!host) continue

    const w = Math.floor(host.getBoundingClientRect().width)
    const displayWidth = w > 0 ? w : 360

    try {
      const sdk = createSdkInstance()
      previewSdks.set(device.phone_id, sdk)
      await initChinacPlayer(sdk, containerId, url, {
        deviceId: device.phone_id,
        displayWidth,
        resolution: '720P',
        mute: true,
        autoConnect: true,
        showBottomBar: false,
      })
    } catch (e) {
      console.error('init preview player', device.phone_id, e)
    }
  }
}

/** 仅恢复某一设备的列表预览（关闭大屏后补回这一路，不重刷其它设备） */
async function initSinglePreviewPlayer(phoneId) {
  if (liveModalOpen.value) return

  const url = liveUrlByPhone.value[phoneId]
  if (!url) return
  if (!availableDevices.value.some((d) => d.phone_id === phoneId)) return
  if (previewSdks.has(phoneId)) return

  try {
    await loadChinacJsSdk()
    if (typeof window !== 'undefined' && !window.XingJieSdkObj) return
  } catch {
    return
  }

  const containerId = previewContainerId(phoneId)
  const host = document.getElementById(containerId)
  if (!host) return

  const w = Math.floor(host.getBoundingClientRect().width)
  const displayWidth = w > 0 ? w : 360

  try {
    const sdk = createSdkInstance()
    previewSdks.set(phoneId, sdk)
    await initChinacPlayer(sdk, containerId, url, {
      deviceId: phoneId,
      displayWidth,
      resolution: '720P',
      mute: true,
      autoConnect: true,
      showBottomBar: false,
    })
  } catch (e) {
    console.error('init single preview player', phoneId, e)
  }
}

async function refreshLiveUrls() {
  await hydrateLiveUrls()
  await nextTick()
  await initPreviewPlayers()
}

async function retryLiveUrl(phoneId) {
  try {
    const data = await cloudPhoneApi.getLiveUrl(phoneId)
    if (data?.url) {
      liveUrlByPhone.value = { ...liveUrlByPhone.value, [phoneId]: data.url }
      await nextTick()
      await initPreviewPlayers()
    } else {
      message.warning('仍无法获取直播地址')
    }
  } catch {
    message.error('获取直播地址失败')
  }
}

async function openEnlarge(phoneId) {
  if (enlargeOpening.value) return
  if (liveModalOpen.value && enlargedPhoneId.value === phoneId) return

  let url = liveUrlByPhone.value[phoneId]

  if (!url) {
    message.loading({ content: '正在获取直播地址...', key: 'liveUrl' })
    try {
      const data = await cloudPhoneApi.getLiveUrl(phoneId)
      url = data?.url
      if (url) {
        liveUrlByPhone.value = { ...liveUrlByPhone.value, [phoneId]: url }
      }
    } catch {
      // ignore
    }
    message.destroy('liveUrl')
  }

  if (!url) {
    message.warning('该设备暂无远程操控地址')
    return
  }

  enlargeOpening.value = true
  openingPhoneId.value = phoneId
  try {
    destroyPreviewSdkForPhone(phoneId)
    destroyModalSdkOnly()

    enlargedPhoneId.value = phoneId
    liveModalOpen.value = true

    await nextTick()

    try {
      await loadChinacJsSdk()
    } catch (e) {
      message.error('加载 SDK 失败')
      enlargedPhoneId.value = null
      liveModalOpen.value = false
      await nextTick()
      await initSinglePreviewPlayer(phoneId)
      return
    }

    const host = document.getElementById('xingjie-modal-play')
    if (host) host.innerHTML = ''

    await nextTick()

    try {
      modalSdk = createSdkInstance()
      await initChinacPlayer(modalSdk, 'xingjie-modal-play', url, {
        deviceId: phoneId,
        displayWidth: 0,
        resolution: '720P',
        mute: false,
        autoConnect: true,
        showBottomBar: true,
      })
    } catch (e) {
      console.error('init modal player', e)
      message.error('加载大屏操控失败')
      enlargedPhoneId.value = null
      liveModalOpen.value = false
      await nextTick()
      await initSinglePreviewPlayer(phoneId)
    }
  } finally {
    enlargeOpening.value = false
    openingPhoneId.value = null
  }
}

async function closeEnlarge() {
  if (closeEnlargeBusy.value) return
  closeEnlargeBusy.value = true
  try {
    const closedId = enlargedPhoneId.value
    destroyModalSdkOnly()
    const host = document.getElementById('xingjie-modal-play')
    if (host) host.innerHTML = ''
    enlargedPhoneId.value = null
    liveModalOpen.value = false

    await nextTick()
    if (closedId) await initSinglePreviewPlayer(closedId)
  } finally {
    closeEnlargeBusy.value = false
  }
}

async function fetchStats() {
  try {
    const [statsRes, myPhoneRes, pointsRes] = await Promise.allSettled([
      cloudPhoneApi.getPoolStats(),
      cloudPhoneApi.getMyPhone(),
      pointsApi.getPoints(),
    ])

    if (statsRes.status === 'fulfilled') stats.value = statsRes.value || {}
    if (myPhoneRes.status === 'fulfilled' && myPhoneRes.value?.phone_id) {
      myPhone.value = myPhoneRes.value
    } else {
      myPhone.value = null
    }
    if (pointsRes.status === 'fulfilled' && pointsRes.value?.points !== undefined) {
      userPoints.value = pointsRes.value.points
    }
  } catch (e) {
    console.error('加载统计数据失败:', e)
  }
}

async function refresh() {
  refreshing.value = true
  try {
    await fetchStats()
    await fetchPoolListOnly()
    await hydrateLiveUrls()
    await nextTick()
    await initPreviewPlayers()
    message.success('刷新成功')
  } finally {
    refreshing.value = false
  }
}

async function releasePhone() {
  try {
    await cloudPhoneApi.release()
    message.success('云手机已释放')
    showReleaseDialog.value = false
    await fetchStats()
  } catch (e) {
    console.error('释放云手机失败:', e)
    message.error('释放云手机失败')
  }
}

async function checkPhoneHealth(phoneId) {
  let targetPhoneId = phoneId
  if (phoneId && typeof phoneId === 'object' && phoneId.target) {
    targetPhoneId = myPhone.value?.phone_id
  }

  healthInfo.value = null
  showHealthDialog.value = true

  try {
    const response = await cloudPhoneApi.checkHealth(targetPhoneId)
    if (response) {
      healthInfo.value = response
    }
  } catch (e) {
    console.error('检查云手机状态失败:', e)
    message.error('检查云手机状态失败')
    showHealthDialog.value = false
  }
}

async function manualScale(count) {
  const requiredPoints = 100 * count
  if (userPoints.value < requiredPoints) {
    message.warning(`积分不足，扩容 ${count} 台云手机需要 ${requiredPoints} 积分`)
    return
  }

  try {
    await cloudPhoneApi.manualScale(count)
    message.success(`成功扩容 ${count} 台云手机，已扣除 ${requiredPoints} 积分`)
    await refresh()
  } catch (e) {
    console.error('扩容云手机失败:', e)
    message.error('扩容云手机失败')
  }
}

onMounted(async () => {
  initialLoading.value = true
  try {
    await fetchStats()
    await fetchPoolListOnly()
    await hydrateLiveUrls()
  } finally {
    initialLoading.value = false
  }

  await nextTick()
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
  await initPreviewPlayers()

  pollingInterval = setInterval(async () => {
    if (liveModalOpen.value) return
    await fetchStats()
  }, 30000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
  destroyAllPreviewSdks()
  destroyModalSdkOnly()
  destroyChinacSdk()
})
</script>

<style scoped>
.cloud-phone {
  padding: 24px;
  min-height: 100%;
  background: #f5f7fa;
}

.stat-card {
  text-align: center;
  border-radius: 8px;
}

.live-section {
  border-radius: 12px;
}

.live-title {
  display: flex;
  align-items: center;
  font-weight: 600;
}

.live-loading,
.live-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.live-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.device-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.device-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.device-card--loading {
  opacity: 0.7;
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-name {
  font-weight: 600;
  font-size: 14px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-actions .ant-btn {
  color: rgba(255, 255, 255, 0.85);
}

.device-actions .ant-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.device-screen {
  width: 100%;
  height: 400px;
  background: #1a1a2e;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.device-screen--blocked {
  cursor: wait;
  pointer-events: none;
}

.screen-loading,
.screen-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #8c8c8c;
  font-size: 13px;
}

.screen-player {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.screen-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.screen-overlay:hover {
  background: rgba(0, 0, 0, 0.4);
}

.screen-overlay:hover .overlay-hint {
  opacity: 1;
}

.overlay-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #fff;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.3s;
}

.device-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}

.device-id {
  font-size: 11px;
  color: #8c8c8c;
  font-family: 'Monaco', 'Menlo', monospace;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pool-list-card {
  border-radius: 12px;
  min-height: 400px;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player-wrap {
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.modal-player {
  width: 100%;
  min-height: 640px;
}

.loading-health {
  display: flex;
  justify-content: center;
  padding: 48px;
}
</style>
