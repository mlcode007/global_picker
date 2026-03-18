<template>
  <div>
    <!-- 过滤栏 -->
    <a-card class="filter-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="6">
          <a-input-search
            v-model:value="store.filters.keyword"
            placeholder="搜索商品标题 / 店铺"
            allow-clear
            @search="onSearch"
          />
        </a-col>
        <a-col :span="4">
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
        <a-col :span="4">
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
        <a-col :flex="1" style="text-align:right">
          <a-space>
            <a-button @click="onSearch"><ReloadOutlined /> 刷新</a-button>
            <a-button type="primary" ghost @click="exportAll"><DownloadOutlined /> 导出 Excel</a-button>
            <a-button type="primary" @click="router.push('/import')"><ImportOutlined /> 批量导入</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 数据表格 -->
    <a-card :bordered="false" style="margin-top: 16px">
      <a-table
        :columns="columns"
        :data-source="store.list"
        :loading="store.loading"
        :pagination="pagination"
        row-key="id"
        :scroll="{ x: 1300 }"
        @change="onTableChange"
      >
        <!-- 商品信息列 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'product'">
            <div class="product-cell">
              <a-image
                v-if="record.main_image_url"
                :src="record.main_image_url"
                :width="56"
                :height="56"
                style="object-fit:cover;border-radius:4px;flex-shrink:0"
                :preview="true"
                :fallback="fallbackImg"
              />
              <div v-else class="img-placeholder"><PictureOutlined /></div>
              <div class="product-info">
                <a @click="router.push(`/products/${record.id}`)" class="product-title">
                  {{ record.title || '（待抓取）' }}
                </a>
                <div class="product-meta">
                  <a-tag size="small">{{ record.seller_location || record.region }}</a-tag>
                  <a v-if="record.shop_name" :href="getShopUrl(record)" target="_blank" rel="noopener" class="shop" @click.stop>
                    {{ record.shop_name }}
                  </a>
                  <span v-else class="shop">—</span>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="column.key === 'price'">
            <div>
              <span class="price-tiktok">{{ record.currency }} {{ record.price }}</span>
              <a-tag v-if="record.discount" color="red" size="small" style="margin-left:4px">{{ record.discount }}</a-tag>
              <div v-if="record.price_cny" class="price-cny">≈ ¥{{ record.price_cny }}</div>
            </div>
          </template>

          <template v-else-if="column.key === 'sales_volume'">
            <span class="sales">{{ record.sales_volume?.toLocaleString() }}</span>
          </template>

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
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined, DownloadOutlined, ImportOutlined, PictureOutlined, SyncOutlined,
} from '@ant-design/icons-vue'
import { useProductStore } from '@/stores/product'
import { exportApi, taskApi } from '@/api/products'
import { STATUS_MAP, REGION_MAP } from '@/utils'

const router = useRouter()
const store = useProductStore()
const recrawlingIds = ref(new Set())

const fallbackImg = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTYiIGhlaWdodD0iNTYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+'

function getShopUrl(record) {
  const url = record.tiktok_url || ''
  const m = url.match(/(https?:\/\/[^/]+\/@[^/]+)/)
  if (m) return m[1]
  if (record.shop_id) return `https://www.tiktok.com/shop/seller-${record.shop_id}`
  return ''
}

const columns = [
  { title: '商品', key: 'product', fixed: 'left', width: 320 },
  { title: 'TikTok 价格', key: 'price', width: 130 },
  { title: '销量', key: 'sales_volume', width: 100, sorter: true, dataIndex: 'sales_volume' },
  { title: '评分', dataIndex: 'rating', width: 80 },
  { title: '选品状态', key: 'status', width: 110 },
  { title: '备注', dataIndex: 'remark', width: 150, ellipsis: true },
  { title: '添加时间', dataIndex: 'created_at', width: 160, sorter: true },
  { title: '操作', key: 'action', fixed: 'right', width: 180 },
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

onMounted(() => store.fetchList())
</script>

<style scoped>
.filter-card { border-radius: 8px; }
.product-cell { display: flex; align-items: center; gap: 12px; }
.img-placeholder {
  width: 56px; height: 56px; background: #f5f5f5; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  color: #bbb; font-size: 20px; flex-shrink: 0;
}
.product-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.product-title {
  font-weight: 500; color: #1677ff; cursor: pointer;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px;
}
.product-title:hover { text-decoration: underline; }
.product-meta { display: flex; align-items: center; gap: 6px; }
.shop { color: #999; font-size: 12px; text-decoration: none; }
a.shop:hover { color: #1677ff; }
.price-tiktok { font-weight: 600; color: #1a1a1a; }
.price-cny { color: #999; font-size: 12px; }
.sales { color: #1677ff; font-weight: 500; }
</style>
