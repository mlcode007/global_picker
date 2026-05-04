<template>
  <div class="exchange-rate-page">
    <a-card title="汇率管理" :bordered="false">
      <template #extra>
        <a-space>
          <a-button type="primary" @click="handleBatchSave" :loading="saving">
            <template #icon><SaveOutlined /></template>
            保存全部
          </a-button>
          <a-button @click="handleRefresh">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </template>

      <a-alert
        message="提示：汇率为全局配置，所有用户共享。修改后缓存将在 5 分钟内自动刷新，或点击「刷新」立即生效。"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />

      <a-table
        :data-source="rates"
        :columns="columns"
        :pagination="false"
        :loading="loading"
        row-key="currency"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'rate_to_cny'">
            <a-input-number
              v-model:value="record.rate_to_cny"
              :min="0.000001"
              :precision="6"
              :step="0.0001"
              style="width: 180px"
              @change="markDirty(record)"
            />
          </template>
          <template v-if="column.key === 'updated_at'">
            {{ formatTime(record.updated_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-button type="link" size="small" @click="handleReset(record)">
              重置
            </a-button>
          </template>
        </template>
      </a-table>

      <div style="margin-top: 16px; text-align: right">
        <a-button type="primary" @click="handleBatchSave" :loading="saving">
          <template #icon><SaveOutlined /></template>
          保存全部
        </a-button>
        <a-button style="margin-left: 8px" @click="handleRefresh">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { profitApi } from '@/api/products'
import http from '@/api/request'

const loading = ref(false)
const saving = ref(false)
const rates = ref([])
const originalRates = ref([])
const dirtyCurrencies = ref(new Set())

const columns = [
  { title: '币种', dataIndex: 'label', key: 'label', width: 160 },
  { title: '汇率（1 单位外币 = ? 人民币）', key: 'rate_to_cny', width: 280 },
  { title: '更新时间', key: 'updated_at', width: 200 },
  { title: '操作', key: 'action', width: 100 },
]

const CURRENCY_LABELS = {
  PHP: '菲律宾比索',
  MYR: '马来西亚令吉',
  THB: '泰国铢',
  SGD: '新加坡元',
  IDR: '印尼盾',
  VND: '越南盾',
  USD: '美元',
  GBP: '英镑',
  JPY: '日元',
  KRW: '韩元',
  BRL: '巴西雷亚尔',
  MXN: '墨西哥比索',
  SAR: '沙特里亚尔',
}

function formatTime(ts) {
  if (!ts) return '-'
  const d = new Date(ts)
  return d.toLocaleString('zh-CN', { hour12: false })
}

async function fetchRates() {
  loading.value = true
  try {
    const res = await profitApi.exchangeRates()
    rates.value = (res || []).map(r => ({
      ...r,
      label: `${CURRENCY_LABELS[r.currency] || r.currency} (${r.currency})`,
    }))
    originalRates.value = JSON.parse(JSON.stringify(rates.value))
    dirtyCurrencies.value.clear()
  } catch (err) {
    message.error('获取汇率列表失败')
  } finally {
    loading.value = false
  }
}

function markDirty(record) {
  dirtyCurrencies.value.add(record.currency)
}

function handleReset(record) {
  const orig = originalRates.value.find(r => r.currency === record.currency)
  if (orig) {
    record.rate_to_cny = orig.rate_to_cny
    dirtyCurrencies.value.delete(record.currency)
  }
}

async function handleBatchSave() {
  if (dirtyCurrencies.value.size === 0) {
    message.info('没有需要保存的变更')
    return
  }
  saving.value = true
  try {
    const payload = {}
    rates.value.forEach(r => {
      if (dirtyCurrencies.value.has(r.currency)) {
        payload[r.currency] = r.rate_to_cny
      }
    })
    await http.put('/profit/exchange-rates', { rates: payload })
    message.success(`成功更新 ${Object.keys(payload).length} 个汇率`)
    await fetchRates()
  } catch (err) {
    message.error('保存失败：' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}

function handleRefresh() {
  fetchRates()
  message.success('已刷新')
}

onMounted(() => {
  fetchRates()
})
</script>

<style scoped>
.exchange-rate-page {
  max-width: 900px;
}
</style>
