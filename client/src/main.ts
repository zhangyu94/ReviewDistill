import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router.ts'
import '@unocss/reset/tailwind.css'
import 'uno.css'

createApp(App).use(createPinia()).use(router).mount('#root')
