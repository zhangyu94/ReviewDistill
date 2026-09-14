<script setup lang="ts">
import type { CommentProgress } from '../../api/client.ts'
import { EMPTY_PROGRESS, progressParts } from '../../workbench/commentProgress.ts'

defineProps<{
  progress: CommentProgress | null
}>()

const partTitle = {
  working_set: 'The number of comments to distill. They are not dropped, and they are still in the manuscript or already verified.',
  unlabeled: 'The number of comments to distill that have no issue type. The Unlabeled chip is the inbox queue, not this count.',
  verified: 'The number of comments that are quality-assured. Does not confirm the issue type.',
  dropped: 'The number of comments not to distill (too local, or a bad extract). History is kept.',
} as const
</script>

<template>
  <div
    class="flex min-h-9 h-auto shrink-0 flex-wrap items-center gap-x-3 gap-y-0.5 border-t border-[var(--ch-color-border)] bg-[var(--ch-color-background-muted)] px-2 text-xs"
  >
    <span class="ch-kicker mb-0">Progress</span>
    <span
      class="tabular-nums"
      :title="partTitle.working_set"
    >{{ (progress ?? EMPTY_PROGRESS).working_set }} to distill</span>
    <span class="ch-muted-text tabular-nums">
      <template v-for="(row, i) in progressParts(progress ?? EMPTY_PROGRESS)" :key="row.key">
        <span v-if="i"> · </span>
        <span :title="partTitle[row.key]">{{ row.key }} {{ row.n }}</span>
      </template>
    </span>
  </div>
</template>
