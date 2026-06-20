import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/Landing.vue'),
    meta: { title: 'Global Picker - 跨平台智能选品比价系统', guest: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', guest: true },
  },
  {
    path: '/app',
    component: () => import('@/components/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/app/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '数据看板' } },
      { path: 'products', name: 'ProductList', component: () => import('@/views/ProductList.vue'), meta: { title: '商品列表' } },
      { path: 'products/:id', name: 'ProductDetail', component: () => import('@/views/ProductDetail.vue'), meta: { title: '商品详情' } },
      { path: 'import', name: 'BatchImport', component: () => import('@/views/BatchImport.vue'), meta: { title: '批量导入' } },
      { path: 'cloud-phone', name: 'CloudPhone', component: () => import('@/views/CloudPhone.vue'), meta: { title: '云手机管理' } },
      { path: 'membership', name: 'Membership', component: () => import('@/views/Membership.vue'), meta: { title: '会员中心' } },
      { path: 'discount-codes', name: 'DiscountCodes', component: () => import('@/views/DiscountCodes.vue'), meta: { title: '折扣码管理', requiresAdmin: true } },
      { path: 'exchange-rate', name: 'ExchangeRate', component: () => import('@/views/ExchangeRate.vue'), meta: { title: '汇率管理' } },
      { path: 'profile', name: 'Profile', component: () => import('@/views/Profile.vue'), meta: { title: '个人主页' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function getCurrentRole() {
  try {
    const user = JSON.parse(localStorage.getItem('gp_user') || 'null')
    return user?.role || null
  } catch {
    return null
  }
}

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('gp_token')

  // 需要认证的页面
  if (to.meta.requiresAuth || to.matched.some(r => r.meta.requiresAuth)) {
    if (!token) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
  }

  // 仅管理员可访问的页面
  if (to.matched.some(r => r.meta.requiresAdmin)) {
    if (getCurrentRole() !== 'admin') {
      return next('/app/dashboard')
    }
  }

  // 已登录用户访问Landing页面时重定向到dashboard
  if (to.name === 'Landing' && token) {
    return next('/app/dashboard')
  }

  // guest页面(登录/注册)已登录时重定向
  if (to.meta.guest && token && to.name !== 'Landing') {
    return next('/app/dashboard')
  }

  next()
})

export default router
