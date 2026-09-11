import { createRouter, createWebHistory } from 'vue-router'
import AppShell from './layout/AppShell.vue'
import HistoryPage from './pages/HistoryPage.vue'
import WorkbenchPage from './pages/WorkbenchPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', name: 'inbox', component: WorkbenchPage },
        { path: 'taxonomy/:id', name: 'issue', component: WorkbenchPage },
        { path: 'history', name: 'history', component: HistoryPage },
      ],
    },
  ],
})
