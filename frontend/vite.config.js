import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 与 cloudPhone 长超时一致，避免本地开发时代理先断开
        timeout: 180000,
        proxyTimeout: 180000,
      },
      '/artifacts': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
