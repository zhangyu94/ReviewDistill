<script setup lang="ts">
import type { WorkbenchSnackbarKind } from '../../workbench/assignmentNotice.ts'

withDefaults(defineProps<{
  text: string
  kind?: WorkbenchSnackbarKind
}>(), {
  kind: 'info',
})
const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <div
    v-if="text"
    class="pointer-events-none fixed bottom-12 right-2 z-20 flex justify-end"
  >
    <div class="pointer-events-auto flex max-w-md items-start gap-2 rounded border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-2 shadow">
      <span
        v-if="kind === 'error'"
        class="i-fa6-solid:circle-exclamation mt-0.5 h-4 w-4 shrink-0 text-[var(--ch-color-destructive)]"
        aria-hidden="true"
      />
      <span
        v-else
        class="i-fa6-solid:circle-info mt-0.5 h-4 w-4 shrink-0 text-[var(--ch-color-body)]"
        aria-hidden="true"
      />
      <p
        class="text-xs break-words"
        :class="kind === 'error' ? 'ch-error-text' : 'text-[var(--ch-color-foreground)]'"
      >
        {{ text }}
      </p>
      <button
        class="ml-auto shrink-0"
        type="button"
        title="Close"
        @click="emit('close')"
      >
        <span class="i-fa6-solid:xmark h-3 w-3" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
