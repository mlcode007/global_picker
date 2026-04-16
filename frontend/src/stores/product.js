import { defineStore } from 'pinia'
import { ref, reactive, watch } from 'vue'
import { productApi, profitApi } from '@/api/products'
import { message } from 'ant-design-vue'

const PAGE_SIZE_STORAGE_KEY = 'gp_product_list_page_size'
const DEFAULT_PAGE_SIZE = 20
const ALLOWED_PAGE_SIZES = new Set([10, 20, 50, 100, 200, 500, 1000])

function readStoredPageSize() {
  if (typeof localStorage === 'undefined') return DEFAULT_PAGE_SIZE
  try {
    const raw = localStorage.getItem(PAGE_SIZE_STORAGE_KEY)
    if (raw == null || raw === '') return DEFAULT_PAGE_SIZE
    const n = parseInt(raw, 10)
    if (Number.isFinite(n) && ALLOWED_PAGE_SIZES.has(n)) return n
  } catch {
    /* ignore */
  }
  return DEFAULT_PAGE_SIZE
}

export const useProductStore = defineStore('product', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)
  const exchangeRates = ref([])

  const filters = reactive({
    page: 1,
    page_size: readStoredPageSize(),
    status: undefined,
    region: undefined,
    keyword: undefined,
    price_cny_min: undefined,
    price_cny_max: undefined,
    profit_min: undefined,
    profit_max: undefined,
    profit_rate_min: undefined,
    profit_rate_max: undefined,
    order_by: 'created_at',
    order_dir: 'desc',
  })

  watch(
    () => filters.page_size,
    (n) => {
      if (!ALLOWED_PAGE_SIZES.has(n)) return
      try {
        localStorage.setItem(PAGE_SIZE_STORAGE_KEY, String(n))
      } catch {
        /* ignore */
      }
    }
  )

  async function fetchList() {
    loading.value = true
    try {
      const params = { ...filters }
      if (params.profit_rate_min != null) {
        params.profit_rate_min = params.profit_rate_min / 100
      }
      if (params.profit_rate_max != null) {
        params.profit_rate_max = params.profit_rate_max / 100
      }
      const res = await productApi.list(params)
      list.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function updateStatus(id, status) {
    await productApi.update(id, { status })
    const item = list.value.find(p => p.id === id)
    if (item) item.status = status
    message.success('状态已更新')
  }

  async function deleteProduct(id) {
    await productApi.remove(id)
    await fetchList()
    message.success('已删除')
  }

  async function batchDeleteProducts(ids) {
    const res = await productApi.batchRemove(ids)
    await fetchList()
    message.success(`成功删除 ${res.deleted_count} 个商品`)
  }

  async function fetchExchangeRates() {
    if (exchangeRates.value.length) return
    exchangeRates.value = await profitApi.exchangeRates()
  }

  return { list, total, loading, filters, fetchList, updateStatus, deleteProduct, batchDeleteProducts, fetchExchangeRates, exchangeRates }
})
