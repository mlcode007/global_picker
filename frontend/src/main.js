import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import router from './router'
import App from './App.vue'

createApp(App)
  .use(createPinia())
  .use(router)
  .use(Antd)
  .mount('#app')
