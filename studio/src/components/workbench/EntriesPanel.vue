<script setup lang="ts">
import { computed } from 'vue'
import type { InboxItemJson } from '../../api/client.ts'
import { DRAG_MIME, serializeDragPayload } from '../../workbench/dropAction.ts'
import { idForPage, pageForId } from '../../workbench/pagination.ts'
import type { CommentsLayout, EntryMode } from '../../workbench/workbenchMode.ts'
import CommentPagination from './CommentPagination.vue'

const props = defineProps<{
  mode: EntryMode
  layout: CommentsLayout
  items: InboxItemJson[]
  observationTexts: { id: string, raw_text: string }[]
  selectedId: string | undefined
  totalCount: number
  selectedCount: number
  loading: boolean
  error?: string
  notice?: string
}>()

const emit = defineEmits<{
  select: [id: string]
  'update:layout': [layout: CommentsLayout]
}>()

const pageIds = computed(() => {
  if (props.mode === 'observations')
    return props.observationTexts.map(row => row.id)
  return props.items.map(item => item.comment.id)
})

const currentPage = computed({
  get: () => pageForId(pageIds.value, props.selectedId),
  set: (page: number) => {
    const id = idForPage(pageIds.value, page)
    if (id)
      emit('select', id)
  },
})

function onCommentDragStart(event: DragEvent, id: string) {
  if (!event.dataTransfer)
    return
  event.dataTransfer.setData(DRAG_MIME, serializeDragPayload({ kind: 'comment', id }))
  event.dataTransfer.effectAllowed = 'move'
}

function emptyCopy(mode: EntryMode): string {
  if (mode === 'disappeared')
    return 'No disappeared comments.'
  if (mode === 'observations')
    return 'No accepted comments on this type yet.'
  return 'No uncoded observations.'
}

function pct(item: InboxItemJson): string | null {
  const c = item.coding?.confidence
  if (c == null)
    return null
  return `${Math.round(c * 100)}%`
}

function toggleClass(active: boolean): string {
  return active ? 'ch-chip ch-chip-active' : 'ch-chip ch-chip-idle'
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col">
    <div class="flex h-9 shrink-0 items-center gap-1.5 border-b border-[var(--ch-color-border)] px-2 text-xs">
      <span class="font-medium">Comments</span>
      <button
        :class="toggleClass(layout === 'list')"
        type="button"
        title="Show a list of comments for scanning"
        aria-label="Show a list of comments for scanning"
        :aria-pressed="layout === 'list'"
        @click="emit('update:layout', 'list')"
      >
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path stroke="currentColor" stroke-width="1.5" d="M2 4h12M2 8h12M2 12h12" />
        </svg>
      </button>
      <button
        :class="toggleClass(layout === 'one')"
        type="button"
        title="Show one comment at a time with context and location"
        aria-label="Show one comment at a time with context and location"
        :aria-pressed="layout === 'one'"
        @click="emit('update:layout', 'one')"
      >
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect width="10" height="12" x="3" y="2" stroke="currentColor" stroke-width="1.5" rx="1" />
        </svg>
      </button>
      <span class="ch-muted-text ml-auto">{{ totalCount }} total · {{ selectedCount }} selected</span>
    </div>
    <div v-if="layout === 'list'" class="min-h-0 flex-1 overflow-auto">
      <p v-if="error" class="ch-error-text px-2 pt-2">{{ error }}</p>
      <p v-if="notice" class="ch-muted-text px-2 pt-2">{{ notice }}</p>
      <template v-if="mode === 'observations'">
        <button
          v-for="row in observationTexts"
          :key="row.id"
          type="button"
          class="block w-full border-b border-[var(--ch-color-border)] px-2 py-1.5 text-left text-xs"
          :class="row.id === selectedId ? 'bg-[var(--ch-color-background-muted)]' : ''"
          :title="row.raw_text"
          @click="emit('select', row.id)"
        >
          <div class="line-clamp-2">{{ row.raw_text }}</div>
        </button>
        <p v-if="!loading && observationTexts.length === 0" class="ch-muted-text p-2">{{ emptyCopy(mode) }}</p>
      </template>
      <template v-else>
        <button
          v-for="item in items"
          :key="item.comment.id"
          type="button"
          class="block w-full border-b border-[var(--ch-color-border)] px-2 py-1.5 text-left text-xs"
          :class="item.comment.id === selectedId ? 'bg-[var(--ch-color-background-muted)]' : ''"
          :title="item.comment.raw_text"
          :draggable="mode === 'uncoded'"
          @click="emit('select', item.comment.id)"
          @dragstart="mode === 'uncoded' ? onCommentDragStart($event, item.comment.id) : undefined"
        >
          <div class="line-clamp-2">{{ item.comment.raw_text }}</div>
          <div class="ch-muted-text mt-0.5">
            {{ item.project_name }} · {{ item.comment.file_path }}:{{ item.comment.line_number }}
            <span v-if="mode === 'uncoded' && pct(item)"> · {{ pct(item) }}</span>
            <span v-else-if="mode === 'disappeared'"> · {{ item.guess }}</span>
          </div>
        </button>
        <p v-if="!loading && items.length === 0" class="ch-muted-text p-2">{{ emptyCopy(mode) }}</p>
      </template>
    </div>
    <div v-else class="flex min-h-0 flex-1 flex-col">
      <div class="min-h-0 flex-1 overflow-auto p-3 text-xs leading-5">
        <slot />
      </div>
      <CommentPagination
        v-model="currentPage"
        :page-count="pageIds.length"
      />
    </div>
  </div>
</template>
