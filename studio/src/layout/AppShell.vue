<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SettingsDialog from '../components/workbench/SettingsDialog.vue'
import ExportDialog from '../components/workbench/ExportDialog.vue'

const route = useRoute()
const historyActive = computed(() => route.name === 'history')
const workbenchActive = computed(() => !historyActive.value)
const workbenchTo = computed(() => (historyActive.value ? '/' : route.path))
const logoSrc = `${import.meta.env.BASE_URL}logo.svg`
</script>

<template>
  <div class="flex h-screen flex-col overflow-hidden bg-[var(--ch-color-background-soft)] text-xs text-[var(--ch-color-foreground)]">
    <header class="relative flex h-9 min-w-0 shrink-0 items-center gap-2 overflow-x-auto border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2 text-xs">
      <RouterLink
        class="inline-flex shrink-0 items-center gap-1.5 font-semibold tracking-[-0.02em] text-[var(--ch-color-foreground)] no-underline"
        to="/"
        title="ReviewDistill home"
      >
        <img :src="logoSrc" alt="" width="16" height="16" class="block">
        ReviewDistill
      </RouterLink>
      <RouterLink
        class="ch-chip"
        :class="workbenchActive ? 'ch-chip-active' : 'ch-chip-idle'"
        :to="workbenchTo"
        title="Coding workbench: taxonomy, issue details, and comments"
      >
        Workbench
      </RouterLink>
      <RouterLink
        class="ch-chip"
        :class="historyActive ? 'ch-chip-active' : 'ch-chip-idle'"
        to="/history"
        title="Chronological log of taxonomy and coding changes"
      >
        History
      </RouterLink>
      <SettingsDialog />
      <ExportDialog />
    </header>
    <main class="min-h-0 flex-1 overflow-hidden p-0">
      <RouterView />
    </main>
  </div>
</template>
