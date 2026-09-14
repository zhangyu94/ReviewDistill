<script setup lang="ts">
import type { CommentProgress } from '../../api/client.ts'
import { EMPTY_PROGRESS, progressHeadlineLabel, progressParts, progressPartTitle } from '../../workbench/commentProgress.ts'

defineProps<{
  progress: CommentProgress | null
}>()
</script>

<template>
  <div
    class="flex min-h-9 h-auto shrink-0 flex-wrap items-center gap-x-3 gap-y-0.5 border-t border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2 text-xs"
  >
    <span class="ch-kicker mb-0">Progress</span>
    <span
      class="tabular-nums"
      :title="progressPartTitle('working_set')"
    >{{ (progress ?? EMPTY_PROGRESS).working_set }} {{ progressHeadlineLabel() }}</span>
    <span class="ch-muted-text tabular-nums">
      <template v-for="(row, i) in progressParts(progress ?? EMPTY_PROGRESS)" :key="row.key">
        <span v-if="i"> · </span>
        <span :title="progressPartTitle(row.key)">{{ row.key }} {{ row.n }}</span>
      </template>
    </span>
  </div>
</template>
