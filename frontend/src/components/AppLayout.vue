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
  </a-layout>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DashboardOutlined,
  UnorderedListOutlined,
  ImportOutlined,
  PhoneOutlined,
  UserOutlined,
  DownOutlined,
  LogoutOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

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
    router.push('/cloud-phone')
  } else if (key === 'Profile') {
    router.push('/profile')
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
</style>
