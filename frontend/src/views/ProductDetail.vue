<template>
  <div v-if="product">
    <a-page-header
      :title="product.title || '商品详情'"
      @back="router.back()"
      style="background:#fff;padding:16px 24px;border-radius:8px;margin-bottom:16px"
    >
      <template #extra>
        <a-space>
          <a-dropdown trigger="click">
            <a-button>
              <template #icon><TagOutlined /></template>
              {{ STATUS_MAP[product.status]?.text }} ▾
            </a-button>
            <template #overlay>
              <a-menu @click="({ key }) => changeStatus(key)">
                <a-menu-item key="pending">待定</a-menu-item>
                <a-menu-item key="selected">已选</a-menu-item>
                <a-menu-item key="abandoned">放弃</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
          <a-button type="primary" ghost @click="exportApi.exportExcel([product.id])">
            <DownloadOutlined /> 导出
          </a-button>
          <a :href="product.tiktok_url" target="_blank">
            <a-button><LinkOutlined /> TikTok 原链接</a-button>
          </a>
        </a-space>
      </template>
    </a-page-header>

    <a-row :gutter="16">
      <!-- 左：TikTok 商品信息 -->
      <a-col :span="10">
        <a-card title="TikTok 商品信息" :bordered="false">
          <div class="img-gallery">
            <a-image
              v-if="product.main_image_url"
              :src="product.main_image_url"
              style="width:100%;max-height:300px;object-fit:contain;border-radius:8px"
            />
            <div v-else class="img-empty"><PictureOutlined style="font-size:48px;color:#ccc" /></div>
          </div>
          <a-descriptions :column="1" size="small" style="margin-top:16px">
            <a-descriptions-item label="标题">{{ product.title || '—' }}</a-descriptions-item>
            <a-descriptions-item label="价格">
              <span class="tiktok-price">{{ product.currency }} {{ product.price }}</span>
              <template v-if="product.original_price">
                <span style="color:#999;margin-left:8px;text-decoration:line-through">
                  {{ product.currency }} {{ product.original_price }}
                </span>
                <a-tag v-if="product.discount" color="red" style="margin-left:4px">{{ product.discount }}</a-tag>
              </template>
              <span v-if="product.price_cny" style="color:#999;margin-left:8px">≈ ¥{{ product.price_cny }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="销量">{{ product.sales_volume?.toLocaleString() }}</a-descriptions-item>
            <a-descriptions-item label="评分">
              <a-rate :value="Number(product.rating)" disabled allow-half />
              <span style="margin-left:4px">{{ product.rating }}</span>
              <span v-if="product.review_count" style="color:#999;margin-left:8px">({{ product.review_count }} 条评价)</span>
            </a-descriptions-item>
            <a-descriptions-item label="区域">
              {{ product.seller_location || REGION_MAP[product.region] || product.region }}
              <a-tag v-if="product.seller_location && product.region" size="small" style="margin-left:6px">{{ product.region }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="店铺">
              <a v-if="shopUrl && product.shop_name" :href="shopUrl" target="_blank" rel="noopener">
                {{ product.shop_name }} <LinkOutlined />
              </a>
              <span v-else>{{ product.shop_name || '—' }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="物流">
              <template v-if="product.free_shipping">
                <a-tag color="green">包邮</a-tag>
              </template>
              <template v-else-if="product.shipping_fee">
                {{ product.currency }} {{ product.shipping_fee }}
              </template>
              <span v-else>—</span>
              <span v-if="product.delivery_days_min" style="color:#999;margin-left:8px">
                预计 {{ product.delivery_days_min }}-{{ product.delivery_days_max }} 天送达
              </span>
            </a-descriptions-item>
          </a-descriptions>
          <a-divider />
          <a-form layout="vertical" @finish="saveRemark">
            <a-form-item label="备注">
              <a-textarea v-model:value="remarkVal" :rows="3" placeholder="添加选品备注..." />
            </a-form-item>
            <a-button html-type="submit" size="small">保存备注</a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- 右：拼多多比价 + 利润计算 -->
      <a-col :span="14">
        <!-- 拼多多比价 -->
        <a-card title="拼多多比价" :bordered="false" style="margin-bottom:16px">
          <template #extra>
            <a-space>
              <a-button
                size="small"
                :type="photoSearchBusy ? 'default' : 'primary'"
                :loading="photoSearchBusy"
                :disabled="!product.main_image_url || photoSearchBusy"
                @click="startPhotoSearch"
              >
                <template #icon><CameraOutlined /></template>
                {{ photoSearchSubmitting ? '提交中...' : photoTaskRunning ? '搜索中...' : '自动拍照购' }}
              </a-button>
              <a-button type="primary" size="small" @click="showAddMatch = true">
                <PlusOutlined /> 添加匹配
              </a-button>
            </a-space>
          </template>

          <!-- 拍照购任务状态条 -->
          <div v-if="photoTask" class="photo-task-bar">
            <a-alert
              :type="photoTaskAlertType"
              show-icon
              :closable="!photoTaskRunning"
              style="margin-bottom:12px"
            >
              <template #message>
                <span>拍照购任务 #{{ photoTask.id }}：{{ photoTaskStatusText }}</span>
                <span v-if="photoTask.candidates_found" style="margin-left:8px;color:#999">
                  找到 {{ photoTask.candidates_found }} 个候选，入库 {{ photoTask.candidates_saved }} 个
                </span>
                <a-button
                  v-if="photoTask.status === 'failed'"
                  size="small"
                  type="link"
                  @click="retryPhotoSearch"
                  style="margin-left:8px"
                >
                  重试
                </a-button>
              </template>
            </a-alert>
          </div>

          <a-empty v-if="!matches.length && !photoTaskRunning" description="暂无匹配商品，点击「自动拍照购」或手动添加" />
          <div v-else class="match-list">
            <div
              v-for="m in matches"
              :key="m.id"
              :class="['match-item', m.is_primary && 'is-primary']"
            >
              <a-image
                v-if="m.pdd_image_url"
                :src="m.pdd_image_url"
                :width="60" :height="60"
                style="object-fit:cover;border-radius:4px;flex-shrink:0"
                :fallback="fallbackImg"
              />
              <div v-else class="match-img-placeholder"><PictureOutlined /></div>
              <div class="match-info">
                <div class="match-title">{{ m.pdd_title }}</div>
                <div class="match-meta">
                  <span class="pdd-price">¥{{ m.pdd_price }}</span>
                  <span v-if="m.pdd_sales_volume" style="color:#999">销量 {{ m.pdd_sales_volume?.toLocaleString() }}</span>
                  <span v-if="m.pdd_shop_name" style="color:#999">{{ m.pdd_shop_name }}</span>
                </div>
                <div class="match-tags">
                  <a-tag v-if="m.is_primary" color="blue">主参照</a-tag>
                  <a-tag v-if="m.is_confirmed" color="green">已确认</a-tag>
                  <a-tag v-if="m.match_source === 'manual'" color="default">手动</a-tag>
                  <a-tag v-if="m.match_source === 'image_search'" color="orange">自动</a-tag>
                  <span v-if="m.match_confidence" style="font-size:11px;color:#999;margin-left:4px">
                    相似 {{ (parseFloat(m.match_confidence) * 100).toFixed(0) }}%
                  </span>
                </div>
              </div>
              <div class="match-actions">
                <a-space direction="vertical" size="small">
                  <a-button size="small" @click="setPrimary(m)">设为主参照</a-button>
                  <a-button size="small" @click="calcWithMatch(m)">计算利润</a-button>
                  <a-popconfirm title="确认删除？" @confirm="delMatch(m.id)">
                    <a-button size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 利润计算器 -->
        <a-card title="利润计算器" :bordered="false">
          <a-form :model="profitForm" layout="inline" @finish="doCalc" class="profit-form">
            <a-row :gutter="12" style="width:100%">
              <a-col :span="12">
                <a-form-item label="TikTok 折人民币">
                  <a-input-number v-model:value="profitForm.tiktok_price_cny" :min="0" :precision="2" style="width:120px" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="拼多多采购价">
                  <a-input-number v-model:value="profitForm.pdd_price_cny" :min="0" :precision="2" style="width:120px" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="物流成本(¥)">
                  <a-input-number v-model:value="profitForm.logistics_cost" :min="0" :precision="2" style="width:120px" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="平台佣金率">
                  <a-input-number v-model:value="profitForm.platform_fee_rate" :min="0" :max="1" :step="0.01" :precision="2" style="width:120px" />
                </a-form-item>
              </a-col>
              <a-col :span="24" style="text-align:right">
                <a-button type="primary" html-type="submit" :loading="calcLoading">计算利润</a-button>
              </a-col>
            </a-row>
          </a-form>

          <!-- 计算结果 -->
          <div v-if="calcResult" class="calc-result">
            <a-divider />
            <a-row :gutter="24" style="text-align:center">
              <a-col :span="8">
                <a-statistic title="TikTok 售价" :value="calcResult.tiktok_price_cny" prefix="¥" :precision="2" />
              </a-col>
              <a-col :span="8">
                <a-statistic title="总成本" :value="totalCost" prefix="¥" :precision="2" value-style="color:#ff4d4f" />
              </a-col>
              <a-col :span="8">
                <a-statistic
                  title="利润"
                  :value="calcResult.profit"
                  prefix="¥"
                  :precision="2"
                  :value-style="{ color: profitRateColor(calcResult.profit_rate) }"
                />
              </a-col>
            </a-row>
            <div class="profit-rate-bar">
              <span>利润率</span>
              <a-progress
                :percent="+(parseFloat(calcResult.profit_rate) * 100).toFixed(1)"
                :stroke-color="profitRateColor(calcResult.profit_rate)"
              />
            </div>
          </div>

          <!-- 历史记录 -->
          <a-divider v-if="profitHistory.length">历史计算</a-divider>
          <a-table
            v-if="profitHistory.length"
            :columns="histCols"
            :data-source="profitHistory"
            :pagination="false"
            size="small"
            row-key="id"
          />
        </a-card>
      </a-col>
    </a-row>

    <!-- 添加拼多多匹配弹窗 -->
    <a-modal v-model:open="showAddMatch" title="添加拼多多匹配商品" @ok="submitMatch" :confirm-loading="matchLoading">
      <a-form :model="matchForm" layout="vertical">
        <a-form-item label="商品标题" required>
          <a-input v-model:value="matchForm.pdd_title" placeholder="拼多多商品标题" />
        </a-form-item>
        <a-form-item label="售价（人民币）" required>
          <a-input-number v-model:value="matchForm.pdd_price" :min="0" :precision="2" style="width:100%" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="销量">
              <a-input-number v-model:value="matchForm.pdd_sales_volume" :min="0" style="width:100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="店铺名">
              <a-input v-model:value="matchForm.pdd_shop_name" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="商品链接">
          <a-input v-model:value="matchForm.pdd_product_url" placeholder="https://..." />
        </a-form-item>
        <a-form-item label="商品图片链接">
          <a-input v-model:value="matchForm.pdd_image_url" placeholder="https://..." />
        </a-form-item>
        <a-form-item>
          <a-checkbox v-model:checked="matchForm.is_primary_bool">设为主参照商品</a-checkbox>
          <a-checkbox v-model:checked="matchForm.is_confirmed_bool" style="margin-left:16px">已人工确认</a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>

  <a-skeleton v-else active :paragraph="{ rows: 8 }" />
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  TagOutlined, DownloadOutlined, LinkOutlined,
  PlusOutlined, PictureOutlined, CameraOutlined,
} from '@ant-design/icons-vue'
import { productApi, pddApi, profitApi, exportApi, photoSearchApi } from '@/api/products'
import { STATUS_MAP, REGION_MAP, profitRateColor } from '@/utils'

const route = useRoute()
const router = useRouter()
const fallbackImg = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+'

const product = ref(null)
const matches = ref([])
const profitHistory = ref([])
const calcResult = ref(null)
const calcLoading = ref(false)
const remarkVal = ref('')
const showAddMatch = ref(false)
const matchLoading = ref(false)

const photoTask = ref(null)
const photoSearchSubmitting = ref(false)
const photoTaskRunning = computed(() => {
  if (!photoTask.value) return false
  return ['queued', 'dispatching', 'running', 'collecting', 'parsing', 'saving'].includes(photoTask.value.status)
})
const photoSearchBusy = computed(() => photoSearchSubmitting.value || photoTaskRunning.value)

const shopUrl = computed(() => {
  if (!product.value) return ''
  const url = product.value.tiktok_url || ''
  const m = url.match(/(https?:\/\/[^/]+\/@[^/]+)/)
  if (m) return m[1]
  if (product.value.shop_id) {
    return `https://www.tiktok.com/shop/seller-${product.value.shop_id}`
  }
  return ''
})
const photoTaskStatusText = computed(() => {
  const map = {
    queued: '排队中…', dispatching: '分配设备…', running: '执行中…',
    collecting: '采集结果…', parsing: '解析中…', saving: '入库中…',
    success: '完成', failed: '失败', cancelled: '已取消',
    retry_waiting: '等待重试…',
  }
  return map[photoTask.value?.status] || photoTask.value?.status || ''
})
const photoTaskAlertType = computed(() => {
  const s = photoTask.value?.status
  if (s === 'success') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'cancelled') return 'warning'
  return 'info'
})
let photoTaskPollTimer = null

const profitForm = reactive({
  tiktok_price_cny: 0,
  pdd_price_cny: 0,
  logistics_cost: 15,
  platform_fee_rate: 0.05,
})

const matchForm = reactive({
  pdd_title: '', pdd_price: null, pdd_sales_volume: null,
  pdd_shop_name: '', pdd_product_url: '', pdd_image_url: '',
  is_primary_bool: false, is_confirmed_bool: false,
})

const totalCost = computed(() => {
  if (!calcResult.value) return 0
  return +(
    parseFloat(calcResult.value.pdd_price_cny) +
    parseFloat(calcResult.value.logistics_cost) +
    parseFloat(calcResult.value.platform_fee) +
    parseFloat(calcResult.value.other_cost)
  ).toFixed(2)
})

const histCols = [
  { title: 'TikTok 价(¥)', dataIndex: 'tiktok_price_cny', width: 110 },
  { title: '拼多多价(¥)', dataIndex: 'pdd_price_cny', width: 110 },
  { title: '物流(¥)', dataIndex: 'logistics_cost', width: 80 },
  { title: '利润(¥)', dataIndex: 'profit', width: 80 },
  { title: '利润率', key: 'rate', customRender: ({ record }) =>
    `${(parseFloat(record.profit_rate) * 100).toFixed(1)}%`, width: 80 },
  { title: '时间', dataIndex: 'created_at', width: 140 },
]

async function load() {
  const [p, m, h] = await Promise.all([
    productApi.get(route.params.id),
    pddApi.getMatches(route.params.id),
    profitApi.history(route.params.id),
  ])
  product.value = p
  matches.value = m
  profitHistory.value = h
  remarkVal.value = p.remark || ''
  if (p.price_cny) profitForm.tiktok_price_cny = parseFloat(p.price_cny)
  if (h.length) {
    const last = h[0]
    profitForm.pdd_price_cny = parseFloat(last.pdd_price_cny) || 0
    profitForm.logistics_cost = parseFloat(last.logistics_cost) ?? 15
    profitForm.platform_fee_rate = parseFloat(last.platform_fee_rate) ?? 0.05
  }
}

async function changeStatus(status) {
  await productApi.update(product.value.id, { status })
  product.value.status = status
  message.success('状态已更新')
}

async function saveRemark() {
  await productApi.update(product.value.id, { remark: remarkVal.value })
  message.success('备注已保存')
}

function calcWithMatch(m) {
  profitForm.pdd_price_cny = parseFloat(m.pdd_price)
}

async function setPrimary(m) {
  await pddApi.updateMatch(m.id, { is_primary: 1 })
  matches.value.forEach(x => x.is_primary = x.id === m.id ? 1 : 0)
  message.success('已设为主参照')
}

async function delMatch(id) {
  await pddApi.deleteMatch(id)
  matches.value = matches.value.filter(m => m.id !== id)
  message.success('已删除')
}

async function doCalc() {
  calcLoading.value = true
  try {
    const primaryMatch = matches.value.find(m => m.is_primary)
    calcResult.value = await profitApi.calculate({
      product_id: product.value.id,
      pdd_match_id: primaryMatch?.id || null,
      ...profitForm,
    })
    profitHistory.value = await profitApi.history(product.value.id)
  } finally {
    calcLoading.value = false
  }
}

async function submitMatch() {
  if (!matchForm.pdd_title || !matchForm.pdd_price) {
    message.warning('请填写标题和价格')
    return
  }
  matchLoading.value = true
  try {
    const m = await pddApi.addMatch({
      product_id: product.value.id,
      pdd_title: matchForm.pdd_title,
      pdd_price: matchForm.pdd_price,
      pdd_sales_volume: matchForm.pdd_sales_volume,
      pdd_shop_name: matchForm.pdd_shop_name,
      pdd_product_url: matchForm.pdd_product_url,
      pdd_image_url: matchForm.pdd_image_url,
      is_primary: matchForm.is_primary_bool ? 1 : 0,
      is_confirmed: matchForm.is_confirmed_bool ? 1 : 0,
      match_source: 'manual',
    })
    matches.value.push(m)
    if (m.is_primary) matches.value.forEach(x => { if (x.id !== m.id) x.is_primary = 0 })
    showAddMatch.value = false
    Object.assign(matchForm, { pdd_title: '', pdd_price: null, pdd_sales_volume: null,
      pdd_shop_name: '', pdd_product_url: '', pdd_image_url: '',
      is_primary_bool: false, is_confirmed_bool: false })
    message.success('匹配商品已添加')
  } finally {
    matchLoading.value = false
  }
}

async function startPhotoSearch() {
  if (!product.value?.main_image_url) {
    message.warning('该商品暂无主图，无法自动拍照购')
    return
  }
  if (photoSearchBusy.value) return
  photoSearchSubmitting.value = true
  try {
    const res = await photoSearchApi.createTask({ product_id: product.value.id })
    photoTask.value = res
    message.info('拍照购任务已创建，正在执行...')
    startPollingPhotoTask(res.id)
  } catch (e) {
    const status = e?.response?.status
    if (status === 409) {
      message.warning('拍照购任务正在执行中，请等待完成')
    } else {
      message.error(e?.response?.data?.detail || '创建拍照购任务失败')
    }
  } finally {
    photoSearchSubmitting.value = false
  }
}

async function retryPhotoSearch() {
  if (!photoTask.value) return
  try {
    const res = await photoSearchApi.retryTask(photoTask.value.id)
    photoTask.value = res
    message.info('重试任务已提交')
    startPollingPhotoTask(res.id)
  } catch (e) {
    message.error(e?.response?.data?.detail || '重试失败')
  }
}

function startPollingPhotoTask(taskId) {
  stopPollingPhotoTask()
  photoTaskPollTimer = setInterval(async () => {
    try {
      const res = await photoSearchApi.getTask(taskId)
      photoTask.value = res
      if (!['queued', 'dispatching', 'running', 'collecting', 'parsing', 'saving'].includes(res.status)) {
        stopPollingPhotoTask()
        if (res.status === 'success') {
          message.success(`拍照购完成，找到 ${res.candidates_found} 个候选，入库 ${res.candidates_saved} 个`)
          const m = await pddApi.getMatches(route.params.id)
          matches.value = m
        }
      }
    } catch {
      stopPollingPhotoTask()
    }
  }, 2000)
}

function stopPollingPhotoTask() {
  if (photoTaskPollTimer) {
    clearInterval(photoTaskPollTimer)
    photoTaskPollTimer = null
  }
}

async function loadLatestPhotoTask() {
  try {
    const tasks = await photoSearchApi.getTasksByProduct(route.params.id)
    if (tasks?.length) {
      photoTask.value = tasks[0]
      if (photoTaskRunning.value) {
        startPollingPhotoTask(tasks[0].id)
      }
    }
  } catch {}
}

onMounted(async () => {
  await load()
  await loadLatestPhotoTask()
})
</script>

<style scoped>
.img-empty {
  height: 200px; display: flex; align-items: center; justify-content: center;
  background: #fafafa; border-radius: 8px;
}
.tiktok-price { font-size: 20px; font-weight: 700; color: #ff2d55; }
.match-list { display: flex; flex-direction: column; gap: 12px; }
.match-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px; border-radius: 8px; border: 1px solid #f0f0f0;
  transition: border-color .2s;
}
.match-item.is-primary { border-color: #1677ff; background: #f0f7ff; }
.match-img-placeholder {
  width: 60px; height: 60px; background: #f5f5f5; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; color: #ccc; flex-shrink: 0;
}
.match-info { flex: 1; min-width: 0; }
.match-title { font-weight: 500; margin-bottom: 4px; }
.match-meta { display: flex; gap: 10px; align-items: center; font-size: 12px; margin-bottom: 4px; }
.pdd-price { font-size: 16px; font-weight: 700; color: #e62e2e; }
.match-tags { display: flex; gap: 4px; }
.match-actions { flex-shrink: 0; }
.profit-form { width: 100%; }
.calc-result { padding-top: 8px; }
.profit-rate-bar { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.profit-rate-bar > span { flex-shrink: 0; color: #666; font-size: 13px; }
.photo-task-bar { margin-bottom: 4px; }
</style>
