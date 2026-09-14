<script setup lang="ts">
import ExportDialog from '../components/workbench/ExportDialog.vue'
import HistoryDialog from '../components/workbench/HistoryDialog.vue'
import SettingsDialog from '../components/workbench/SettingsDialog.vue'

const logoSrc = `${import.meta.env.BASE_URL}logo.svg`

const headerLinks = [
  {
    id: 'github',
    label: 'GitHub',
    href: 'https://github.com/zhangyu94/ReviewDistill',
    title: 'Open the GitHub repository',
    icon: 'i-fa6-brands:github',
  },
  {
    id: 'docs',
    label: 'Docs',
    href: 'https://zhangyu94.github.io/ReviewDistill/',
    title: 'Open the documentation',
    icon: 'i-fa6-solid:book',
  },
] as const
</script>

<template>
  <div class="flex h-screen flex-col overflow-hidden bg-[var(--ch-color-background-soft)] text-xs text-[var(--ch-color-foreground)]">
    <header class="relative flex h-9 min-w-0 shrink-0 items-center gap-2 overflow-x-auto border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2 text-xs">
      <div class="inline-flex shrink-0 items-center gap-1.5 font-semibold tracking-[-0.02em] text-[var(--ch-color-foreground)]">
        <img :src="logoSrc" alt="" width="16" height="16" class="block">
        ReviewDistill
      </div>
      <div class="ml-auto flex shrink-0 items-center gap-3">
        <div class="flex shrink-0 items-center gap-1.5">
          <HistoryDialog />
          <SettingsDialog />
          <ExportDialog />
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <a
            v-for="link in headerLinks"
            :key="link.id"
            class="inline-flex h-6 shrink-0 items-center gap-1 text-xs font-medium no-underline leading-none text-[var(--ch-color-body)] hover:text-[var(--ch-color-foreground)] hover:no-underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--ch-color-ring)]"
            :href="link.href"
            :title="link.title"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span :class="link.icon" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {{ link.label }}
          </a>
        </div>
      </div>
    </header>
    <main class="min-h-0 flex-1 overflow-hidden p-0">
      <RouterView />
    </main>
  </div>
</template>
