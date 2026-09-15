<script setup lang="ts">
defineProps<{
  unlabeledOn: boolean
  dismissUnlabeledHref: string
  toggleUnlabeledHref: string
  labelChip: { label: string, title: string, dismissHref: string } | null
}>()
</script>

<template>
  <div class="flex min-h-9 shrink-0 flex-wrap items-center gap-1.5 border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background-muted)] px-2 py-1.5 text-xs">
    <span class="ch-kicker mb-0 mr-1 shrink-0">Selectors</span>
    <span
      v-if="unlabeledOn"
      class="ch-chip ch-chip-active gap-0.5 pr-1"
    >
      Unlabeled
      <RouterLink
        class="inline-flex h-4 w-4 items-center justify-center rounded-[2px] text-xs leading-none text-[var(--ch-color-muted-foreground)] no-underline hover:bg-[var(--ch-color-background)] hover:text-[var(--ch-color-foreground)]"
        :to="dismissUnlabeledHref"
        title="Remove Unlabeled selector"
        aria-label="Remove Unlabeled selector"
      >×</RouterLink>
    </span>
    <span v-if="unlabeledOn && labelChip" class="ch-muted-text">∩</span>
    <span
      v-if="labelChip"
      class="ch-chip ch-chip-active gap-0.5 pr-1"
      :title="labelChip.title"
    >
      {{ labelChip.label }}
      <RouterLink
        class="inline-flex h-4 w-4 items-center justify-center rounded-[2px] text-xs leading-none text-[var(--ch-color-muted-foreground)] no-underline hover:bg-[var(--ch-color-background)] hover:text-[var(--ch-color-foreground)]"
        :to="labelChip.dismissHref"
        title="Remove label selector"
        :aria-label="`Remove ${labelChip.title || labelChip.label} selector`"
      >×</RouterLink>
    </span>
    <div class="ml-auto flex flex-wrap items-center gap-1.5">
      <RouterLink
        class="ch-chip ch-chip-idle"
        :to="toggleUnlabeledHref"
        title="Unlabeled comments, plus comments not in the manuscript that still need Verify or Delete"
      >
        Unlabeled
      </RouterLink>
    </div>
  </div>
</template>
