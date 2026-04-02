import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { productApi, profitApi } from '@/api/products'
import { message } from 'ant-design-vue'

export const useProductStore = defineStore('product', () => {
  const list = ref([])
  const total = ref(0)
  const loading = ref(false)
  const exchangeRates = ref([])

  const filters = reactive({
    page: 1,
    page_size: 20,
    status: undefined,
    region: undefined,
    keyword: undefined,
    price_cny_min: undefined,
    price_cny_max: undefined,
    profit_min: undefined,
    profit_max: undefined,
    order_by: 'created_at',
    order_dir: 'desc',
  })

  async function fetchList() {
    loading.value = true
    try {
      const res = await productApi.list(filters)
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

  async function fetchExchangeRates() {
    if (exchangeRates.value.length) return
    exchangeRates.value = await profitApi.exchangeRates()
  }

  return { list, total, loading, filters, fetchList, updateStatus, deleteProduct, fetchExchangeRates, exchangeRates }
})
