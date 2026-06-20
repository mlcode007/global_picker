<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible theme="dark" width="220">
      <div class="logo">
        <span v-if="!collapsed">Global Picker</span>
        <span v-else>GP</span>
      </div>
      <a-menu
        theme="dark"
        mode="inline"
        :selected-keys="[selectedKey]"
        @click="handleMenuClick"
      >
        <a-menu-item key="Dashboard">
          <template #icon><DashboardOutlined /></template>
          数据看板
        </a-menu-item>
        <a-menu-item key="ProductList">
          <template #icon><UnorderedListOutlined /></template>
          商品列表
        </a-menu-item>
        <a-menu-item key="BatchImport">
          <template #icon><ImportOutlined /></template>
          批量导入
        </a-menu-item>
        <a-menu-item key="CloudPhone">
          <template #icon><PhoneOutlined /></template>
          云手机管理
        </a-menu-item>
        <a-menu-item key="Membership">
          <template #icon><CrownOutlined /></template>
          会员中心
        </a-menu-item>
        <a-menu-item v-if="isAdmin" key="DiscountCodes">
          <template #icon><TagOutlined /></template>
          折扣码管理
        </a-menu-item>
        <a-menu-item key="ExchangeRate">
          <template #icon><DollarOutlined /></template>
          汇率管理
        </a-menu-item>
        <a-menu-item key="Profile">
          <template #icon><UserOutlined /></template>
          个人主页
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="header">
        <span class="header-title">{{ route.meta.title || 'Global Picker' }}</span>
        <div class="header-right">
          <a-tag color="green">后端已连接</a-tag>
          <a-dropdown v-if="authStore.isLoggedIn">
            <a class="user-info" @click.prevent>
              <a-avatar :size="28" style="background-color: #667eea; margin-right: 8px;">
                {{ avatarText }}
              </a-avatar>
              <span class="user-name">{{ authStore.displayName }}</span>
              <DownOutlined style="font-size: 10px; margin-left: 4px;" />
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item disabled>
                  <span style="color: #999; font-size: 12px;">
                    {{ authStore.user?.company_name }}
                  </span>
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item @click="handleLogout">
                  <LogoutOutlined />
                  <span style="margin-left: 8px;">退出登录</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content class="content">
        <router-view />
      </a-layout-content>

      <a-layout-footer class="footer">
        Global Picker © 2026 — 跨平台选品比价系统
      </a-layout-footer>
    </a-layout>

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
  </a-layout>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DashboardOutlined,
  UnorderedListOutlined,
  ImportOutlined,
  PhoneOutlined,
  CrownOutlined,
  TagOutlined,
  DollarOutlined,
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const showDocPopup = ref(false)
const showWechatPopup = ref(false)
const showContactPopup = ref(false)

onMounted(() => {
  if (authStore.isLoggedIn) {
    authStore.startAutoRefresh()
  }
})

onUnmounted(() => {
  authStore.stopAutoRefresh()
})

const isAdmin = computed(() => authStore.user?.role === 'admin')

const avatarText = computed(() => {
  const name = authStore.displayName
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const selectedKey = computed(() => {
  const name = route.name
  if (name) return name
  return 'Dashboard'
})

function handleMenuClick({ key }) {
  console.log('Menu clicked:', key)
  if (key === 'CloudPhone') {
    router.push('/app/cloud-phone')
  } else if (key === 'Membership') {
    router.push('/app/membership')
  } else if (key === 'ExchangeRate') {
    router.push('/app/exchange-rate')
  } else if (key === 'Profile') {
    router.push('/app/profile')
  } else {
    router.push({ name: key })
  }
}

function handleLogout() {
  authStore.logout()
}

watch(route, () => {
  selectedKey.value = route.name || 'Dashboard'
})
</script>

<style scoped>
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #001529;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.user-name {
  font-size: 14px;
  color: #fff;
}

.content {
  margin: 24px;
  min-height: calc(100vh - 128px);
  background: #f0f2f5;
  border-radius: 8px;
  padding: 24px;
}

.footer {
  text-align: center;
  padding: 24px;
  color: #999;
  font-size: 14px;
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
</style>
