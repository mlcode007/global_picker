<template>
  <div class="discount-codes">
    <a-page-header title="折扣码管理" ghost>
      <template #extra>
        <a-space>
          <a-select
            v-model:value="filterTier"
            style="width: 140px"
            allow-clear
            placeholder="全部等级"
            @change="fetchCodes"
          >
            <a-select-option value="basic">基础版</a-select-option>
            <a-select-option value="pro">专业版</a-select-option>
          </a-select>
          <a-button type="primary" @click="openCreate">新建折扣码</a-button>
          <a-button @click="fetchCodes" :loading="loading">刷新</a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-card style="margin-top: 16px">
      <a-table
        :data-source="codes"
        :columns="columns"
        :loading="loading"
        row-key="id"
        size="middle"
        :scroll="{ x: 900 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tier'">
            <a-tag :color="record.tier === 'pro' ? 'gold' : 'blue'">
              {{ tierNameMap[record.tier] }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'price'">
            ¥{{ record.price }}
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'success' : 'default'">
              {{ record.is_active ? '启用' : '停用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'usage'">
            <a-tag :color="record.status === 'used' ? 'error' : 'processing'">
              {{ record.status === 'used' ? '已使用' : '未使用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'expires_at'">
            {{ record.expires_at ? formatDate(record.expires_at) : '长期有效' }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a @click="openEdit(record)">编辑</a>
              <a @click="toggleActive(record)">{{ record.is_active ? '停用' : '启用' }}</a>
              <a-popconfirm
                v-if="record.status === 'used'"
                title="重置后该折扣码可再次使用，确定？"
                @confirm="resetCode(record)"
              >
                <a>重置</a>
              </a-popconfirm>
              <a-popconfirm title="确定删除该折扣码？" @confirm="removeCode(record)">
                <a style="color: #cf1322">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建 / 编辑弹窗 -->
    <a-modal
      v-model:open="showModal"
      :title="editing ? '编辑折扣码' : '新建折扣码'"
      :confirm-loading="saving"
      @ok="submitForm"
      @cancel="showModal = false"
    >
      <a-form layout="vertical">
        <a-form-item label="折扣码">
          <a-input
            v-model:value="form.code"
            :disabled="editing"
            placeholder="留空则自动生成"
          />
          <div v-if="!editing" style="margin-top: 4px; color: #999; font-size: 12px">
            可手动填写，留空将自动生成随机折扣码
          </div>
        </a-form-item>
        <a-form-item label="适用等级" required>
          <a-select v-model:value="form.tier" :disabled="editing">
            <a-select-option value="basic">基础版（原价 ¥{{ originalPrice('basic') }}）</a-select-option>
            <a-select-option value="pro">专业版（原价 ¥{{ originalPrice('pro') }}）</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="折扣价（元/月）" required>
          <a-input-number v-model:value="form.price" :min="0" :precision="2" style="width: 100%" />
          <div style="margin-top: 4px; color: #999; font-size: 12px">
            折扣码为一次性，被成功使用后将自动置为「已使用」且不可再次使用
          </div>
        </a-form-item>
        <a-form-item label="有效期">
          <a-date-picker
            v-model:value="form.expires_at"
            show-time
            style="width: 100%"
            placeholder="留空表示长期有效"
          />
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="form.remark" placeholder="可选" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch v-model:checked="form.is_active" checked-children="启用" un-checked-children="停用" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { discountApi } from '@/api/discount'
import { membershipApi } from '@/api/membership'

const tierNameMap = { basic: '基础版', pro: '专业版' }

const columns = [
  { title: '折扣码', dataIndex: 'code', key: 'code', width: 140 },
  { title: '等级', key: 'tier', width: 90 },
  { title: '折扣价', key: 'price', width: 100 },
  { title: '启用', key: 'is_active', width: 80 },
  { title: '使用状态', key: 'usage', width: 100 },
  { title: '有效期', key: 'expires_at', width: 170 },
  { title: '备注', dataIndex: 'remark', key: 'remark', width: 140 },
  { title: '操作', key: 'action', width: 180, fixed: 'right' },
]

const codes = ref([])
const loading = ref(false)
const filterTier = ref(undefined)

const showModal = ref(false)
const editing = ref(false)
const saving = ref(false)
const editingId = ref(null)
const planPrices = ref({ basic: 99, pro: 129 })

const form = ref({
  code: '',
  tier: 'basic',
  price: null,
  expires_at: null,
  remark: '',
  is_active: true,
})

function originalPrice(tier) {
  return planPrices.value[tier] ?? '-'
}

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchCodes() {
  loading.value = true
  try {
    const data = await discountApi.list(filterTier.value)
    codes.value = data.items || []
  } catch (e) {
    console.error('获取折扣码失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchPlanPrices() {
  try {
    const data = await membershipApi.getPlans()
    const map = {}
    ;(data.plans || []).forEach((p) => { map[p.tier] = p.price })
    planPrices.value = { basic: map.basic ?? 99, pro: map.pro ?? 129 }
  } catch (e) {
    console.error('获取套餐价格失败:', e)
  }
}

function openCreate() {
  editing.value = false
  editingId.value = null
  form.value = {
    code: '',
    tier: 'basic',
    price: null,
    expires_at: null,
    remark: '',
    is_active: true,
  }
  showModal.value = true
}

function openEdit(record) {
  editing.value = true
  editingId.value = record.id
  form.value = {
    code: record.code,
    tier: record.tier,
    price: record.price,
    expires_at: record.expires_at ? dayjs(record.expires_at) : null,
    remark: record.remark || '',
    is_active: !!record.is_active,
  }
  showModal.value = true
}

async function submitForm() {
  if (form.value.price == null || form.value.price < 0) {
    message.warning('请输入有效的折扣价')
    return
  }
  saving.value = true
  try {
    const payload = {
      price: form.value.price,
      expires_at: form.value.expires_at ? form.value.expires_at.toISOString() : null,
      remark: form.value.remark || null,
      is_active: form.value.is_active,
    }
    if (editing.value) {
      await discountApi.update(editingId.value, payload)
      message.success('已更新折扣码')
    } else {
      await discountApi.create({
        ...payload,
        code: form.value.code.trim() || null,
        tier: form.value.tier,
      })
      message.success('已创建折扣码')
    }
    showModal.value = false
    fetchCodes()
  } catch (e) {
    const detail = e.response?.data?.detail
    message.error(detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(record) {
  try {
    await discountApi.update(record.id, { is_active: !record.is_active })
    message.success(record.is_active ? '已停用' : '已启用')
    fetchCodes()
  } catch (e) {
    const detail = e.response?.data?.detail
    message.error(detail || '操作失败')
  }
}

async function resetCode(record) {
  try {
    await discountApi.update(record.id, { status: 'unused' })
    message.success('已重置为未使用')
    fetchCodes()
  } catch (e) {
    const detail = e.response?.data?.detail
    message.error(detail || '重置失败')
  }
}

async function removeCode(record) {
  try {
    await discountApi.remove(record.id)
    message.success('已删除')
    fetchCodes()
  } catch (e) {
    const detail = e.response?.data?.detail
    message.error(detail || '删除失败')
  }
}

onMounted(() => {
  fetchCodes()
  fetchPlanPrices()
})
</script>

<style scoped>
.discount-codes {
  width: 100%;
}
</style>
