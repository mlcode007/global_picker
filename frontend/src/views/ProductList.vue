<template>
  <div class="product-list-page">
    <!-- 过滤栏 -->
    <a-card class="filter-card" :bordered="false">
      <a-row :gutter="[12, 12]" align="middle">
        <a-col :span="5">
          <a-input-search
            v-model:value="store.filters.keyword"
            placeholder="搜索商品标题 / 店铺"
            allow-clear
            @search="onSearch"
          />
        </a-col>
        <a-col :span="3">
          <a-select
            v-model:value="store.filters.status"
            placeholder="选品状态"
            allow-clear
            style="width: 100%"
            @change="onSearch"
          >
            <a-select-option value="pending">待定</a-select-option>
            <a-select-option value="selected">已选</a-select-option>
            <a-select-option value="abandoned">放弃</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="3">
          <a-select
            v-model:value="store.filters.region"
            placeholder="销售区域"
            allow-clear
            style="width: 100%"
            @change="onSearch"
          >
            <a-select-option v-for="(v, k) in REGION_MAP" :key="k" :value="k">{{ v }}</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="3">
          <div class="range-filter">
            <span class="range-label">TikTok¥</span>
            <a-input-number
              v-model:value="store.filters.price_cny_min"
              placeholder="最低"
              :min="0"
              :precision="0"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
            <span class="range-sep">-</span>
            <a-input-number
              v-model:value="store.filters.price_cny_max"
              placeholder="最高"
              :min="0"
              :precision="0"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
          </div>
        </a-col>
        <a-col :span="3">
          <div class="range-filter">
            <span class="range-label">利润¥</span>
            <a-input-number
              v-model:value="store.filters.profit_min"
              placeholder="最低"
              :precision="0"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
            <span class="range-sep">-</span>
            <a-input-number
              v-model:value="store.filters.profit_max"
              placeholder="最高"
              :precision="0"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
          </div>
        </a-col>
        <a-col :span="3">
          <div class="range-filter">
            <span class="range-label">利润率%</span>
            <a-input-number
              v-model:value="store.filters.profit_rate_min"
              placeholder="最低"
              :precision="1"
              :step="0.1"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
            <span class="range-sep">-</span>
            <a-input-number
              v-model:value="store.filters.profit_rate_max"
              placeholder="最高"
              :precision="1"
              :step="0.1"
              size="small"
              style="width:60px"
              @pressEnter="onSearch"
            />
          </div>
        </a-col>
        <a-col :flex="1" style="text-align:right">
          <a-space>
            <a-button @click="onSearch"><ReloadOutlined /> 刷新</a-button>
            <a-button
              type="primary"
              ghost
              :disabled="!selectedRowKeys.length"
              @click="openExportModal"
            >
              <DownloadOutlined /> 导出 Excel
            </a-button>
            <a-tooltip title="对勾选且有主图的商品依次执行拍照购（本批全部处理）。侧栏数字表示每笔任务最多入库几条拼多多匹配。每步前会对你名下非离线云手机做健康检查（与云手机管理「检查」一致），失败自动重试最多 3 次。">
              <a-button
                type="primary"
                ghost
                :loading="photoBatchRunning"
                :disabled="photoBatchRunning || crawlBatchRunning || !selectedRowKeys.length"
                @click="startBatchPhotoSearch"
              >
                <CameraOutlined /> 自动拍照购
              </a-button>
            </a-tooltip>
            <a-tooltip title="对勾选且有采集任务的商品依次重新采集 TikTok 数据，完成后自动刷新本行">
              <a-button
                type="primary"
                ghost
                :loading="crawlBatchRunning"
                :disabled="crawlBatchRunning || photoBatchRunning || !selectedRowKeys.length"
                @click="startBatchCrawl"
              >
                <SyncOutlined /> 批量采集
              </a-button>
            </a-tooltip>
            <a-button type="primary" @click="router.push('/import')"><ImportOutlined /> 批量导入</a-button>
          </a-space>
        </a-col>
      </a-row>
      <a-row :gutter="[12, 8]" align="middle" class="photo-batch-toolbar-row">
        <a-col :span="24">
          <a-space wrap :size="12" align="center">
            <span class="toolbar-muted">自动拍照购</span>
            <span>每笔最多入库</span>
            <a-input-number
              v-model:value="photoBatchMaxItems"
              :min="1"
              :max="50"
              size="small"
              style="width: 72px"
            />
            <span>条拼多多</span>
            <a-divider type="vertical" />
            <a-checkbox v-model:checked="photoBatchFetchPddLinks">获取拼多多商品链接</a-checkbox>
            <span class="toolbar-hint">关闭则跳过详情页链接步骤，速度更快</span>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 数据表格 -->
    <a-card :bordered="false" style="margin-top: 12px">
      <a-table
        :columns="columns"
        :data-source="store.list"
        :loading="store.loading"
        :pagination="pagination"
        row-key="id"
        :scroll="{ x: 1400 }"
        :row-selection="rowSelection"
        :expanded-row-keys="expandedRowKeys"
        :expand-column-width="92"
        @change="onTableChange"
        @expand="onExpand"
      >
        <template #expandColumnTitle>
          <div class="expand-col-title" @click.stop>
            <a class="expand-col-link" @click="expandAllPddRows">全部展开</a>
            <a class="expand-col-link" @click="collapseAllPddRows">全部折叠</a>
          </div>
        </template>
        <template #bodyCell="{ column, record }">
          <!-- 商品信息列 -->
          <template v-if="column.key === 'product'">
            <div class="product-cell">
              <a-image
                v-if="record.main_image_url"
                :src="record.main_image_url"
                :width="80"
                :height="80"
                style="object-fit:cover;border-radius:6px;flex-shrink:0"
                :preview="true"
                :fallback="fallbackImg"
              />
              <div v-else class="img-placeholder"><PictureOutlined /></div>
              <div class="product-info">
                <span
                  class="product-title"
                  role="button"
                  tabindex="0"
                  @click="toggleExpand(record.id)"
                  @keydown.enter.prevent="toggleExpand(record.id)"
                >
                  {{ record.title || '（待抓取）' }}
                </span>
                <div class="product-meta">
                  <a-tag size="small">{{ record.seller_location || record.region }}</a-tag>
                  <a v-if="record.shop_name" :href="getShopUrl(record)" target="_blank" rel="noopener" class="shop" @click.stop>
                    {{ record.shop_name }}
                  </a>
                  <span v-else class="shop">—</span>
                </div>
                <div v-if="photoRowProgress[record.id]" class="photo-batch-row">
                  <template v-if="photoRowProgress[record.id].phase === 'skipped'">
                    <span class="photo-batch-muted">{{ photoRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="photoRowProgress[record.id].phase === 'queued'">
                    <a-tag color="default" style="margin:0">排队 {{ photoRowProgress[record.id].orderIndex }}/{{ photoRowProgress[record.id].batchTotal }}</a-tag>
                    <span class="photo-batch-muted">{{ photoRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="photoRowProgress[record.id].phase === 'running'">
                    <a-spin size="small" style="margin-right:6px" />
                    <span class="photo-batch-active">{{ photoRowProgress[record.id].stepText }}</span>
                    <span v-if="photoRowProgress[record.id].task?.id" class="photo-batch-muted">任务 #{{ photoRowProgress[record.id].task.id }}</span>
                  </template>
                  <template v-else-if="photoRowProgress[record.id].phase === 'done'">
                    <CheckCircleOutlined class="photo-batch-ok" />
                    <span class="photo-batch-done-text">{{ photoRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="photoRowProgress[record.id].phase === 'failed'">
                    <CloseCircleOutlined class="photo-batch-err" />
                    <span class="photo-batch-err-text">{{ photoRowProgress[record.id].stepText }}</span>
                  </template>
                </div>
                <div v-if="crawlRowProgress[record.id]" class="photo-batch-row crawl-batch-row">
                  <template v-if="crawlRowProgress[record.id].phase === 'skipped'">
                    <span class="photo-batch-muted">{{ crawlRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="crawlRowProgress[record.id].phase === 'queued'">
                    <a-tag color="processing" style="margin:0">采集 {{ crawlRowProgress[record.id].orderIndex }}/{{ crawlRowProgress[record.id].batchTotal }}</a-tag>
                    <span class="photo-batch-muted">{{ crawlRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="crawlRowProgress[record.id].phase === 'running'">
                    <a-spin size="small" style="margin-right:6px" />
                    <span class="photo-batch-active">{{ crawlRowProgress[record.id].stepText }}</span>
                    <span v-if="crawlRowProgress[record.id].task?.id" class="photo-batch-muted">任务 #{{ crawlRowProgress[record.id].task.id }}</span>
                  </template>
                  <template v-else-if="crawlRowProgress[record.id].phase === 'done'">
                    <CheckCircleOutlined class="photo-batch-ok" />
                    <span class="photo-batch-done-text">{{ crawlRowProgress[record.id].stepText }}</span>
                  </template>
                  <template v-else-if="crawlRowProgress[record.id].phase === 'failed'">
                    <CloseCircleOutlined class="photo-batch-err" />
                    <span class="photo-batch-err-text">{{ crawlRowProgress[record.id].stepText }}</span>
                  </template>
                </div>
              </div>
            </div>
          </template>

          <!-- TikTok 价格列 -->
          <template v-else-if="column.key === 'price'">
            <div>
              <span class="price-tiktok">{{ record.currency }} {{ record.price }}</span>
              <a-tag v-if="record.discount" color="red" size="small" style="margin-left:4px">{{ record.discount }}</a-tag>
              <div v-if="record.price_cny" class="price-cny">≈ ¥{{ record.price_cny }}</div>
            </div>
          </template>

          <!-- 销量列 -->
          <template v-else-if="column.key === 'sales_volume'">
            <span class="sales">{{ record.sales_volume?.toLocaleString() }}</span>
          </template>

          <!-- 拼多多匹配列 -->
          <template v-else-if="column.key === 'pdd_toggle'">
            <a-button
              size="small"
              type="link"
              @click.stop="toggleExpand(record.id)"
            >
              <template #icon>
                <DownOutlined v-if="!expandedRowKeys.includes(record.id)" />
                <UpOutlined v-else />
              </template>
              {{ pddMatchesMap[record.id]?.length || 0 }} 个匹配
            </a-button>
          </template>

          <!-- 预估利润列 -->
          <template v-else-if="column.key === 'profit'">
            <template v-if="record.estimated_profit != null">
              <div :style="{ color: profitColor(record.estimated_profit), fontWeight: 600 }">
                ¥{{ Number(record.estimated_profit).toFixed(2) }}
              </div>
            </template>
            <a-tooltip
              v-else-if="!record.price_cny || Number(record.price_cny) <= 0"
              title="预估利润需商品有 TikTok 人民币价（先完成采集/补全价格）"
            >
              <span class="no-data">需TikTok价</span>
            </a-tooltip>
            <span v-else class="no-data">—</span>
          </template>

          <!-- 预估利润率列 -->
          <template v-else-if="column.key === 'profit_rate'">
            <template v-if="record.profit_rate != null">
              <div :style="{ color: profitColor(record.profit_rate * record.price_cny), fontWeight: 600 }">
                {{ (Number(record.profit_rate) * 100).toFixed(1) }}%
              </div>
            </template>
            <span v-else class="no-data">—</span>
          </template>

          <!-- 选品状态列 -->
          <template v-else-if="column.key === 'status'">
            <a-dropdown trigger="click">
              <a-tag
                :color="STATUS_MAP[record.status]?.color"
                style="cursor:pointer"
              >
                {{ STATUS_MAP[record.status]?.text }} ▾
              </a-tag>
              <template #overlay>
                <a-menu @click="({ key }) => store.updateStatus(record.id, key)">
                  <a-menu-item key="pending">待定</a-menu-item>
                  <a-menu-item key="selected">已选</a-menu-item>
                  <a-menu-item key="abandoned">放弃</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </template>

          <!-- 操作列 -->
          <template v-else-if="column.key === 'action'">
            <a-space :size="4">
              <a @click="router.push(`/products/${record.id}`)">详情</a>
              <a-divider type="vertical" style="margin:0" />
              <a-tooltip :title="record.crawl_task_id ? '重新采集' : '无采集任务'">
                <a
                  :style="!record.crawl_task_id
                    ? 'color:#ccc;cursor:not-allowed'
                    : (recrawlingIds.has(record.id) || crawlBatchRunning)
                      ? 'color:#faad14;opacity:.7'
                      : 'color:#faad14'"
                  @click="record.crawl_task_id && !crawlBatchRunning && recrawl(record)"
                >
                  <SyncOutlined :spin="recrawlingIds.has(record.id)" /> 采集
                </a>
              </a-tooltip>
              <a-divider type="vertical" style="margin:0" />
              <a-popconfirm title="确认删除？" @confirm="store.deleteProduct(record.id)">
                <a style="color:#ff4d4f">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>

        <!-- 展开行：拼多多匹配商品 -->
        <template #expandedRowRender="{ record }">
          <div class="pdd-expand-wrapper">
            <div v-if="pddMatchesLoading[record.id]" style="text-align:center;padding:12px">
              <a-spin size="small" /> 加载中...
            </div>
            <div v-else-if="!pddMatchesMap[record.id]?.length" class="pdd-expand-empty">
              暂无拼多多匹配商品
            </div>
            <div v-else class="pdd-match-list">
              <div
                v-for="m in pddMatchesMap[record.id]"
                :key="m.id"
                :class="['pdd-match-row', m.is_primary && 'is-primary']"
              >
                <a-image
                  v-if="m.pdd_image_url"
                  :src="m.pdd_image_url"
                  referrerpolicy="no-referrer"
                  :width="56" :height="56"
                  style="object-fit:cover;border-radius:6px;flex-shrink:0"
                  :fallback="fallbackImg"
                />
                <div v-else class="pdd-img-placeholder"><PictureOutlined /></div>
                <div class="pdd-match-info">
                  <span class="pdd-match-title">{{ m.pdd_title }}</span>
                  <div class="pdd-match-meta">
                    <span class="pdd-price">¥{{ m.pdd_price }}</span>
                    <span v-if="m.pdd_sales_volume" class="pdd-sales">销量 {{ m.pdd_sales_volume?.toLocaleString() }}</span>
                    <span v-if="m.pdd_shop_name" class="pdd-shop">{{ m.pdd_shop_name }}</span>
                    <a
                      v-if="m.pdd_product_url"
                      :href="m.pdd_product_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click.stop
                      class="pdd-link"
                    >
                      <LinkOutlined /> 拼多多商品页
                    </a>
                  </div>
                </div>
                <div class="pdd-match-tags">
                  <a-tag v-if="m.is_primary" color="blue">主参照</a-tag>
                  <a-tag v-if="m.match_source === 'manual'" color="default" size="small">手动</a-tag>
                  <a-tag v-if="m.match_source === 'image_search'" color="orange" size="small">自动</a-tag>
                </div>
                <div class="pdd-match-actions">
                  <a-space :size="4" wrap align="center">
                    <a-button
                      v-if="!m.is_primary"
                      size="small"
                      type="link"
                      @click="setPrimaryInList(record, m)"
                    >
                      设为主参照
                    </a-button>
                    <a-popconfirm
                      title="确认删除该拼多多匹配？"
                      ok-text="删除"
                      ok-type="danger"
                      @confirm="deleteMatchInList(record, m)"
                    >
                      <a-button size="small" type="link" danger @click.stop>删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </div>
              </div>
            </div>
          </div>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="exportModalOpen"
      title="导出 Excel"
      ok-text="开始导出"
      cancel-text="取消"
      :confirm-loading="exportSubmitting"
      width="720px"
      destroy-on-close
      @ok="confirmExport"
    >
      <p class="export-modal-summary">
        将导出当前已勾选的 <strong>{{ selectedRowKeys.length }}</strong> 条商品。请选择需要包含的列（无需的列可不选）。列选择会保存在本机与账号中，清除浏览器数据后将自动从账号恢复。
      </p>
      <div class="export-field-toolbar">
        <a-space>
          <a-button size="small" @click="selectAllExportFields">全选</a-button>
          <a-button size="small" @click="clearExportFields">全不选</a-button>
          <a-button size="small" type="link" @click="resetExportFields">恢复默认</a-button>
        </a-space>
      </div>
      <a-checkbox-group v-model:value="exportSelectedFields" class="export-checkbox-group">
        <a-row :gutter="[8, 6]">
          <a-col v-for="opt in exportFieldOptions" :key="opt.key" :span="12">
            <a-checkbox :value="opt.key">{{ opt.label }}</a-checkbox>
          </a-col>
        </a-row>
      </a-checkbox-group>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined, DownloadOutlined, ImportOutlined, PictureOutlined,
  SyncOutlined, DownOutlined, UpOutlined, LinkOutlined,
  CameraOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons-vue'
import { useProductStore } from '@/stores/product'
import { productApi, exportApi, taskApi, pddApi, photoSearchApi } from '@/api/products'
import { userApi } from '@/api/user'
import { cloudPhoneApi } from '@/api/cloudPhone'
import { STATUS_MAP, REGION_MAP } from '@/utils'
import { pollPhotoTaskUntilDone, PHOTO_POLL_ACTIVE, formatPhotoTaskLine } from '@/utils/photoSearchTask'
import { pollCrawlTaskUntilDone, formatCrawlTaskLine, sleep as crawlSleep } from '@/utils/crawlTask'

const router = useRouter()
const store = useProductStore()
const recrawlingIds = ref(new Set())

const fallbackImg = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+'

function profitColor(val) {
  const v = Number(val)
  if (v >= 20) return '#52c41a'
  if (v >= 0) return '#faad14'
  return '#ff4d4f'
}

// --- 复选框 & 全选 ---
const selectedRowKeys = ref([])
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys) => { selectedRowKeys.value = keys },
  getCheckboxProps: () => ({
    disabled: photoBatchRunning.value || crawlBatchRunning.value,
  }),
}))

// --- 列表页批量拍照购（串行）---
const photoBatchRunning = ref(false)
const photoRowProgress = reactive({})
const PHOTO_BATCH_DEFAULT_MAX = 2
const LS_PHOTO_BATCH_MAX = 'gp_photo_batch_max_items'
const LS_PHOTO_BATCH_FETCH_LINKS = 'gp_photo_batch_fetch_pdd_links'

function readStoredPhotoBatchMax() {
  if (typeof localStorage === 'undefined') return PHOTO_BATCH_DEFAULT_MAX
  try {
    const raw = localStorage.getItem(LS_PHOTO_BATCH_MAX)
    if (raw == null || raw === '') return PHOTO_BATCH_DEFAULT_MAX
    const n = parseInt(raw, 10)
    if (!Number.isFinite(n)) return PHOTO_BATCH_DEFAULT_MAX
    return Math.min(Math.max(1, n), 50)
  } catch {
    return PHOTO_BATCH_DEFAULT_MAX
  }
}

function readStoredPhotoBatchFetchPddLinks() {
  if (typeof localStorage === 'undefined') return true
  try {
    const raw = localStorage.getItem(LS_PHOTO_BATCH_FETCH_LINKS)
    if (raw == null) return true
    return raw === '1' || raw === 'true'
  } catch {
    return true
  }
}

const photoBatchMaxItems = ref(readStoredPhotoBatchMax())
/** 为 true 时后端会进拼多多详情补全商品链接；为 false 时跳过该步骤以提速 */
const photoBatchFetchPddLinks = ref(readStoredPhotoBatchFetchPddLinks())

watch(photoBatchMaxItems, (v) => {
  try {
    const n = Math.floor(Number(v))
    if (Number.isFinite(n) && n >= 1 && n <= 50) {
      localStorage.setItem(LS_PHOTO_BATCH_MAX, String(n))
    }
  } catch {
    /* ignore */
  }
})

watch(photoBatchFetchPddLinks, (v) => {
  try {
    localStorage.setItem(LS_PHOTO_BATCH_FETCH_LINKS, v ? '1' : '0')
  } catch {
    /* ignore */
  }
})

/** 最近一次健康检查通过的云手机 phone_id，减少重复拉列表 */
const photoHealthPhoneCache = ref(null)

// --- 列表页批量采集 TikTok（串行，与拍照购一致：间隔 + 行内进度）---
const crawlBatchRunning = ref(false)
const crawlRowProgress = reactive({})

/** 两条商品采集之间的间隔（ms），避免连续打满后端/浏览器 */
const CRAWL_BATCH_GAP_MS = { min: 720, max: 1100 }

function randomCrawlGap() {
  const { min, max } = CRAWL_BATCH_GAP_MS
  return min + Math.floor(Math.random() * (max - min + 1))
}

async function startBatchCrawl() {
  if (crawlBatchRunning.value) return
  const keys = [...selectedRowKeys.value]
  if (!keys.length) {
    message.warning('请先勾选要采集的商品')
    return
  }

  const rows = store.list.filter(r => keys.includes(r.id))
  const ordered = keys.map(id => rows.find(r => r.id === id)).filter(Boolean)

  Object.keys(crawlRowProgress).forEach((k) => { delete crawlRowProgress[k] })

  ordered.forEach((r, i) => {
    const orderIndex = i + 1
    const batchTotal = ordered.length
    if (!r.crawl_task_id) {
      crawlRowProgress[r.id] = {
        phase: 'skipped',
        orderIndex,
        batchTotal,
        stepText: '无采集任务，已跳过（请通过导入或详情页创建商品）',
      }
    } else {
      crawlRowProgress[r.id] = {
        phase: 'queued',
        orderIndex,
        batchTotal,
        stepText: `排队中（${orderIndex}/${batchTotal}）`,
      }
    }
  })

  const valid = ordered.filter(r => r.crawl_task_id)
  if (!valid.length) {
    message.warning('勾选的商品均无采集任务，无法批量采集')
    return
  }

  crawlBatchRunning.value = true
  let ok = 0
  let fail = 0

  try {
    for (let i = 0; i < valid.length; i++) {
      const r = valid[i]
      const pid = r.id

      if (i > 0) {
        await crawlSleep(randomCrawlGap())
      }

      crawlRowProgress[pid] = {
        ...crawlRowProgress[pid],
        phase: 'running',
        stepText: '提交采集任务…',
        task: null,
      }

      try {
        const submitted = await taskApi.retry(r.crawl_task_id)
        crawlRowProgress[pid].task = submitted
        crawlRowProgress[pid].stepText = formatCrawlTaskLine(submitted)
        console.info(
          `[批量采集] 商品 id=${pid} 已提交 任务 #${submitted.id} 状态=${submitted.status}`,
        )

        const finalTask = await pollCrawlTaskUntilDone(
          r.crawl_task_id,
          (t) => {
            crawlRowProgress[pid].task = t
            crawlRowProgress[pid].stepText = formatCrawlTaskLine(t)
            if (t.status === 'running' || t.status === 'pending') {
              console.info(
                `[批量采集] 商品 id=${pid} 任务 #${t.id} 轮询 → ${t.status}`,
              )
            }
          },
        )

        if (finalTask.status === 'done') {
          ok += 1
          crawlRowProgress[pid].phase = 'done'
          crawlRowProgress[pid].task = finalTask
          crawlRowProgress[pid].stepText = formatCrawlTaskLine(finalTask)
          console.info(`[批量采集] 商品 id=${pid} 采集成功`)
          try {
            const updated = finalTask.product ?? await productApi.get(pid)
            const index = store.list.findIndex(p => p.id === pid)
            if (index !== -1) {
              store.list[index] = updated
            }
          } catch (e) {
            console.warn('[批量采集] 刷新商品行失败', pid, e)
          }
        } else {
          fail += 1
          crawlRowProgress[pid].phase = 'failed'
          crawlRowProgress[pid].task = finalTask
          crawlRowProgress[pid].stepText = formatCrawlTaskLine(finalTask)
          console.warn(
            `[批量采集] 商品 id=${pid} 采集失败`,
            finalTask.error_msg || finalTask.status,
          )
        }
      } catch (e) {
        fail += 1
        crawlRowProgress[pid].phase = 'failed'
        const msg = e?.message || '提交或等待任务失败'
        crawlRowProgress[pid].stepText = msg
        console.error('[批量采集] 异常', { productId: pid, err: e })
      }
    }

    message.success(`批量采集已结束：成功 ${ok} 条，失败 ${fail} 条`)
    if (fail > 0) {
      message.warning({
        content: `有 ${fail} 条未成功，请查看各行说明或稍后单独点击「采集」重试`,
        duration: 7,
      })
    }
  } finally {
    crawlBatchRunning.value = false
  }
}

function httpErrorDetail(err) {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg
  return null
}

/** 与云手机列表一致：排除离线、已删除，其余均参与轮询检查（含「检查中」等） */
const _POOL_STATUS_EXCLUDE = new Set(['offline', 'off', 'deleted', 'del'])
/** 每轮之间间隔；设备之间短间隔，减轻并发压力 */
const PHONE_CHECK_MAX_ROUNDS = 3
const PHONE_CHECK_ROUND_GAP_MS = 900
const PHONE_CHECK_DEVICE_GAP_MS = 120
/** 单商品拍照购：失败或异常时最多尝试次数（含首次）；第 2 次起强制重做云手机检查并 retry 任务 */
const PHOTO_BATCH_MAX_ATTEMPTS = 3
const PHOTO_BATCH_RETRY_GAP_MS = 500

function _isPoolDeviceNotOffline(status) {
  return !_POOL_STATUS_EXCLUDE.has(String(status || '').toLowerCase())
}

/** 优先：可用 > 已绑定/检查中 > 超时类 > 其它；同优先内有 ADB 端口优先 */
function _poolDeviceSortKey(p) {
  const s = String(p.status || '').toLowerCase()
  const raw = String(p.status || '')
  let pri = 5
  if (s === 'available' || s === 'ok') pri = 0
  else if (
    s === 'bound'
    || s === 'checking'
    || s.includes('check')
    || raw.includes('检查')
  ) pri = 1
  else if (s === 'timeo' || s === 'adb_timeout' || s === 'timeout' || s === 'to') pri = 2
  else if (s === 'maintenance') pri = 3
  const adb = p.adb_host_port ? 0 : 1
  return [pri, adb, p.phone_id || '']
}

function _sortPoolDevicesForCheck(items) {
  return [...items].sort((a, b) => {
    const ka = _poolDeviceSortKey(a)
    const kb = _poolDeviceSortKey(b)
    for (let i = 0; i < 3; i++) {
      if (ka[i] < kb[i]) return -1
      if (ka[i] > kb[i]) return 1
    }
    return 0
  })
}

/**
 * 与「云手机管理」中「检查」相同接口（/cloud-phone/health）。
 * 遍历当前账号云手机池内所有非离线设备，逐台检查；最多 3 轮；onLog 用于更新单行 stepText 提示。
 */
async function ensureUserCloudPhoneReady(options = {}) {
  const { onLog } = options
  const log = (msg) => {
    onLog?.(msg)
  }

  if (photoHealthPhoneCache.value) {
    log(`复用缓存设备 ${photoHealthPhoneCache.value}，快速校验…`)
    try {
      const quick = await cloudPhoneApi.checkHealth(photoHealthPhoneCache.value)
      if (quick?.is_healthy) {
        log('缓存设备健康，可用')
        return
      }
      log('缓存设备未通过，重新扫描云手机池')
    } catch (e) {
      log(`缓存校验失败：${httpErrorDetail(e) || e?.message || '未知错误'}`)
    }
    photoHealthPhoneCache.value = null
  }

  for (let round = 1; round <= PHONE_CHECK_MAX_ROUNDS; round++) {
    if (round > 1) {
      log(`第 ${round}/${PHONE_CHECK_MAX_ROUNDS} 轮：等待 ${PHONE_CHECK_ROUND_GAP_MS / 1000}s 后重试…`)
      await new Promise((r) => setTimeout(r, PHONE_CHECK_ROUND_GAP_MS))
    }

    const data = await cloudPhoneApi.listPool({ page: 1, page_size: 100 })
    const items = data?.items || []
    const eligible = _sortPoolDevicesForCheck(
      items.filter((p) => _isPoolDeviceNotOffline(p.status)),
    )

    if (!eligible.length) {
      log(`第 ${round} 轮：无非离线设备（已排除 离线/已删除）`)
      if (round === PHONE_CHECK_MAX_ROUNDS) {
        throw new Error(
          '当前账号下无非离线云手机，请到「云手机管理」创建或恢复设备后再试。',
        )
      }
      continue
    }

    log(`第 ${round} 轮：待检查 ${eligible.length} 台（非离线，按状态与 ADB 优先）`)

    for (let i = 0; i < eligible.length; i++) {
      const c = eligible[i]
      const name = c.phone_name || c.phone_id
      const st = c.status || '-'
      const adbInfo = c.adb_host_port ? `ADB ${c.adb_host_port}` : '未配置 ADB 端口'
      log(`[${i + 1}/${eligible.length}] ${name} · 状态 ${st} · ${adbInfo}`)

      if (i > 0) {
        await new Promise((r) => setTimeout(r, PHONE_CHECK_DEVICE_GAP_MS))
      }

      try {
        const info = await cloudPhoneApi.checkHealth(c.phone_id)
        if (info?.is_healthy) {
          photoHealthPhoneCache.value = c.phone_id
          log(`→ 健康检查通过，已选用 ${c.phone_id}`)
          return
        }
        log('→ 未通过（is_healthy=false），后台可能已将状态更新为离线等')
      } catch (e) {
        log(`→ 请求失败：${httpErrorDetail(e) || e?.message || '未知错误'}`)
      }
    }

    if (round < PHONE_CHECK_MAX_ROUNDS) {
      log(`第 ${round} 轮结束仍无可用设备，将进入下一轮`)
    }
  }

  throw new Error(
    `已对非离线设备完成 ${PHONE_CHECK_MAX_ROUNDS} 轮健康检查，仍无可用设备。请到「云手机管理」排查或稍后重试。`,
  )
}

/**
 * 每笔拍照购任务最多入库几条拼多多候选（对应接口 max_candidates）。
 * 勿用 `|| 默认`：0/falsy 会与默认混淆。
 */
function resolvePhotoMaxCandidates() {
  const v = photoBatchMaxItems.value
  if (v === null || v === undefined || v === '') {
    return PHOTO_BATCH_DEFAULT_MAX
  }
  const n = Math.floor(Number(v))
  if (!Number.isFinite(n)) {
    return PHOTO_BATCH_DEFAULT_MAX
  }
  return Math.min(Math.max(1, n), 50)
}

async function refreshProductRow(productId) {
  try {
    const updated = await productApi.get(productId)
    const index = store.list.findIndex(p => p.id === productId)
    if (index !== -1) {
      store.list[index] = updated
    }
  } catch (e) {
    console.error('刷新商品行失败', productId, e)
  }
}

async function startBatchPhotoSearch() {
  if (photoBatchRunning.value) return
  const keys = [...selectedRowKeys.value]
  if (!keys.length) {
    message.warning('请先勾选要执行拍照购的商品')
    return
  }
  const rows = store.list.filter(r => keys.includes(r.id))
  const ordered = keys.map(id => rows.find(r => r.id === id)).filter(Boolean)

  /** 本批依次执行：所有勾选且有主图的 TikTok 商品；「每笔最多入库」只限制 max_candidates，不限制本批行数 */
  const validAll = ordered.filter(r => r.main_image_url)
  const toRun = validAll

  Object.keys(photoRowProgress).forEach((k) => {
    delete photoRowProgress[k]
  })

  const bt = toRun.length
  ordered.forEach((r, i) => {
    const orderIndex = i + 1
    if (!r.main_image_url) {
      photoRowProgress[r.id] = {
        phase: 'skipped',
        orderIndex,
        batchTotal: bt,
        stepText: '无主图，已跳过',
      }
      return
    }
    const qi = validAll.findIndex((x) => x.id === r.id) + 1
    photoRowProgress[r.id] = {
      phase: 'queued',
      orderIndex: qi,
      batchTotal: bt,
      stepText: `排队中（${qi}/${bt}）`,
    }
  })

  if (!validAll.length) {
    message.warning('勾选的商品均无主图，无法拍照购')
    return
  }
  if (!toRun.length) {
    message.warning('本批次可执行商品数为 0')
    return
  }

  photoBatchRunning.value = true
  try {
    for (const r of toRun) {
      const pid = r.id
      let photoTaskId = null
      let lastFailMsg = ''

      for (let attempt = 1; attempt <= PHOTO_BATCH_MAX_ATTEMPTS; attempt++) {
        const isRetry = attempt > 1
        photoRowProgress[pid] = {
          ...photoRowProgress[pid],
          phase: 'running',
          stepText: isRetry
            ? `第 ${attempt}/${PHOTO_BATCH_MAX_ATTEMPTS} 次重试：检查云手机…`
            : '检查云手机…',
          task: null,
        }

        if (isRetry) {
          photoHealthPhoneCache.value = null
          await new Promise((res) => setTimeout(res, PHOTO_BATCH_RETRY_GAP_MS))
        }

        try {
          await ensureUserCloudPhoneReady({
            onLog: (hint) => {
              photoRowProgress[pid].stepText = hint
            },
          })
        } catch (err) {
          lastFailMsg = err?.message || '云手机不可用'
          if (attempt >= PHOTO_BATCH_MAX_ATTEMPTS) {
            photoRowProgress[pid].phase = 'failed'
            photoRowProgress[pid].stepText = `已重试 ${PHOTO_BATCH_MAX_ATTEMPTS} 次：${lastFailMsg}`
          }
          continue
        }

        photoRowProgress[pid].stepText = photoTaskId && isRetry ? '重新提交任务…' : '创建任务…'

        let task
        try {
          if (photoTaskId && isRetry) {
            task = await photoSearchApi.retryTask(photoTaskId)
          } else {
            task = await photoSearchApi.createTask({
              product_id: pid,
              fetch_pdd_links: photoBatchFetchPddLinks.value,
              max_candidates: resolvePhotoMaxCandidates(),
            })
          }
          photoTaskId = task.id
        } catch (e) {
          if (e?.status === 409) {
            photoRowProgress[pid].stepText = '检测到已有任务，接续进度…'
            try {
              const tasks = await photoSearchApi.getTasksByProduct(pid)
              task = tasks?.find(t => PHOTO_POLL_ACTIVE.has(t.status)) || tasks?.[0]
            } catch {
              task = null
            }
            if (!task) {
              lastFailMsg = e?.message || '已有任务但无法获取状态'
              if (attempt >= PHOTO_BATCH_MAX_ATTEMPTS) {
                photoRowProgress[pid].phase = 'failed'
                photoRowProgress[pid].stepText = lastFailMsg
              }
              continue
            }
            photoTaskId = task.id
          } else {
            lastFailMsg = httpErrorDetail(e) || e?.message || '创建任务失败'
            if (attempt >= PHOTO_BATCH_MAX_ATTEMPTS) {
              photoRowProgress[pid].phase = 'failed'
              photoRowProgress[pid].stepText = lastFailMsg
            }
            continue
          }
        }

        photoRowProgress[pid].task = task
        photoRowProgress[pid].stepText = formatPhotoTaskLine(task)

        const finalTask = await pollPhotoTaskUntilDone(task.id, (t) => {
          photoRowProgress[pid].task = t
          photoRowProgress[pid].stepText = formatPhotoTaskLine(t)
        })

        if (finalTask.status === 'success') {
          photoRowProgress[pid].phase = 'done'
          photoRowProgress[pid].stepText =
            `完成 · 本商品 候选 ${finalTask.candidates_found}，入库 ${finalTask.candidates_saved}`
          photoRowProgress[pid].task = finalTask
          try {
            await photoSearchApi.syncTaskImages(finalTask.id)
          } catch { /* 同步失败不阻断 */ }
          await loadPddMatches(pid)
          await refreshProductRow(pid)
          break
        }

        lastFailMsg = finalTask.error_message
          || (finalTask.status === 'cancelled' ? '已取消' : `状态：${finalTask.status}`)

        if (attempt >= PHOTO_BATCH_MAX_ATTEMPTS) {
          photoRowProgress[pid].phase = 'failed'
          photoRowProgress[pid].task = finalTask
          photoRowProgress[pid].stepText = `已重试 ${PHOTO_BATCH_MAX_ATTEMPTS} 次：${lastFailMsg}`
        } else {
          photoRowProgress[pid].stepText = `第 ${attempt} 次未成功，将重试（${lastFailMsg}）`
        }
      }
    }

    message.success('批量拍照购已执行完毕')
    await store.fetchList()
    if (toRun.length) {
      await loadPddMatchesBatch(toRun.map((x) => x.id))
    }
  } finally {
    photoHealthPhoneCache.value = null
    photoBatchRunning.value = false
  }
}

// --- 展开行 & 拼多多匹配 ---
const expandedRowKeys = ref([])
const pddMatchesMap = reactive({})
const pddMatchesLoading = reactive({})

function expandAllPddRows() {
  if (!store.list?.length) return
  const ids = store.list.map(p => p.id)
  expandedRowKeys.value = [...ids]
  ids.forEach((id) => {
    if (pddMatchesMap[id] === undefined) {
      loadPddMatches(id)
    }
  })
}

function collapseAllPddRows() {
  expandedRowKeys.value = []
}

function toggleExpand(productId) {
  const idx = expandedRowKeys.value.indexOf(productId)
  if (idx >= 0) {
    expandedRowKeys.value = expandedRowKeys.value.filter(k => k !== productId)
  } else {
    expandedRowKeys.value = [...expandedRowKeys.value, productId]
    if (!pddMatchesMap[productId]) {
      loadPddMatches(productId)
    }
  }
}

function onExpand(expanded, record) {
  if (expanded) {
    if (!expandedRowKeys.value.includes(record.id)) {
      expandedRowKeys.value = [...expandedRowKeys.value, record.id]
    }
    if (!pddMatchesMap[record.id]) {
      loadPddMatches(record.id)
    }
  } else {
    expandedRowKeys.value = expandedRowKeys.value.filter(k => k !== record.id)
  }
}

async function loadPddMatches(productId) {
  pddMatchesLoading[productId] = true
  try {
    const data = await pddApi.getMatches(productId)
    pddMatchesMap[productId] = data
  } catch {
    pddMatchesMap[productId] = []
  } finally {
    pddMatchesLoading[productId] = false
  }
}

/** 每批 ID 数量：避免 product_ids 查询串过长被网关/浏览器截断 */
const PD_MATCH_BATCH_SIZE = 50

async function loadPddMatchesBatch(productIds) {
  if (!productIds.length) return
  try {
    for (let i = 0; i < productIds.length; i += PD_MATCH_BATCH_SIZE) {
      const chunk = productIds.slice(i, i + PD_MATCH_BATCH_SIZE)
      const data = await pddApi.getMatchesBatch(chunk)
      for (const [pid, matches] of Object.entries(data)) {
        pddMatchesMap[pid] = matches
      }
    }
  } catch {}
}

async function setPrimaryInList(record, m) {
  try {
    await pddApi.updateMatch(m.id, { is_primary: 1 })
    if (pddMatchesMap[record.id]) {
      pddMatchesMap[record.id].forEach(x => x.is_primary = x.id === m.id ? 1 : 0)
    }
    // 刷新当前商品数据以获取更新后的利润
    const updatedProduct = await productApi.get(record.id)
    const index = store.list.findIndex(p => p.id === record.id)
    if (index !== -1) {
      store.list[index] = updatedProduct
    }
    message.success('已设为主参照')
  } catch (e) {
    message.error(e?.message || '设置失败')
  }
}

async function deleteMatchInList(record, m) {
  try {
    await pddApi.deleteMatch(m.id)
    const list = pddMatchesMap[record.id]
    if (list) {
      pddMatchesMap[record.id] = list.filter(x => x.id !== m.id)
    }
    // 刷新当前商品数据以获取更新后的利润
    const updatedProduct = await productApi.get(record.id)
    const index = store.list.findIndex(p => p.id === record.id)
    if (index !== -1) {
      store.list[index] = updatedProduct
    }
    message.success('已删除该拼多多匹配')
  } catch (e) {
    message.error(e?.message || '删除失败')
  }
}

watch(() => store.list, (newList) => {
  if (newList?.length) {
    const idSet = new Set(newList.map(p => p.id))
    loadPddMatchesBatch([...idSet])
    expandedRowKeys.value = expandedRowKeys.value.filter(k => idSet.has(k))
  } else {
    expandedRowKeys.value = []
  }
}, { immediate: false })

// --- 原有逻辑 ---
function getShopUrl(record) {
  const url = record.tiktok_url || ''
  const m = url.match(/(https?:\/\/[^/]+\/@[^/]+)/)
  if (m) return m[1]
  if (record.shop_id) return `https://www.tiktok.com/shop/seller-${record.shop_id}`
  return ''
}

const columns = [
  { title: '商品', key: 'product', fixed: 'left', width: 400 },
  { title: 'TikTok 价格', key: 'price', width: 140 },
  { title: '销量', key: 'sales_volume', width: 90, sorter: true, dataIndex: 'sales_volume' },
  { title: '评分', dataIndex: 'rating', width: 70 },
  { title: '拼多多匹配', key: 'pdd_toggle', width: 110 },
  { title: '预估利润', key: 'profit', width: 100, sorter: true, dataIndex: 'estimated_profit' },
  { title: '预估利润率', key: 'profit_rate', width: 100, sorter: true, dataIndex: 'profit_rate' },
  { title: '选品状态', key: 'status', width: 100 },
  { title: '备注', dataIndex: 'remark', width: 120, ellipsis: true },
  { title: '添加时间', dataIndex: 'created_at', width: 150, sorter: true },
  { title: '操作', key: 'action', fixed: 'right', width: 160 },
]

const pagination = computed(() => ({
  current: store.filters.page,
  pageSize: store.filters.page_size,
  total: store.total,
  showSizeChanger: true,
  showTotal: t => `共 ${t} 条`,
  pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
}))

function onSearch() {
  store.filters.page = 1
  store.fetchList()
}

function onTableChange(pag, _, sorter) {
  store.filters.page = pag.current
  store.filters.page_size = pag.pageSize
  if (sorter.field) {
    store.filters.order_by = sorter.field
    store.filters.order_dir = sorter.order === 'ascend' ? 'asc' : 'desc'
  }
  store.fetchList()
}

/** 与后端 export_service.EXPORT_COLUMNS 的 key、顺序保持一致 */
const exportFieldOptions = [
  { key: 'id', label: '商品ID' },
  { key: 'tiktok_product_id', label: 'TikTok商品ID' },
  { key: 'title', label: '商品标题' },
  { key: 'description', label: '商品描述' },
  { key: 'tiktok_url', label: 'TikTok链接' },
  { key: 'main_image_url', label: '主图URL' },
  { key: 'region', label: '区域代码' },
  { key: 'region_label', label: '区域' },
  { key: 'category', label: '分类' },
  { key: 'price', label: 'TikTok售价' },
  { key: 'currency', label: '货币' },
  { key: 'price_cny', label: '折合人民币' },
  { key: 'original_price', label: '原价' },
  { key: 'discount', label: '折扣' },
  { key: 'sales_volume', label: '销量' },
  { key: 'rating', label: '评分' },
  { key: 'review_count', label: '评价数' },
  { key: 'stock_status', label: '库存状态' },
  { key: 'shop_name', label: '店铺名称' },
  { key: 'shop_id', label: '店铺ID' },
  { key: 'seller_location', label: '卖家地区' },
  { key: 'shipping_fee', label: '运费' },
  { key: 'free_shipping', label: '是否包邮' },
  { key: 'delivery_days_min', label: '配送天数(最少)' },
  { key: 'delivery_days_max', label: '配送天数(最多)' },
  { key: 'status', label: '选品状态代码' },
  { key: 'status_label', label: '选品状态' },
  { key: 'remark', label: '备注' },
  { key: 'estimated_profit', label: '预估利润' },
  { key: 'profit_rate', label: '预估利润率' },
  { key: 'pdd_price', label: '拼多多价格(主匹配)' },
  { key: 'pdd_shop_name', label: '拼多多店铺(主匹配)' },
  { key: 'pdd_product_url', label: '拼多多商品链接(主匹配)' },
  { key: 'pdd_title', label: '拼多多标题(主匹配)' },
  { key: 'latest_profit', label: '最新核算利润' },
  { key: 'latest_profit_rate', label: '最新核算利润率' },
  { key: 'created_at', label: '添加时间' },
  { key: 'updated_at', label: '更新时间' },
]

const LS_EXPORT_FIELDS = 'gp_export_field_keys'

const DEFAULT_EXPORT_FIELDS = exportFieldOptions
  .map(o => o.key)
  .filter(k => k !== 'description')

function normalizeExportFieldKeys(keys) {
  if (!Array.isArray(keys) || !keys.length) return null
  const valid = new Set(exportFieldOptions.map(o => o.key))
  const filtered = keys.filter(k => valid.has(k))
  return filtered.length ? filtered : null
}

function readStoredExportFields() {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(LS_EXPORT_FIELDS)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return normalizeExportFieldKeys(parsed)
  } catch {
    return null
  }
}

const exportModalOpen = ref(false)
const exportSubmitting = ref(false)
const exportSelectedFields = ref([...DEFAULT_EXPORT_FIELDS])

async function openExportModal() {
  const n = selectedRowKeys.value.length
  if (!n) {
    message.warning('请先勾选要导出的商品')
    return
  }
  let fields = readStoredExportFields()
  if (!fields) {
    try {
      const data = await userApi.getExportFieldPreferences()
      fields = normalizeExportFieldKeys(data?.export_product_field_keys)
    } catch {
      /* 忽略，使用默认列 */
    }
  }
  exportSelectedFields.value = fields?.length ? [...fields] : [...DEFAULT_EXPORT_FIELDS]
  exportModalOpen.value = true
}

function selectAllExportFields() {
  exportSelectedFields.value = exportFieldOptions.map(o => o.key)
}

function clearExportFields() {
  exportSelectedFields.value = []
}

function resetExportFields() {
  exportSelectedFields.value = [...DEFAULT_EXPORT_FIELDS]
}

async function confirmExport() {
  if (!exportSelectedFields.value.length) {
    message.warning('请至少选择一列导出')
    return false
  }
  const ids = [...selectedRowKeys.value]
  if (!ids.length) {
    message.warning('请先勾选要导出的商品')
    return false
  }
  exportSubmitting.value = true
  try {
    await exportApi.exportProductsExcel(ids, exportSelectedFields.value)
    try {
      localStorage.setItem(LS_EXPORT_FIELDS, JSON.stringify(exportSelectedFields.value))
    } catch {
      /* ignore */
    }
    userApi.putExportFieldPreferences({
      export_product_field_keys: exportSelectedFields.value,
    }).catch(() => {})
    exportModalOpen.value = false
  } catch {
    /* 错误提示在 exportApi 内；返回 rejected Promise 避免 Modal 误关 */
    return Promise.reject(new Error('export failed'))
  } finally {
    exportSubmitting.value = false
  }
}

async function recrawl(record) {
  if (recrawlingIds.value.has(record.id)) return
  if (!record.crawl_task_id) {
    message.warning('该商品无采集任务')
    return
  }
  recrawlingIds.value = new Set([...recrawlingIds.value, record.id])
  try {
    await taskApi.retry(record.crawl_task_id)
    const finalTask = await pollCrawlTaskUntilDone(record.crawl_task_id, () => {})
    if (finalTask.status === 'done') {
      const updated = finalTask.product ?? await productApi.get(record.id)
      const index = store.list.findIndex(p => p.id === record.id)
      if (index !== -1) {
        store.list[index] = updated
      }
      message.success('采集完成，商品信息已更新')
    } else {
      message.error(finalTask.error_msg || '采集失败')
    }
  } catch (e) {
    message.error(e?.message || '采集失败')
  } finally {
    recrawlingIds.value = new Set([...recrawlingIds.value].filter(i => i !== record.id))
  }
}

onMounted(async () => {
  await store.fetchList()
  if (store.list.length) {
    const ids = store.list.map(p => p.id)
    await loadPddMatchesBatch(ids)
  }
})
</script>

<style scoped>
.filter-card { border-radius: 8px; text-align: left; }
.filter-card :deep(.ant-row) { justify-content: flex-start; }
.photo-batch-toolbar-row {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
}
.toolbar-muted {
  font-size: 13px;
  font-weight: 500;
  color: #595959;
}
.toolbar-hint {
  font-size: 12px;
  color: #8c8c8c;
}
.expand-col-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 0;
  line-height: 1.2;
}
.expand-col-link {
  font-size: 12px;
  color: #1677ff;
  cursor: pointer;
  white-space: nowrap;
}
.expand-col-link:hover {
  color: #4096ff;
}

.export-modal-summary {
  margin-bottom: 12px;
  color: #595959;
  font-size: 13px;
  line-height: 1.6;
}
.export-field-toolbar {
  margin-bottom: 10px;
}
.export-checkbox-group {
  width: 100%;
  max-height: 420px;
  overflow-y: auto;
  padding: 4px 0;
}
.range-filter {
  display: flex; align-items: center; gap: 4px;
}
.range-label {
  font-size: 12px; color: #666; white-space: nowrap; flex-shrink: 0;
}
.range-sep { color: #ccc; }

.product-cell { display: flex; align-items: center; gap: 12px; }
.img-placeholder {
  width: 80px; height: 80px; background: #f5f5f5; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #bbb; font-size: 24px; flex-shrink: 0;
}
.product-info { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.product-title {
  font-weight: 500; color: #1677ff; cursor: pointer;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 240px;
}
.product-title:hover { text-decoration: underline; }
.product-meta { display: flex; align-items: center; gap: 6px; }
.photo-batch-row {
  margin-top: 6px;
  max-width: 300px;
  font-size: 12px;
  line-height: 1.45;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}
.photo-batch-muted { color: #999; }
.photo-batch-active { color: #1677ff; font-weight: 500; }
.photo-batch-done-text { color: #52c41a; font-weight: 500; }
.photo-batch-err-text { color: #ff4d4f; }
.photo-batch-ok { color: #52c41a; margin-right: 4px; }
.photo-batch-err { color: #ff4d4f; margin-right: 4px; }
.shop { color: #999; font-size: 12px; text-decoration: none; }
a.shop:hover { color: #1677ff; }
.price-tiktok { font-weight: 600; color: #1a1a1a; }
.price-cny { color: #999; font-size: 12px; margin-top: 2px; }
.sales { color: #1677ff; font-weight: 500; }
.no-data { color: #ccc; }
.profit-rate-text { font-size: 12px; color: #999; margin-top: 2px; }

/* 展开行 - 拼多多匹配 */
.pdd-expand-wrapper {
  padding: 6px 0 6px 92px;
}
.pdd-expand-empty {
  color: #999; font-size: 13px; padding: 8px 0;
}
.pdd-match-list {
  display: flex; flex-direction: column; gap: 8px;
}
.pdd-match-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; border-radius: 8px;
  border: 1px solid #f0f0f0; background: #fafafa;
  transition: all .2s;
}
.pdd-match-row:hover {
  border-color: #d9d9d9;
}
.pdd-match-row.is-primary {
  border-color: #1677ff; background: #f0f7ff;
}
.pdd-img-placeholder {
  width: 56px; height: 56px; background: #f0f0f0; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: #ccc; font-size: 16px; flex-shrink: 0;
}
.pdd-match-info { flex: 1; min-width: 0; }
.pdd-match-title {
  font-size: 13px; font-weight: 500; color: #333;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  display: block; max-width: 360px;
}
.pdd-match-meta {
  display: flex; gap: 10px; align-items: center; font-size: 12px; margin-top: 4px;
}
.pdd-price { font-weight: 600; color: #e62e2e; font-size: 14px; }
.pdd-sales { color: #999; }
.pdd-shop { color: #999; }
.pdd-link { color: #1677ff; font-size: 12px; }
.pdd-match-tags { display: flex; gap: 4px; flex-shrink: 0; }
.pdd-match-actions { flex-shrink: 0; }

/* 分页「每页条数」：选择器与下拉层加宽，避免 1000/page 等文案被截断 */
.product-list-page :deep(.ant-pagination-options-size-changer .ant-select-selector) {
  min-width: 118px;
}
.product-list-page :deep(.ant-pagination-options .ant-select-dropdown) {
  min-width: 148px !important;
}
.product-list-page :deep(.ant-pagination-options .ant-select-item-option-content) {
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}
</style>
