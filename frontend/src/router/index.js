import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '数据看板' } },
      { path: 'products', name: 'ProductList', component: () => import('@/views/ProductList.vue'), meta: { title: '商品列表' } },
      { path: 'products/:id', name: 'ProductDetail', component: () => import('@/views/ProductDetail.vue'), meta: { title: '商品详情' } },
      { path: 'import', name: 'BatchImport', component: () => import('@/views/BatchImport.vue'), meta: { title: '批量导入' } },
    ],
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
