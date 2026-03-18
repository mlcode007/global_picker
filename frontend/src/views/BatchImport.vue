<template>
  <a-row :gutter="16">
    <!-- 批量导入 -->
    <a-col :span="14">
      <a-card title="批量导入 TikTok 商品链接" :bordered="false">
        <a-alert
          message="每行一个 TikTok 商品链接，支持一次导入多条"
          type="info" show-icon style="margin-bottom:16px"
        />
        <a-textarea
          v-model:value="urlsText"
          :rows="14"
          placeholder="https://shop.tiktok.com/view/product/xxx?region=PH&#10;https://shop.tiktok.com/view/product/yyy?region=MY&#10;..."
          style="font-family:monospace;font-size:13px"
        />
        <div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center">
          <span style="color:#999">共 {{ urlCount }} 条链接</span>
          <a-space>
            <a-button @click="urlsText = ''">清空</a-button>
            <a-button type="primary" :loading="importing" :disabled="!urlCount" @click="doImport">
              <ImportOutlined /> 开始导入
            </a-button>
          </a-space>
        </div>
      </a-card>

      <!-- 单条添加 -->
      <a-card title="单条添加" :bordered="false" style="margin-top:16px">
        <a-form :model="singleForm" layout="vertical" @finish="doSingle">
          <a-row :gutter="12">
            <a-col :span="24">
              <a-form-item label="TikTok 链接" required>
                <a-input v-model:value="singleForm.tiktok_url" placeholder="https://shop.tiktok.com/view/product/..." />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="商品标题">
                <a-input v-model:value="singleForm.title" placeholder="可选，自动抓取后覆盖" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="价格">
                <a-input-number v-model:value="singleForm.price" :min="0" :precision="2" style="width:100%" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="货币">
                <a-select v-model:value="singleForm.currency" style="width:100%">
                  <a-select-option value="PHP">PHP</a-select-option>
                  <a-select-option value="MYR">MYR</a-select-option>
                  <a-select-option value="THB">THB</a-select-option>
                  <a-select-option value="SGD">SGD</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="区域">
                <a-select v-model:value="singleForm.region" style="width:100%">
                  <a-select-option v-for="(v, k) in REGION_MAP" :key="k" :value="k">{{ k }} - {{ v }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="18">
              <a-form-item label="备注">
                <a-input v-model:value="singleForm.remark" placeholder="可选" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-button type="primary" html-type="submit" :loading="singleLoading">添加商品</a-button>
        </a-form>
      </a-card>
    </a-col>

    <!-- 右：导出 & 结果反馈 -->
    <a-col :span="10">
      <a-card title="报表导出" :bordered="false">
        <a-descriptions :column="1" size="small">
          <a-descriptions-item label="格式">Excel (.xlsx)</a-descriptions-item>
          <a-descriptions-item label="包含字段">
            商品信息、TikTok 价格、拼多多对比价、利润、利润率、选品状态
          </a-descriptions-item>
        </a-descriptions>
        <a-divider />
        <a-space direction="vertical" style="width:100%">
          <a-button type="primary" block @click="exportApi.exportExcel()">
            <DownloadOutlined /> 导出全部商品
          </a-button>
          <a-button block @click="router.push('/products')">
            <FilterOutlined /> 前往列表筛选后导出
          </a-button>
        </a-space>
      </a-card>

      <!-- 采集进度面板 -->
      <a-card v-if="taskList.length" title="采集进度" :bordered="false" style="margin-top:16px">
        <div style="margin-bottom:12px;display:flex;align-items:center;gap:12px">
          <a-progress
            :percent="crawlPercent"
            :status="crawlProgressStatus"
            style="flex:1"
          />
          <span style="font-size:12px;color:#666;white-space:nowrap">
            {{ doneCount }}/{{ taskList.length }} 完成
          </span>
        </div>
        <div class="task-list">
          <div v-for="task in taskList" :key="task.id" class="task-row">
            <component
              :is="statusIconComp(task.status)"
              :style="{ color: statusIconColor(task.status), fontSize: '16px', flexShrink: 0 }"
            />
            <span class="task-url">{{ truncateUrl(task.url) }}</span>
            <a-tag :color="statusTagColor(task.status)" style="flex-shrink:0">
              {{ statusLabel(task.status) }}
            </a-tag>
            <a-tooltip v-if="task.error_msg" :title="task.error_msg">
              <ExclamationCircleOutlined style="color:#ff4d4f;cursor:pointer;flex-shrink:0" />
            </a-tooltip>
            <a
              v-if="['failed', 'done'].includes(task.status)"
              style="font-size:12px;color:#1677ff;flex-shrink:0"
              @click="retryTask(task)"
            >重新采集</a>
          </div>
        </div>
        <div v-if="crawlDone" style="margin-top:12px;text-align:right">
          <a-button type="primary" @click="router.push('/products')">
            前往商品列表查看结果
          </a-button>
        </div>
      </a-card>

      <!-- 采集配置 -->
      <a-card title="采集配置" :bordered="false" style="margin-top:16px">
        <a-alert
          v-if="!hasCookies && !hasProxy"
          type="warning"
          show-icon
          message="未配置 Cookie 或代理，TikTok 可能拦截采集请求"
          style="margin-bottom:12px;font-size:12px"
        />
        <a-alert
          v-else-if="hasCookies"
          type="success"
          show-icon
          message="Cookie 已配置"
          style="margin-bottom:12px;font-size:12px"
        />
        <a-space direction="vertical" style="width:100%">
          <a-button block @click="showCookieModal = true">
            <KeyOutlined /> 配置 TikTok Cookie
          </a-button>
          <a-button block @click="showProxyModal = true">
            <GlobalOutlined /> 配置代理
          </a-button>
        </a-space>
      </a-card>

      <!-- Cookie 配置弹窗 -->
      <a-modal
        v-model:open="showCookieModal"
        title="配置 TikTok Cookie"
        @ok="saveCookies"
        :confirm-loading="cookieSaving"
        ok-text="保存"
      >
        <a-alert type="info" show-icon style="margin-bottom:12px" message="获取步骤">
          <template #description>
            <ol style="margin:6px 0;padding-left:16px;font-size:12px;line-height:1.8">
              <li>在浏览器打开 shop.tiktok.com 并正常浏览（通过验证）</li>
              <li>按 F12 → Application → Cookies → shop.tiktok.com</li>
              <li>复制 sessionid、msToken、ttwid 等字段</li>
            </ol>
          </template>
        </a-alert>
        <a-form-item label="Cookie（JSON 或 key=value 格式）">
          <a-textarea
            v-model:value="cookieInput"
            :rows="5"
            placeholder='{"sessionid":"xxx","msToken":"yyy","ttwid":"zzz"}'
            style="font-family:monospace;font-size:12px"
          />
        </a-form-item>
        <a-button v-if="hasCookies" danger size="small" @click="clearCookies">清除已有 Cookie</a-button>
      </a-modal>

      <!-- 代理配置弹窗 -->
      <a-modal
        v-model:open="showProxyModal"
        title="配置代理"
        @ok="saveProxy"
        :confirm-loading="proxySaving"
        ok-text="保存"
      >
        <a-alert
          type="info" show-icon style="margin-bottom:12px"
          message="需要住宅代理（Residential Proxy）才能绕过 IP 封锁"
        />
        <a-form-item label="代理地址">
          <a-input
            v-model:value="proxyInput"
            placeholder="http://user:pass@host:port 或 socks5://host:port，留空清除"
          />
        </a-form-item>
      </a-modal>

      <!-- 使用说明 -->
      <a-card title="使用说明" :bordered="false" style="margin-top:16px">
        <a-steps direction="vertical" size="small" :current="4">
          <a-step title="粘贴 TikTok 链接" description="支持批量，每行一个" />
          <a-step title="点击导入" description="系统自动创建抓取任务" />
          <a-step title="查看商品列表" description="进入详情页填写拼多多比价" />
          <a-step title="计算利润" description="自动计算利润率，辅助选品决策" />
          <a-step title="标记与导出" description="标记已选/放弃，导出 Excel 报表" />
        </a-steps>
      </a-card>
    </a-col>
  </a-row>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ImportOutlined, DownloadOutlined, FilterOutlined,
  CheckCircleOutlined, CloseCircleOutlined, SyncOutlined,
  ClockCircleOutlined, ExclamationCircleOutlined,
  KeyOutlined, GlobalOutlined,
} from '@ant-design/icons-vue'
import { productApi, exportApi, taskApi, settingsApi } from '@/api/products'
import { REGION_MAP } from '@/utils'

const router = useRouter()
const urlsText = ref('')
const importing = ref(false)
const singleLoading = ref(false)

const singleForm = reactive({
  tiktok_url: '', title: '', price: null, currency: 'PHP', region: 'PH', remark: '',
})

// 采集进度
const taskList = ref([])   // [{ id, url, status, error_msg }]
let pollTimer = null

const urlCount = computed(() =>
  urlsText.value.split('\n').map(s => s.trim()).filter(Boolean).length
)

const doneCount = computed(() =>
  taskList.value.filter(t => ['done', 'failed'].includes(t.status)).length
)

const crawlPercent = computed(() => {
  if (!taskList.value.length) return 0
  return Math.round((doneCount.value / taskList.value.length) * 100)
})

const crawlDone = computed(() =>
  taskList.value.length > 0 && doneCount.value === taskList.value.length
)

const crawlProgressStatus = computed(() => {
  if (!crawlDone.value) return 'active'
  return taskList.value.some(t => t.status === 'failed') ? 'exception' : 'success'
})

// 状态展示辅助
function statusIconComp(status) {
  return {
    pending: ClockCircleOutlined,
    running: SyncOutlined,
    done: CheckCircleOutlined,
    failed: CloseCircleOutlined,
  }[status] || ClockCircleOutlined
}

function statusIconColor(status) {
  return { pending: '#d9d9d9', running: '#1677ff', done: '#52c41a', failed: '#ff4d4f' }[status] || '#d9d9d9'
}

function statusTagColor(status) {
  return { pending: 'default', running: 'processing', done: 'success', failed: 'error' }[status] || 'default'
}

function statusLabel(status) {
  return { pending: '等待中', running: '采集中', done: '完成', failed: '失败' }[status] || status
}

function truncateUrl(url) {
  const m = url.match(/\/product\/(\d+)/)
  return m ? `商品 ${m[1]}` : (url.length > 40 ? url.slice(0, 40) + '…' : url)
}

// 轮询任务状态
function startPolling(ids) {
  stopPolling()
  taskList.value = ids.map(id => ({ id, url: '', status: 'pending', error_msg: null }))

  const poll = async () => {
    try {
      const tasks = await taskApi.queryBatch(ids)
      tasks.forEach(t => {
        const item = taskList.value.find(x => x.id === t.id)
        if (item) Object.assign(item, t)
      })
      if (tasks.every(t => ['done', 'failed'].includes(t.status))) {
        stopPolling()
      }
    } catch (_) { /* 静默失败，继续轮询 */ }
  }

  poll()
  pollTimer = setInterval(poll, 2500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onUnmounted(stopPolling)

// 导入操作
async function doImport() {
  const urls = urlsText.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (!urls.length) return
  importing.value = true
  taskList.value = []
  try {
    const result = await productApi.batchImport(urls)
    const { created = 0, duplicates = 0, task_ids = [] } = result

    if (created === 0 && duplicates > 0) {
      // 全部重复
      message.warning(`${duplicates} 条链接已存在，未新增商品`)
    } else if (created > 0 && duplicates > 0) {
      // 部分重复
      message.info(`新增 ${created} 条，跳过重复 ${duplicates} 条，后台开始采集`)
      urlsText.value = ''
    } else if (created > 0) {
      // 全部新增
      message.success(`已提交 ${created} 条，后台开始采集`)
      urlsText.value = ''
    } else {
      message.warning('未导入任何商品，请检查链接格式')
    }

    if (task_ids.length) {
      startPolling(task_ids)
    }
  } finally {
    importing.value = false
  }
}

async function doSingle() {
  if (!singleForm.tiktok_url) { message.warning('请填写链接'); return }
  singleLoading.value = true
  try {
    await productApi.create({ ...singleForm })
    message.success('商品已添加，后台开始采集')
    Object.assign(singleForm, { tiktok_url: '', title: '', price: null, currency: 'PHP', region: 'PH', remark: '' })
  } catch (e) {
    if (e.status === 409) {
      message.warning({
        content: '该链接已存在，商品已在列表中',
        duration: 4,
      })
    }
    // 其他错误由 request.js 全局拦截器处理
  } finally {
    singleLoading.value = false
  }
}

async function retryTask(task) {
  // 先从服务端同步最新状态（解决前端缓存与DB不一致问题）
  try {
    const latest = await taskApi.get(task.id)
    Object.assign(task, latest)
  } catch (_) {}

  if (task.status === 'running') {
    message.warning('任务正在采集中，请稍后')
    return
  }

  try {
    // 乐观更新：先在本地显示 running 状态
    task.status = 'running'
    task.error_msg = null
    const updated = await taskApi.retry(task.id)
    Object.assign(task, updated)
    message.success('已重新提交，后台采集中')
    // 重启轮询，实时更新该任务状态
    startPolling(taskList.value.map(t => t.id))
  } catch (e) {
    // 失败时恢复最新状态
    try {
      const latest = await taskApi.get(task.id)
      Object.assign(task, latest)
    } catch (_) {}
  }
}

// ── 采集配置 ──
const showCookieModal = ref(false)
const showProxyModal = ref(false)
const cookieInput = ref('')
const proxyInput = ref('')
const cookieSaving = ref(false)
const proxySaving = ref(false)
const hasCookies = ref(false)
const hasProxy = ref(false)

async function loadConfig() {
  try {
    const cfg = await settingsApi.getConfig()
    hasCookies.value = !!cfg.tiktok_cookies
    hasProxy.value = !!cfg.tiktok_proxy
    proxyInput.value = cfg.tiktok_proxy || ''
  } catch (_) {}
}

async function saveCookies() {
  if (!cookieInput.value.trim()) { message.warning('请输入 Cookie'); return }
  cookieSaving.value = true
  try {
    await settingsApi.updateCookies(cookieInput.value)
    hasCookies.value = true
    showCookieModal.value = false
    cookieInput.value = ''
    message.success('Cookie 已保存')
  } finally {
    cookieSaving.value = false
  }
}

async function clearCookies() {
  await settingsApi.clearCookies()
  hasCookies.value = false
  message.success('Cookie 已清除')
}

async function saveProxy() {
  proxySaving.value = true
  try {
    await settingsApi.updateProxy(proxyInput.value)
    hasProxy.value = !!proxyInput.value
    showProxyModal.value = false
    message.success(proxyInput.value ? '代理已保存' : '代理已清除')
  } finally {
    proxySaving.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.task-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 320px;
  overflow-y: auto;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fafafa;
  font-size: 13px;
}
.task-url {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #333;
}
</style>
