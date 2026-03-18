<template>
  <div class="dashboard">
    <a-spin :spinning="loading" tip="加载统计数据...">
      <!-- 顶部概览卡片 -->
      <a-row :gutter="[16, 16]">
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card class="stat-card stat-card--product" hoverable>
            <a-statistic title="商品总数" :value="stats.products?.total || 0">
              <template #prefix><ShoppingOutlined /></template>
            </a-statistic>
            <div class="stat-footer">
              <span class="stat-badge stat-badge--up" v-if="stats.products?.today">
                今日 +{{ stats.products.today }}
              </span>
              <span class="stat-badge" v-else>今日暂无新增</span>
              <span class="stat-sub">本周 +{{ stats.products?.week || 0 }}</span>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card class="stat-card stat-card--match" hoverable>
            <a-statistic title="拼多多匹配" :value="stats.pdd_matches?.total || 0">
              <template #prefix><LinkOutlined /></template>
            </a-statistic>
            <div class="stat-footer">
              <span class="stat-badge">
                匹配率 {{ formatPercent(stats.pdd_matches?.match_rate) }}
              </span>
              <span class="stat-sub">已确认 {{ stats.pdd_matches?.confirmed || 0 }}</span>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card class="stat-card stat-card--profit" hoverable>
            <a-statistic
              title="平均利润率"
              :value="formatPercent(stats.profit?.avg_profit_rate)"
              :value-style="{ color: profitRateColor(stats.profit?.avg_profit_rate || 0) }"
            >
              <template #prefix><FundOutlined /></template>
            </a-statistic>
            <div class="stat-footer">
              <span class="stat-badge">
                盈利 {{ stats.profit?.positive_count || 0 }} / {{ stats.profit?.products_calculated || 0 }}
              </span>
              <span class="stat-sub">高利润 {{ stats.profit?.high_margin_count || 0 }}</span>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card class="stat-card stat-card--task" hoverable>
            <a-statistic title="采集任务" :value="stats.crawl_tasks?.total || 0">
              <template #prefix><ThunderboltOutlined /></template>
            </a-statistic>
            <div class="stat-footer">
              <a-tag v-if="crawlRunning > 0" color="processing">{{ crawlRunning }} 运行中</a-tag>
              <a-tag v-if="crawlFailed > 0" color="error">{{ crawlFailed }} 失败</a-tag>
              <a-tag v-if="crawlPending > 0" color="default">{{ crawlPending }} 等待</a-tag>
              <a-tag v-if="crawlRunning === 0 && crawlFailed === 0 && crawlPending === 0" color="success">空闲</a-tag>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 第二行: 商品状态 + 区域分布 + 比价来源 -->
      <a-row :gutter="[16, 16]" style="margin-top: 16px">
        <a-col :xs="24" :lg="8">
          <a-card title="商品选品状态" class="chart-card">
            <template #extra>
              <a-tag>共 {{ stats.products?.total || 0 }} 件</a-tag>
            </template>
            <div class="status-grid">
              <div
                v-for="item in productStatusList"
                :key="item.key"
                class="status-item"
              >
                <div class="status-item__bar">
                  <div
                    class="status-item__fill"
                    :style="{
                      width: statusPercent(item.count) + '%',
                      background: item.barColor,
                    }"
                  />
                </div>
                <div class="status-item__info">
                  <a-badge :color="item.dotColor" :text="item.label" />
                  <span class="status-item__count">{{ item.count }}</span>
                </div>
              </div>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="8">
          <a-card title="销售区域分布" class="chart-card">
            <div class="region-grid">
              <div
                v-for="item in regionList"
                :key="item.code"
                class="region-item"
              >
                <div class="region-item__flag">{{ item.flag }}</div>
                <div class="region-item__info">
                  <div class="region-item__name">{{ item.name }}</div>
                  <div class="region-item__count">{{ item.count }} 件</div>
                </div>
                <a-progress
                  :percent="regionPercent(item.count)"
                  :show-info="false"
                  :stroke-color="item.color"
                  size="small"
                  style="flex: 1; margin-left: 8px"
                />
              </div>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="8">
          <a-card title="比价来源分布" class="chart-card">
            <div class="source-grid">
              <div
                v-for="item in matchSourceList"
                :key="item.key"
                class="source-item"
              >
                <div class="source-item__icon" :style="{ background: item.color }">
                  <component :is="item.icon" />
                </div>
                <div class="source-item__info">
                  <div class="source-item__label">{{ item.label }}</div>
                  <div class="source-item__value">{{ item.count }}</div>
                </div>
              </div>
            </div>
            <a-divider style="margin: 12px 0" />
            <div class="source-summary">
              <a-statistic title="有匹配商品" :value="stats.pdd_matches?.products_with_match || 0" :value-style="{ fontSize: '20px' }" />
              <a-statistic title="匹配率" :value="formatPercent(stats.pdd_matches?.match_rate)" :value-style="{ fontSize: '20px' }" />
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 第三行: 每日趋势 + 拍照购 + 设备状态 -->
      <a-row :gutter="[16, 16]" style="margin-top: 16px">
        <a-col :xs="24" :lg="12">
          <a-card title="近 7 天商品新增趋势" class="chart-card">
            <div class="trend-chart">
              <div
                v-for="(day, idx) in stats.daily_trend || []"
                :key="idx"
                class="trend-bar-group"
              >
                <div class="trend-value">{{ day.count }}</div>
                <div class="trend-bar-wrapper">
                  <div
                    class="trend-bar"
                    :style="{ height: trendBarHeight(day.count) + '%' }"
                  />
                </div>
                <div class="trend-label">{{ day.date }}</div>
              </div>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="6">
          <a-card title="拍照购任务" class="chart-card">
            <a-statistic
              title="成功率"
              :value="formatPercent(stats.photo_search?.success_rate)"
              :value-style="{ fontSize: '28px', color: '#1677ff' }"
              style="text-align: center; margin-bottom: 16px"
            />
            <div class="photo-stats">
              <div v-for="item in photoStatusList" :key="item.key" class="photo-stat-row">
                <a-badge :status="item.badge" :text="item.label" />
                <span>{{ item.count }}</span>
              </div>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="6">
          <a-card title="设备状态" class="chart-card">
            <div class="device-grid">
              <div
                v-for="item in deviceStatusList"
                :key="item.key"
                class="device-item"
              >
                <div class="device-item__dot" :style="{ background: item.color }" />
                <span class="device-item__label">{{ item.label }}</span>
                <span class="device-item__count">{{ item.count }}</span>
              </div>
            </div>
            <a-divider style="margin: 12px 0" />
            <a-statistic
              title="设备总数"
              :value="stats.devices?.total || 0"
              :value-style="{ fontSize: '24px' }"
              style="text-align: center"
            />
          </a-card>
        </a-col>
      </a-row>

      <!-- 第四行: 利润分析 + 最新商品 -->
      <a-row :gutter="[16, 16]" style="margin-top: 16px">
        <a-col :xs="24" :lg="8">
          <a-card title="利润分析概览" class="chart-card">
            <div class="profit-overview">
              <div class="profit-metric">
                <div class="profit-metric__label">已计算利润商品</div>
                <div class="profit-metric__value">{{ stats.profit?.products_calculated || 0 }}</div>
              </div>
              <div class="profit-metric">
                <div class="profit-metric__label">平均利润 (CNY)</div>
                <div class="profit-metric__value" :style="{ color: (stats.profit?.avg_profit || 0) >= 0 ? '#52c41a' : '#ff4d4f' }">
                  ¥{{ stats.profit?.avg_profit || 0 }}
                </div>
              </div>
              <div class="profit-metric">
                <div class="profit-metric__label">平均利润率</div>
                <div class="profit-metric__value" :style="{ color: profitRateColor(stats.profit?.avg_profit_rate || 0) }">
                  {{ formatPercent(stats.profit?.avg_profit_rate) }}
                </div>
              </div>
              <div class="profit-metric">
                <div class="profit-metric__label">盈利商品</div>
                <div class="profit-metric__value" style="color: #52c41a">
                  {{ stats.profit?.positive_count || 0 }}
                </div>
              </div>
              <div class="profit-metric">
                <div class="profit-metric__label">高利润率 (≥20%)</div>
                <div class="profit-metric__value" style="color: #1677ff">
                  {{ stats.profit?.high_margin_count || 0 }}
                </div>
              </div>
            </div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="16">
          <a-card title="最近添加的商品" class="chart-card">
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/products')">查看全部</a-button>
            </template>
            <a-table
              :data-source="stats.recent_products || []"
              :columns="recentColumns"
              :pagination="false"
              size="small"
              row-key="id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'product'">
                  <div class="recent-product">
                    <a-image
                      v-if="record.main_image_url"
                      :src="record.main_image_url"
                      :width="40"
                      :height="40"
                      style="border-radius: 6px; object-fit: cover; flex-shrink: 0"
                      :preview="false"
                    />
                    <div class="recent-product__info">
                      <a class="recent-product__title" @click="$router.push(`/products/${record.id}`)">
                        {{ record.title || '未知商品' }}
                      </a>
                    </div>
                  </div>
                </template>
                <template v-if="column.key === 'price'">
                  <div>{{ record.currency }} {{ record.price }}</div>
                  <div v-if="record.price_cny" style="color: #999; font-size: 12px">≈ ¥{{ record.price_cny }}</div>
                </template>
                <template v-if="column.key === 'region'">
                  <a-tag>{{ REGION_MAP[record.region] || record.region }}</a-tag>
                </template>
                <template v-if="column.key === 'status'">
                  <a-tag :color="STATUS_MAP[record.status]?.color">{{ STATUS_MAP[record.status]?.text || record.status }}</a-tag>
                </template>
                <template v-if="column.key === 'sales'">
                  {{ record.sales_volume }}
                </template>
                <template v-if="column.key === 'time'">
                  {{ formatTime(record.created_at) }}
                </template>
              </template>
            </a-table>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  ShoppingOutlined,
  LinkOutlined,
  FundOutlined,
  ThunderboltOutlined,
  CameraOutlined,
  SearchOutlined,
  EditOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { dashboardApi } from '@/api/products'
import { STATUS_MAP, REGION_MAP, profitRateColor } from '@/utils'

const loading = ref(false)
const stats = ref({})

const REGION_FLAGS = {
  PH: '🇵🇭', MY: '🇲🇾', TH: '🇹🇭', SG: '🇸🇬', ID: '🇮🇩', VN: '🇻🇳',
}
const REGION_COLORS = {
  PH: '#1677ff', MY: '#faad14', TH: '#722ed1', SG: '#eb2f96', ID: '#fa541c', VN: '#13c2c2',
}

const crawlRunning = computed(() => stats.value.crawl_tasks?.by_status?.running || 0)
const crawlFailed = computed(() => stats.value.crawl_tasks?.by_status?.failed || 0)
const crawlPending = computed(() => stats.value.crawl_tasks?.by_status?.pending || 0)

const productStatusList = computed(() => {
  const s = stats.value.products?.by_status || {}
  return [
    { key: 'pending', label: '待定', count: s.pending || 0, dotColor: '#d9d9d9', barColor: '#d9d9d9' },
    { key: 'selected', label: '已选', count: s.selected || 0, dotColor: '#52c41a', barColor: '#52c41a' },
    { key: 'abandoned', label: '放弃', count: s.abandoned || 0, dotColor: '#ff4d4f', barColor: '#ff4d4f' },
  ]
})

function statusPercent(count) {
  const total = stats.value.products?.total || 1
  return Math.round((count / total) * 100)
}

const regionList = computed(() => {
  const r = stats.value.products?.by_region || {}
  return Object.entries(r)
    .map(([code, count]) => ({
      code,
      name: REGION_MAP[code] || code,
      flag: REGION_FLAGS[code] || '🌍',
      color: REGION_COLORS[code] || '#1677ff',
      count,
    }))
    .sort((a, b) => b.count - a.count)
})

function regionPercent(count) {
  const total = stats.value.products?.total || 1
  return Math.round((count / total) * 100)
}

const matchSourceList = computed(() => {
  const s = stats.value.pdd_matches?.by_source || {}
  return [
    { key: 'image_search', label: '拍照购', count: s.image_search || 0, color: '#1677ff', icon: CameraOutlined },
    { key: 'keyword_search', label: '关键词搜索', count: s.keyword_search || 0, color: '#722ed1', icon: SearchOutlined },
    { key: 'manual', label: '手动添加', count: s.manual || 0, color: '#faad14', icon: EditOutlined },
  ]
})

const photoStatusList = computed(() => {
  const s = stats.value.photo_search?.by_status || {}
  return [
    { key: 'success', label: '成功', count: s.success || 0, badge: 'success' },
    { key: 'failed', label: '失败', count: s.failed || 0, badge: 'error' },
    { key: 'running', label: '运行中', count: (s.running || 0) + (s.collecting || 0) + (s.parsing || 0) + (s.saving || 0), badge: 'processing' },
    { key: 'queued', label: '排队中', count: (s.queued || 0) + (s.dispatching || 0), badge: 'default' },
    { key: 'cancelled', label: '已取消', count: s.cancelled || 0, badge: 'warning' },
  ]
})

const deviceStatusList = computed(() => {
  const s = stats.value.devices?.by_status || {}
  return [
    { key: 'idle', label: '空闲', count: s.idle || 0, color: '#52c41a' },
    { key: 'busy', label: '忙碌', count: s.busy || 0, color: '#1677ff' },
    { key: 'offline', label: '离线', count: s.offline || 0, color: '#d9d9d9' },
    { key: 'error', label: '异常', count: s.error || 0, color: '#ff4d4f' },
  ]
})

function trendBarHeight(count) {
  const trend = stats.value.daily_trend || []
  const max = Math.max(...trend.map(d => d.count), 1)
  return Math.max((count / max) * 100, 4)
}

function formatPercent(val) {
  if (val === undefined || val === null) return '0%'
  return (parseFloat(val) * 100).toFixed(1) + '%'
}

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

const recentColumns = [
  { title: '商品', key: 'product', width: '35%' },
  { title: '价格', key: 'price', width: '15%' },
  { title: '区域', key: 'region', width: '12%' },
  { title: '状态', key: 'status', width: '12%' },
  { title: '销量', key: 'sales', width: '10%' },
  { title: '添加时间', key: 'time', width: '16%' },
]

async function fetchStats() {
  loading.value = true
  try {
    stats.value = await dashboardApi.getStats()
  } catch (e) {
    message.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
}

/* ── 顶部卡片 ── */
.stat-card {
  border-radius: 10px;
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}
.stat-card--product { border-top: 3px solid #1677ff; }
.stat-card--match   { border-top: 3px solid #722ed1; }
.stat-card--profit  { border-top: 3px solid #52c41a; }
.stat-card--task    { border-top: 3px solid #fa8c16; }

.stat-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #999;
}
.stat-badge {
  padding: 1px 6px;
  border-radius: 4px;
  background: #f5f5f5;
  font-size: 12px;
}
.stat-badge--up {
  background: #f6ffed;
  color: #52c41a;
}
.stat-sub { color: #bbb; }

/* ── 图表卡片 ── */
.chart-card {
  border-radius: 10px;
  height: 100%;
}

/* ── 商品状态 ── */
.status-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.status-item__bar {
  height: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}
.status-item__fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.status-item__info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.status-item__count {
  font-weight: 600;
  font-size: 16px;
  color: #333;
}

/* ── 区域分布 ── */
.region-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.region-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.region-item__flag {
  font-size: 22px;
  width: 30px;
  text-align: center;
}
.region-item__info {
  min-width: 72px;
}
.region-item__name {
  font-size: 13px;
  font-weight: 500;
}
.region-item__count {
  font-size: 11px;
  color: #999;
}

/* ── 比价来源 ── */
.source-grid {
  display: flex;
  gap: 16px;
  justify-content: space-around;
}
.source-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.source-item__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
}
.source-item__info {
  text-align: center;
}
.source-item__label {
  font-size: 12px;
  color: #999;
}
.source-item__value {
  font-size: 20px;
  font-weight: 700;
  color: #333;
}
.source-summary {
  display: flex;
  justify-content: space-around;
}

/* ── 趋势图 ── */
.trend-chart {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  height: 200px;
  padding: 0 8px;
}
.trend-bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  gap: 4px;
}
.trend-value {
  font-size: 12px;
  font-weight: 600;
  color: #333;
}
.trend-bar-wrapper {
  flex: 1;
  width: 32px;
  display: flex;
  align-items: flex-end;
}
.trend-bar {
  width: 100%;
  background: linear-gradient(180deg, #1677ff, #69b1ff);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.6s ease;
}
.trend-label {
  font-size: 11px;
  color: #999;
}

/* ── 拍照购统计 ── */
.photo-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.photo-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

/* ── 设备状态 ── */
.device-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.device-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.device-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.device-item__label {
  flex: 1;
  font-size: 13px;
}
.device-item__count {
  font-weight: 600;
  font-size: 16px;
  color: #333;
}

/* ── 利润概览 ── */
.profit-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profit-metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
}
.profit-metric__label {
  font-size: 13px;
  color: #666;
}
.profit-metric__value {
  font-size: 18px;
  font-weight: 700;
}

/* ── 最近商品表 ── */
.recent-product {
  display: flex;
  align-items: center;
  gap: 10px;
}
.recent-product__title {
  font-size: 13px;
  color: #333;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  cursor: pointer;
}
.recent-product__title:hover {
  color: #1677ff;
}
</style>
