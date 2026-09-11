<script setup lang="ts">
import type { SelectorId } from '../../workbench/workbenchMode.ts'

defineProps<{
  selector: SelectorId
  uncodedCount: number
  disappearedCount: number
  typeHref: string
  typeLabel: string
  typeTitle: string
  uncodedHref: string
  disappearedHref: string
  coding: boolean
  canRequestSuggestions: boolean
  codeAllTitle: string
  showCodeAll: boolean
}>()

const emit = defineEmits<{
  codeAll: []
  dismissType: []
}>()

function chipClass(active: boolean): string {
  return active ? 'ch-chip ch-chip-active' : 'ch-chip ch-chip-idle'
}
</script>

<template>
  <div class="flex min-h-9 shrink-0 flex-wrap items-center gap-1.5 border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2 py-1.5 text-xs">
    <span class="ch-kicker mb-0 mr-1 shrink-0">Selectors</span>
    <span
      v-if="typeHref"
      :class="chipClass(selector === 'type')"
      class="gap-0.5 pr-1"
    >
      <RouterLink
        class="text-inherit no-underline"
        :to="typeHref"
        :title="typeTitle"
      >
        {{ typeLabel }}
      </RouterLink>
      <button
        class="inline-flex h-4 w-4 items-center justify-center rounded-[2px] text-xs leading-none text-[var(--ch-color-muted-foreground)] hover:bg-[var(--ch-color-background)] hover:text-[var(--ch-color-foreground)]"
        type="button"
        title="Clear this type selector"
        :aria-label="`Remove ${typeTitle || typeLabel} selector`"
        @click="emit('dismissType')"
      >×</button>
    </span>
    <div class="ml-auto flex flex-wrap items-center gap-1.5">
      <span v-if="showCodeAll" class="inline-flex" :title="codeAllTitle">
        <button
          class="ch-btn ch-btn-outline"
          type="button"
          :disabled="coding || !canRequestSuggestions"
          @click="emit('codeAll')"
        >{{ coding ? 'Coding…' : 'Get AI suggestions' }}</button>
      </span>
      <RouterLink :class="chipClass(selector === 'uncoded')" :to="uncodedHref" title="Comments that still need an issue type">
        Uncoded ({{ uncodedCount }})
      </RouterLink>
      <RouterLink :class="chipClass(selector === 'disappeared')" :to="disappearedHref" title="Comments gone from the source files">
        Disappeared ({{ disappearedCount }})
      </RouterLink>
    </div>
  </div>
</template>
