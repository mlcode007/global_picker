<template>
  <div class="landing">
    <!-- Header -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <div class="logo-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="url(#logoGradient)"/>
              <path d="M8 16L12 12L16 16L20 12L24 16" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M8 20L12 16L16 20L20 16L24 20" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
              <defs>
                <linearGradient id="logoGradient" x1="0" y2="32" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#6366f1"/>
                  <stop offset="1" stop-color="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span class="logo-text">Global Picker</span>
        </div>
        
        <nav class="nav-links">
          <a href="#features" class="nav-link">功能</a>
          <a href="#workflow" class="nav-link">流程</a>
          <a href="#pricing" class="nav-link">价格</a>
        </nav>
        
        <div class="header-actions">
          <button class="btn-text" @click="goToLogin">登录</button>
          <button class="btn-cta" @click="goToLogin">
            立即选品
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-container">
        <div class="hero-badge">
          <span class="badge-icon">✨</span>
          <span>跨境电商智能选品平台</span>
        </div>
        
        <h1 class="hero-title">
          <span class="title-line">选品，从未如此</span>
          <span class="title-highlight">简单高效</span>
        </h1>
        
        <p class="hero-desc">
          自动采集 TikTok 商品数据，智能匹配拼多多货源，<br/>
          实时计算利润空间，让选品决策更精准
        </p>
        
        <div class="hero-cta">
          <button class="btn-large btn-cta-primary" @click="goToLogin">
            立即选品
            <span class="btn-en">Get Started</span>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <p class="cta-note">无需信用卡 · 立即开始</p>
        </div>
        
        <!-- Stats -->
        <div class="hero-stats">
          <div class="stat-item">
            <div class="stat-value">{{ animatedStats.products }}+</div>
            <div class="stat-label">商品数据</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-value">{{ animatedStats.matches }}+</div>
            <div class="stat-label">成功匹配</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-value">{{ animatedStats.users }}+</div>
            <div class="stat-label">活跃用户</div>
          </div>
        </div>
      </div>
      
      <!-- Product Preview -->
      <div class="hero-preview">
        <div class="preview-window">
          <div class="window-header">
            <div class="window-controls">
              <span class="control control-close"></span>
              <span class="control control-minimize"></span>
              <span class="control control-maximize"></span>
            </div>
            <div class="window-title">Global Picker Dashboard</div>
          </div>
          <div class="window-content">
            <div class="preview-sidebar">
              <div class="sidebar-item sidebar-item-active">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7"/>
                  <rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/>
                  <rect x="3" y="14" width="7" height="7"/>
                </svg>
                <span>数据看板</span>
              </div>
              <div class="sidebar-item">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 7L12 3L4 7M20 7L12 11M20 7V17L12 21M12 11L4 7M12 11V21M4 7V17L12 21"/>
                </svg>
                <span>商品列表</span>
              </div>
              <div class="sidebar-item">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="M21 21L16.65 16.65"/>
                </svg>
                <span>智能匹配</span>
              </div>
              <div class="sidebar-item">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2V20M2 12H20"/>
                </svg>
                <span>批量导入</span>
              </div>
            </div>
            <div class="preview-main">
              <div class="preview-cards">
                <div class="preview-card">
                  <div class="card-label">商品总数</div>
                  <div class="card-value">12,847</div>
                  <div class="card-trend trend-up">↑ 23%</div>
                </div>
                <div class="preview-card">
                  <div class="card-label">匹配成功</div>
                  <div class="card-value">8,234</div>
                  <div class="card-trend trend-up">↑ 18%</div>
                </div>
                <div class="preview-card">
                  <div class="card-label">平均利润率</div>
                  <div class="card-value">32.5%</div>
                  <div class="card-trend trend-up">↑ 5%</div>
                </div>
              </div>
              <div class="preview-chart">
                <div class="chart-title">7日趋势</div>
                <div class="chart-bars">
                  <div class="chart-bar" style="--height: 40%"></div>
                  <div class="chart-bar" style="--height: 60%"></div>
                  <div class="chart-bar" style="--height: 45%"></div>
                  <div class="chart-bar" style="--height: 75%"></div>
                  <div class="chart-bar" style="--height: 55%"></div>
                  <div class="chart-bar" style="--height: 80%"></div>
                  <div class="chart-bar chart-bar-today" style="--height: 90%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section id="features" class="features">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">核心功能</h2>
          <p class="section-desc">为跨境卖家打造的完整选品工具链</p>
        </div>
        
        <div class="features-grid">
          <div class="feature-item" v-for="feature in features" :key="feature.title">
            <div class="feature-icon" :style="{ background: feature.color }">
              <component :is="feature.icon" />
            </div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Workflow -->
    <section id="workflow" class="workflow">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">四步完成选品</h2>
          <p class="section-desc">简单流程，高效决策</p>
        </div>
        
        <div class="workflow-steps">
          <div class="workflow-step" v-for="(step, index) in workflowSteps" :key="step.title">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <h3 class="step-title">{{ step.title }}</h3>
              <p class="step-desc">{{ step.desc }}</p>
            </div>
            <div class="step-arrow" v-if="index < workflowSteps.length - 1">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing -->
    <section id="pricing" class="pricing">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">简单透明的价格</h2>
          <p class="section-desc">按需付费，无隐藏费用</p>
        </div>
        
        <div class="pricing-cards">
          <div class="pricing-card">
            <div class="pricing-header">
              <h3 class="pricing-name">免费版</h3>
              <div class="pricing-price">
                <span class="price-amount">¥0</span>
                <span class="price-period">/月</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>每日采集 50 条商品</li>
              <li>基础比价功能</li>
              <li>手动匹配功能</li>
              <li>Excel 导出</li>
            </ul>
            <button class="btn-outline" @click="goToLogin">免费注册</button>
          </div>
          
          <div class="pricing-card pricing-card-popular">
            <div class="popular-badge">最受欢迎</div>
            <div class="pricing-header">
              <h3 class="pricing-name">基础版</h3>
              <div class="pricing-price">
                <span class="price-amount">¥99</span>
                <span class="price-period">/月</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>每日采集 500 条商品</li>
              <li>智能自动匹配</li>
              <li>拍照购自动化</li>
              <li>利润分析报告</li>
              <li>Excel 导出</li>
            </ul>
            <button class="btn-gradient" @click="goToLogin">立即订阅</button>
          </div>
          
          <div class="pricing-card">
            <div class="pricing-header">
              <h3 class="pricing-name">专业版</h3>
              <div class="pricing-price">
                <span class="price-amount">¥129</span>
                <span class="price-period">/月</span>
              </div>
            </div>
            <ul class="pricing-features">
              <li>每日采集不限</li>
              <li>全部基础版功能</li>
              <li>优先客服支持</li>
              <li>云手机订阅 ¥100/月/台</li>
              <li>最多 5 台云手机</li>
            </ul>
            <button class="btn-outline" @click="goToLogin">立即订阅</button>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="cta-container">
        <div class="cta-content">
          <h2 class="cta-title">准备好开始了吗？</h2>
          <p class="cta-desc">立即登录，开启智能选品之旅</p>
          <button class="btn-large btn-white" @click="goToLogin">
            立即选品
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-container">
        <div class="footer-brand">
          <div class="logo">
            <div class="logo-icon">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <rect width="32" height="32" rx="8" fill="url(#footerLogoGradient)"/>
                <path d="M8 16L12 12L16 16L20 12L24 16" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <defs>
                  <linearGradient id="footerLogoGradient" x1="0" y2="32" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#6366f1"/>
                    <stop offset="1" stop-color="#8b5cf6"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <span class="logo-text">Global Picker</span>
          </div>
          <p class="footer-tagline">让选品更简单高效</p>
        </div>

        <div class="footer-links">
          <div class="footer-column">
            <h4 class="footer-title">产品</h4>
            <a href="#features" class="footer-link">功能介绍</a>
            <a href="#pricing" class="footer-link">价格方案</a>
            <a href="#" class="footer-link">更新日志</a>
          </div>
          <div class="footer-column">
            <h4 class="footer-title">支持</h4>
            <a href="#" class="footer-link">帮助文档</a>
            <a href="#" class="footer-link">API 文档</a>
            <a href="#" class="footer-link">联系我们</a>
          </div>
          <div class="footer-column">
            <h4 class="footer-title">公司</h4>
            <a href="#" class="footer-link">关于我们</a>
            <a href="#" class="footer-link">隐私政策</a>
            <a href="#" class="footer-link">服务条款</a>
          </div>
        </div>

        <div class="footer-bottom">
          <p class="copyright">&copy; {{ currentYear }} Global Picker. All rights reserved.</p>
        </div>
      </div>
    </footer>

    <!-- Floating Side Bar -->
    <div class="side-bar">
      <div class="side-bar-item" @mouseenter="showDocPopup = true" @mouseleave="showDocPopup = false">
        <a href="https://notion.so" target="_blank" rel="noopener" class="side-bar-link">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </a>
        <div class="side-popup" v-show="showDocPopup">
          <div class="side-popup-arrow"></div>
          <div class="side-popup-content">
            <div class="qr-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <path d="M3 9h18M9 3v18"/>
              </svg>
              <p>Notion 文档页面</p>
              <p class="qr-hint">替换为实际文档链接</p>
            </div>
          </div>
        </div>
      </div>

      <div class="side-bar-item" @mouseenter="showWechatPopup = true" @mouseleave="showWechatPopup = false">
        <a href="javascript:void(0)" class="side-bar-link">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </a>
        <div class="side-popup" v-show="showWechatPopup">
          <div class="side-popup-arrow"></div>
          <div class="side-popup-content">
            <div class="qr-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <path d="M3 9h18M9 3v18"/>
              </svg>
              <p>Global Picker 服务号</p>
              <p class="qr-hint">替换为实际二维码图片</p>
            </div>
          </div>
        </div>
      </div>

      <div class="side-bar-item" @mouseenter="showContactPopup = true" @mouseleave="showContactPopup = false">
        <a href="javascript:void(0)" class="side-bar-link">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
        </a>
        <div class="side-popup" v-show="showContactPopup">
          <div class="side-popup-arrow"></div>
          <div class="side-popup-content">
            <div class="qr-placeholder">
              <img src="/wechat-qrcode.png" alt="企业微信二维码" class="qr-image"/>
              <p>企业微信二维码</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const currentYear = new Date().getFullYear()

const showDocPopup = ref(false)
const showWechatPopup = ref(false)
const showContactPopup = ref(false)

const animatedStats = ref({
  products: 0,
  matches: 0,
  users: 0
})

const targetStats = {
  products: 50000,
  matches: 30000,
  users: 1000
}

// Icon Components
const IconGlobe = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M2 12h20"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>`
}

const IconSearch = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="M21 21l-4.35-4.35"/>
    </svg>`
}

const IconChart = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M18 20V10"/>
      <path d="M12 20V4"/>
      <path d="M6 20v-6"/>
    </svg>`
}

const IconCamera = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
      <circle cx="12" cy="13" r="4"/>
    </svg>`
}

const IconDownload = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>`
}

const IconShield = {
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>`
}

const features = [
  {
    icon: IconGlobe,
    title: 'TikTok 商品采集',
    desc: '自动化采集全球 TikTok 商品数据，支持菲律宾、越南等多区域',
    color: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
  },
  {
    icon: IconSearch,
    title: '智能货源匹配',
    desc: '基于图像识别算法，自动匹配拼多多同款商品与实时价格',
    color: 'linear-gradient(135deg, #ec4899 0%, #f43f5e 100%)'
  },
  {
    icon: IconChart,
    title: '利润分析计算',
    desc: '自动汇率换算，实时计算利润率，筛选高利润商品',
    color: 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
  },
  {
    icon: IconCamera,
    title: '拍照购自动化',
    desc: 'ADB 控制设备自动拍照搜索，批量获取候选商品',
    color: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
  },
  {
    icon: IconDownload,
    title: '报表导出',
    desc: '一键导出 Excel 报表，自定义字段，满足不同分析需求',
    color: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
  },
  {
    icon: IconShield,
    title: '数据安全',
    desc: '企业级加密存储，完善的权限管理体系，保障数据安全',
    color: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
  }
]

const workflowSteps = [
  { title: '添加商品', desc: '输入 TikTok 链接或批量导入商品' },
  { title: '自动采集', desc: '系统自动抓取商品详细信息' },
  { title: '智能匹配', desc: 'AI 自动匹配拼多多同款货源' },
  { title: '利润决策', desc: '基于数据分析做出采购决策' }
]

function goToLogin() {
  router.push('/login')
}

function animateValue(start, end, duration, callback) {
  const startTime = Date.now()
  const animate = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    const current = Math.floor(start + (end - start) * easeOut)
    callback(current)
    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }
  animate()
}

onMounted(() => {
  setTimeout(() => {
    Object.keys(targetStats).forEach(key => {
      animateValue(0, targetStats[key], 2000, (val) => {
        animatedStats.value[key] = val
      })
    })
  }, 800)
})
</script>

<style scoped>
/* ===== Base Styles ===== */
.landing {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  color: #1a1a1a;
  background: #fff;
  overflow-x: hidden;
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ===== Header ===== */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  display: flex;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  font-size: 14px;
  color: #666;
  text-decoration: none;
  transition: color 0.2s;
}

.nav-link:hover {
  color: #1a1a1a;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* ===== Buttons ===== */
.btn-text {
  padding: 8px 16px;
  font-size: 14px;
  color: #666;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.btn-text:hover {
  color: #1a1a1a;
}

.btn-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.btn-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
}

.btn-outline {
  width: 100%;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  background: transparent;
  border: 2px solid #e5e5e5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  border-color: #1a1a1a;
}

.btn-gradient {
  width: 100%;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #fff;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-gradient:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
}

.btn-large {
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cta-primary {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 18px 40px;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 24px rgba(16, 185, 129, 0.35);
  letter-spacing: -0.5px;
}

.btn-cta-primary:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(16, 185, 129, 0.45);
}

.btn-en {
  font-size: 13px;
  font-weight: 500;
  opacity: 0.85;
  letter-spacing: 0.5px;
}

.btn-white {
  color: #1a1a1a;
  background: #fff;
}

.btn-white:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

/* ===== Hero Section ===== */
.hero {
  padding: 140px 0 80px;
  background: linear-gradient(180deg, #fafafa 0%, #fff 100%);
}

.hero-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  color: #6366f1;
  margin-bottom: 32px;
}

.badge-icon {
  font-size: 14px;
}

.hero-title {
  font-size: 72px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -2px;
  margin-bottom: 24px;
}

.title-line {
  display: block;
  color: #1a1a1a;
}

.title-highlight {
  display: block;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 18px;
  line-height: 1.6;
  color: #666;
  margin-bottom: 40px;
}

.hero-cta {
  margin-bottom: 48px;
}

.cta-note {
  margin-top: 12px;
  font-size: 13px;
  color: #999;
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 48px;
  margin-top: 60px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: 800;
  color: #1a1a1a;
  letter-spacing: -1px;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 4px;
}

.stat-divider {
  width: 1px;
  height: 48px;
  background: #e5e5e5;
}

/* ===== Product Preview ===== */
.hero-preview {
  max-width: 1200px;
  margin: 80px auto 0;
  padding: 0 24px;
}

.preview-window {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.window-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.window-controls {
  display: flex;
  gap: 8px;
}

.control {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.control-close { background: #ff5f57; }
.control-minimize { background: #febc2e; }
.control-maximize { background: #28c840; }

.window-title {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.window-content {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 0;
  min-height: 400px;
}

.preview-sidebar {
  background: #fafafa;
  padding: 16px;
  border-right: 1px solid rgba(0, 0, 0, 0.05);
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  color: #666;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-item:hover {
  background: #f0f0f0;
}

.sidebar-item-active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  color: #6366f1;
}

.sidebar-item span {
  font-size: 14px;
  font-weight: 500;
}

.preview-main {
  padding: 24px;
}

.preview-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.preview-card {
  padding: 20px;
  background: #fafafa;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.card-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
}

.card-trend {
  font-size: 12px;
  font-weight: 600;
  margin-top: 8px;
}

.trend-up { color: #10b981; }

.preview-chart {
  padding: 20px;
  background: #fafafa;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.chart-title {
  font-size: 13px;
  color: #999;
  margin-bottom: 16px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 120px;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(180deg, #e5e5e5 0%, #d4d4d4 100%);
  border-radius: 4px 4px 0 0;
  height: var(--height);
  transition: background 0.3s;
}

.chart-bar-today {
  background: linear-gradient(180deg, #6366f1 0%, #8b5cf6 100%);
}

/* ===== Features Section ===== */
.features {
  padding: 120px 0;
  background: #fff;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-title {
  font-size: 48px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -1px;
  margin-bottom: 16px;
}

.section-desc {
  font-size: 18px;
  color: #666;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}

.feature-item {
  padding: 32px;
  background: #fafafa;
  border-radius: 16px;
  transition: all 0.3s;
}

.feature-item:hover {
  background: #fff;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
  transform: translateY(-4px);
}

.feature-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  margin-bottom: 20px;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.feature-desc {
  font-size: 14px;
  line-height: 1.6;
  color: #666;
}

/* ===== Workflow Section ===== */
.workflow {
  padding: 120px 0;
  background: #fafafa;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 16px;
}

.step-number {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  border-radius: 12px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 13px;
  color: #666;
}

.step-arrow {
  color: #ccc;
  flex-shrink: 0;
}

/* ===== Pricing Section ===== */
.pricing {
  padding: 120px 0;
  background: #fff;
}

.pricing-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.pricing-card {
  padding: 32px;
  background: #fafafa;
  border-radius: 16px;
  border: 2px solid transparent;
  transition: all 0.3s;
}

.pricing-card:hover {
  background: #fff;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

.pricing-card-popular {
  border-color: #6366f1;
  position: relative;
}

.popular-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 16px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  border-radius: 100px;
}

.pricing-header {
  text-align: center;
  margin-bottom: 24px;
}

.pricing-name {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.pricing-price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.price-amount {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a1a;
}

.price-period {
  font-size: 14px;
  color: #999;
}

.pricing-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
}

.pricing-features li {
  padding: 12px 0;
  font-size: 14px;
  color: #666;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.pricing-features li:last-child {
  border-bottom: none;
}

/* ===== CTA Section ===== */
.cta-section {
  padding: 120px 0;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

.cta-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.cta-content {
  text-align: center;
}

.cta-title {
  font-size: 48px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -1px;
  margin-bottom: 16px;
}

.cta-desc {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 32px;
}

/* ===== Footer ===== */
.footer {
  padding: 80px 0 40px;
  background: #1a1a1a;
  color: #fff;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.footer-brand {
  margin-bottom: 48px;
}

.footer-tagline {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.footer-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 48px;
  margin-bottom: 48px;
}

.footer-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
}

.footer-link {
  display: block;
  font-size: 14px;
  color: #666;
  text-decoration: none;
  padding: 8px 0;
  transition: color 0.2s;
}

.footer-link:hover {
  color: #fff;
}

.footer-bottom {
  padding-top: 32px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.copyright {
  font-size: 13px;
  color: #666;
  text-align: center;
  margin: 0;
}

/* ===== Floating Side Bar ===== */
.side-bar {
  position: fixed;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 999;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.side-bar-item {
  position: relative;
}

.side-bar-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: #fff;
  border-radius: 12px;
  color: #1a1a1a;
  text-decoration: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  cursor: pointer;
}

.side-bar-link:hover {
  transform: translateX(-4px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  color: #6366f1;
}

.side-bar-link svg {
  opacity: 0.7;
  transition: opacity 0.2s;
}

.side-bar-link:hover svg {
  opacity: 1;
}

/* Side Popup */
.side-popup {
  position: absolute;
  right: calc(100% + 12px);
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
}

.side-popup-arrow {
  width: 12px;
  height: 12px;
  background: #fff;
  transform: rotate(45deg);
  position: absolute;
  right: -6px;
  top: 50%;
  margin-top: -6px;
  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
}

.side-popup-content {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  min-width: 200px;
}

.qr-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.qr-image {
  width: 160px;
  height: 160px;
  border-radius: 8px;
  object-fit: contain;
}

.qr-placeholder p {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  margin: 0;
}

.qr-hint {
  font-size: 12px;
  color: #999;
  font-weight: 400;
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .hero-title {
    font-size: 56px;
  }
  
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .workflow-steps {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .pricing-cards {
    grid-template-columns: 1fr;
    max-width: 400px;
  }
  
  .window-content {
    grid-template-columns: 1fr;
  }
  
  .preview-sidebar {
    display: none;
  }
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }
  
  .hero-title {
    font-size: 42px;
  }
  
  .title-line, .title-highlight {
    display: inline;
  }
  
  .hero-stats {
    flex-direction: column;
    gap: 24px;
  }
  
  .stat-divider {
    display: none;
  }
  
  .section-title {
    font-size: 36px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .workflow-steps {
    grid-template-columns: 1fr;
  }
  
  .step-arrow {
    display: none;
  }
  
  .footer-links {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  
  .cta-title {
    font-size: 36px;
  }
  
  .side-bar {
    right: 12px;
  }
  
  .side-bar-link {
    width: 40px;
    height: 40px;
  }
}
</style>