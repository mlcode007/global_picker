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

// SEO: Dynamic meta tag management
function updateMetaTags(route) {
  const baseTitle = 'Global Picker - 跨平台智能选品比价系统'
  const title = route.meta.title
    ? `${route.meta.title} | ${baseTitle}`
    : baseTitle

  // Update page title
  document.title = title

  // Update meta description based on route
  const descriptions = {
    'Landing': 'Global Picker 是一款跨平台智能选品比价系统，支持TikTok商品采集、拼多多比价、利润分析、拍照购自动化、数据看板与报表导出。',
    'Login': '登录 Global Picker，开启智能选品之旅。',
    'Register': '注册 Global Picker，免费体验跨平台智能选品比价系统。',
    'Dashboard': '数据看板 - 实时掌握选品进度、匹配状态和利润趋势。',
    'ProductList': '商品列表 - 管理您的选品商品，查看匹配状态和利润分析。',
    'BatchImport': '批量导入 - 快速导入TikTok商品数据，高效获取选品素材。',
    'CloudPhone': '云手机管理 - 管理您的云手机设备，支持拍照购自动化。',
    'Membership': '会员中心 - 查看会员权益、套餐信息和订阅管理。',
    'Profile': '个人主页 - 管理您的账户信息和偏好设置。',
  }

  const description = descriptions[route.name] || 'Global Picker - 跨平台智能选品比价系统'

  // Update or create meta description
  let metaDescription = document.querySelector('meta[name="description"]')
  if (!metaDescription) {
    metaDescription = document.createElement('meta')
    metaDescription.name = 'description'
    document.head.appendChild(metaDescription)
  }
  metaDescription.content = description

  // Update or create meta keywords
  let metaKeywords = document.querySelector('meta[name="keywords"]')
  if (!metaKeywords) {
    metaKeywords = document.createElement('meta')
    metaKeywords.name = 'keywords'
    document.head.appendChild(metaKeywords)
  }
  metaKeywords.content = 'Global Picker, 选品工具, 跨平台比价, TikTok选品, 拼多多比价, 电商选品, 利润分析, 拍照购, 智能选品, 跨境电商'

  // Update canonical URL
  let canonical = document.querySelector('link[rel="canonical"]')
  if (!canonical) {
    canonical = document.createElement('link')
    canonical.rel = 'canonical'
    document.head.appendChild(canonical)
  }
  canonical.href = `https://www.globalpicker.com${route.fullPath}`

  // Update Open Graph tags
  const ogTags = {
    'og:title': title,
    'og:description': description,
    'og:url': `https://www.globalpicker.com${route.fullPath}`,
  }

  Object.entries(ogTags).forEach(([property, content]) => {
    let meta = document.querySelector(`meta[property="${property}"]`)
    if (!meta) {
      meta = document.createElement('meta')
      meta.setAttribute('property', property)
      document.head.appendChild(meta)
    }
    meta.content = content
  })
}

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

  // Update SEO meta tags
  updateMetaTags(to)

  next()
})

export default router
