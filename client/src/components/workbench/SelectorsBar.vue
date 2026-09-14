<script setup lang="ts">
import { unlabeledSelectorLabel } from '../../workbench/workbenchMode.ts'

defineProps<{
  unlabeledOn: boolean
  dismissUnlabeledHref: string
  toggleUnlabeledHref: string
  typeChip: { label: string, title: string, dismissHref: string } | null
}>()
</script>

<template>
  <div class="flex min-h-9 shrink-0 flex-wrap items-center gap-1.5 border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2 py-1.5 text-xs">
    <span class="ch-kicker mb-0 mr-1 shrink-0">Selectors</span>
    <span
      v-if="unlabeledOn"
      class="ch-chip ch-chip-active gap-0.5 pr-1"
    >
      {{ unlabeledSelectorLabel() }}
      <RouterLink
        class="inline-flex h-4 w-4 items-center justify-center rounded-[2px] text-xs leading-none text-[var(--ch-color-muted-foreground)] no-underline hover:bg-[var(--ch-color-background)] hover:text-[var(--ch-color-foreground)]"
        :to="dismissUnlabeledHref"
        title="Remove Unlabeled selector"
        aria-label="Remove Unlabeled selector"
      >×</RouterLink>
    </span>
    <span v-if="unlabeledOn && typeChip" class="ch-muted-text">∩</span>
    <span
      v-if="typeChip"
      class="ch-chip ch-chip-active gap-0.5 pr-1"
      :title="typeChip.title"
    >
      {{ typeChip.label }}
      <RouterLink
        class="inline-flex h-4 w-4 items-center justify-center rounded-[2px] text-xs leading-none text-[var(--ch-color-muted-foreground)] no-underline hover:bg-[var(--ch-color-background)] hover:text-[var(--ch-color-foreground)]"
        :to="typeChip.dismissHref"
        title="Remove type selector"
        :aria-label="`Remove ${typeChip.title || typeChip.label} selector`"
      >×</RouterLink>
    </span>
    <div class="ml-auto flex flex-wrap items-center gap-1.5">
      <RouterLink
        class="ch-chip ch-chip-idle"
        :to="toggleUnlabeledHref"
        title="Unlabeled comments, plus comments not in the manuscript that still need Verify or Drop"
      >
        {{ unlabeledSelectorLabel() }}
      </RouterLink>
    </div>
  </div>
</template>
