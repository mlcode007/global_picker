<template>
  <div>
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
        <a-col :span="4">
          <div class="range-filter">
            <span class="range-label">TikTok¥</span>
            <a-input-number
              v-model:value="store.filters.price_cny_min"
              placeholder="最低"
              :min="0"
              :precision="0"
              size="small"
              style="width:70px"
              @pressEnter="onSearch"
            />
            <span class="range-sep">-</span>
            <a-input-number
              v-model:value="store.filters.price_cny_max"
              placeholder="最高"
              :min="0"
              :precision="0"
              size="small"
              style="width:70px"
              @pressEnter="onSearch"
            />
          </div>
        </a-col>
        <a-col :span="4">
          <div class="range-filter">
            <span class="range-label">利润¥</span>
            <a-input-number
              v-model:value="store.filters.profit_min"
              placeholder="最低"
              :precision="0"
              size="small"
              style="width:70px"
              @pressEnter="onSearch"
            />
            <span class="range-sep">-</span>
            <a-input-number
              v-model:value="store.filters.profit_max"
              placeholder="最高"
              :precision="0"
              size="small"
              style="width:70px"
              @pressEnter="onSearch"
            />
          </div>
        </a-col>
        <a-col :flex="1" style="text-align:right">
          <a-space>
            <a-button @click="onSearch"><ReloadOutlined /> 刷新</a-button>
            <a-button type="primary" ghost @click="exportAll"><DownloadOutlined /> 导出 Excel</a-button>
            <a-tooltip title="对左侧勾选的商品依次执行拍照购（需有主图），无需进入详情页">
              <a-button
                type="primary"
                ghost
                :loading="photoBatchRunning"
                :disabled="photoBatchRunning || !selectedRowKeys.length"
                @click="startBatchPhotoSearch"
              >
                <CameraOutlined /> 自动拍照购
              </a-button>
            </a-tooltip>
            <a-button type="primary" @click="router.push('/import')"><ImportOutlined /> 批量导入</a-button>
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
              <div v-if="record.profit_rate != null" class="profit-rate-text">
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
                    : recrawlingIds.has(record.id) ? 'color:#faad14;opacity:.7' : 'color:#faad14'"
                  @click="record.crawl_task_id && recrawl(record)"
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
import { exportApi, taskApi, pddApi, photoSearchApi } from '@/api/products'
import { STATUS_MAP, REGION_MAP } from '@/utils'
import { pollPhotoTaskUntilDone, PHOTO_POLL_ACTIVE, formatPhotoTaskLine } from '@/utils/photoSearchTask'

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
  getCheckboxProps: () => ({ disabled: photoBatchRunning.value }),
}))

// --- 列表页批量拍照购（串行）---
const photoBatchRunning = ref(false)
const photoRowProgress = reactive({})

async function startBatchPhotoSearch() {
  if (photoBatchRunning.value) return
  const keys = [...selectedRowKeys.value]
  if (!keys.length) {
    message.warning('请先勾选要执行拍照购的商品')
    return
  }
  const rows = store.list.filter(r => keys.includes(r.id))
  const ordered = keys.map(id => rows.find(r => r.id === id)).filter(Boolean)

  Object.keys(photoRowProgress).forEach((k) => { delete photoRowProgress[k] })

  ordered.forEach((r, i) => {
    const orderIndex = i + 1
    const batchTotal = ordered.length
    if (!r.main_image_url) {
      photoRowProgress[r.id] = {
        phase: 'skipped',
        orderIndex,
        batchTotal,
        stepText: '无主图，已跳过',
      }
    } else {
      photoRowProgress[r.id] = {
        phase: 'queued',
        orderIndex,
        batchTotal,
        stepText: `排队中（${orderIndex}/${batchTotal}）`,
      }
    }
  })

  const valid = ordered.filter(r => r.main_image_url)
  if (!valid.length) {
    message.warning('勾选的商品均无主图，无法拍照购')
    return
  }

  photoBatchRunning.value = true
  try {
    for (const r of valid) {
      const pid = r.id
      photoRowProgress[pid] = {
        ...photoRowProgress[pid],
        phase: 'running',
        stepText: '创建任务…',
        task: null,
      }

      let task
      try {
        task = await photoSearchApi.createTask({ product_id: pid })
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
            photoRowProgress[pid].phase = 'failed'
            photoRowProgress[pid].stepText = e?.message || '已有任务但无法获取状态'
            continue
          }
        } else {
          photoRowProgress[pid].phase = 'failed'
          photoRowProgress[pid].stepText = e?.message || '创建任务失败'
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
        photoRowProgress[pid].stepText = `完成 · 候选 ${finalTask.candidates_found}，入库 ${finalTask.candidates_saved}`
        photoRowProgress[pid].task = finalTask
        try {
          await photoSearchApi.syncTaskImages(finalTask.id)
        } catch { /* 同步失败不阻断 */ }
        await loadPddMatches(pid)
      } else {
        photoRowProgress[pid].phase = 'failed'
        photoRowProgress[pid].task = finalTask
        photoRowProgress[pid].stepText = finalTask.error_message
          || (finalTask.status === 'cancelled' ? '已取消' : `状态：${finalTask.status}`)
      }
    }

    message.success('批量拍照购已执行完毕')
    await store.fetchList()
    await loadPddMatchesBatch(valid.map(r => r.id))
  } finally {
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

async function loadPddMatchesBatch(productIds) {
  if (!productIds.length) return
  try {
    const data = await pddApi.getMatchesBatch(productIds)
    for (const [pid, matches] of Object.entries(data)) {
      pddMatchesMap[pid] = matches
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
    await store.fetchList()
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
    await store.fetchList()
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
  { title: '预估利润', key: 'profit', width: 110, sorter: true, dataIndex: 'estimated_profit' },
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
  pageSizeOptions: ['10', '20', '50', '100'],
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

function exportAll() {
  exportApi.exportExcel()
}

async function recrawl(record) {
  if (recrawlingIds.value.has(record.id)) return
  recrawlingIds.value = new Set([...recrawlingIds.value, record.id])
  try {
    await taskApi.retry(record.crawl_task_id)
    message.success(`已提交重新采集：${record.title || record.tiktok_url}`)
  } catch (e) {
    message.error(e?.message || '提交采集失败')
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
.filter-card { border-radius: 8px; }
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
</style>
