<script setup lang="ts">
import type { InboxItemJson, TaxonomyNode } from '../../api/client.ts'
import type { CommentsLayout } from '../../workbench/workbenchMode.ts'
import { computed } from 'vue'
import { commentListLeafLabelNames } from '../../workbench/commentList.ts'
import { commentsTotalLabel } from '../../workbench/commentsHeader.ts'
import { DRAG_MIME, serializeDragPayload } from '../../workbench/dropAction.ts'
import { idForPage, pageForId } from '../../workbench/pagination.ts'
import CommentPagination from './CommentPagination.vue'

const props = defineProps<{
  layout: CommentsLayout
  items: InboxItemJson[]
  selectedId: string | undefined
  forest?: TaxonomyNode[]
  totalCount: number
  toDistillCount: number
  unlabeled: boolean
  labelOn: boolean
  loading: boolean
  emptyCopy: string
  error?: string
  notice?: string
  showLabelWithAi: boolean
  labeling: boolean
  canLabelWithAi: boolean
  labelWithAiTitle: string
}>()

const emit = defineEmits<{
  'select': [id: string]
  'update:layout': [layout: CommentsLayout]
  'labelWithAi': []
}>()

const pageIds = computed(() => props.items.map((item) => item.comment.id))

const currentPage = computed({
  get: () => pageForId(pageIds.value, props.selectedId),
  set: (page: number) => {
    const id = idForPage(pageIds.value, page)
    if (id) { emit('select', id) }
  },
})

function onCommentDragStart(event: DragEvent, id: string) {
  if (!event.dataTransfer) { return }
  event.dataTransfer.setData(DRAG_MIME, serializeDragPayload({ kind: 'comment', id }))
  event.dataTransfer.effectAllowed = 'move'
}

function leafTypeLabel(item: InboxItemJson): string {
  return commentListLeafLabelNames(item, props.forest ?? [])
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col">
    <div class="flex min-h-9 shrink-0 flex-wrap items-center gap-1.5 border-b border-[var(--ch-color-border)] px-2 py-1 text-xs">
      <span class="font-medium">Comments</span>
      <div
        class="inline-flex overflow-hidden rounded-[4px] border border-[var(--ch-color-border)]"
        role="group"
        aria-label="Comment layout"
      >
        <button
          class="inline-flex h-6 w-6 items-center justify-center p-0.5 rounded-none text-xs font-medium border-e border-[var(--ch-color-border)] hover:bg-[var(--ch-color-background-muted)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--ch-color-ring)]"
          :class="layout === 'list'
            ? 'bg-[#e5e5e5] text-[var(--ch-color-foreground)]'
            : 'text-[var(--ch-color-muted-foreground)]'"
          type="button"
          title="Show a list of comments for scanning"
          aria-label="Show a list of comments for scanning"
          :aria-pressed="layout === 'list'"
          @click="emit('update:layout', 'list')"
        >
          <span class="i-fa6-solid:list h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button
          class="inline-flex h-6 w-6 items-center justify-center p-0.5 rounded-none text-xs font-medium hover:bg-[var(--ch-color-background-muted)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--ch-color-ring)]"
          :class="layout === 'one'
            ? 'bg-[#e5e5e5] text-[var(--ch-color-foreground)]'
            : 'text-[var(--ch-color-muted-foreground)]'"
          type="button"
          title="Show one comment at a time with context and location"
          aria-label="Show one comment at a time with context and location"
          :aria-pressed="layout === 'one'"
          @click="emit('update:layout', 'one')"
        >
          <span class="i-fa6-regular:square h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <span class="ml-auto inline-flex items-center gap-1.5">
        <span v-if="showLabelWithAi" class="inline-flex" :title="labelWithAiTitle">
          <button
            class="ch-btn ch-btn-outline gap-1"
            type="button"
            :disabled="labeling || !canLabelWithAi"
            @click="emit('labelWithAi')"
          >
            <span class="i-fa6-solid:wand-magic-sparkles h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {{ labeling ? 'Labeling…' : 'Label with AI' }}
          </button>
        </span>
        <span class="ch-muted-text">{{ commentsTotalLabel(totalCount, { unlabeled, labelOn }, toDistillCount) }}</span>
      </span>
    </div>
    <p v-if="error" class="ch-error-text px-2 pt-2">
      {{ error }}
    </p>
    <p v-if="notice" class="ch-muted-text px-2 pt-2">
      {{ notice }}
    </p>
    <div v-if="layout === 'list'" class="min-h-0 flex-1 overflow-auto">
      <button
        v-for="item in items"
        :key="item.comment.id"
        type="button"
        class="block w-full border-b border-[var(--ch-color-border)] px-2 py-1.5 text-left text-xs"
        :class="item.comment.id === selectedId ? 'bg-[var(--ch-color-background-muted)]' : ''"
        :title="item.comment.raw_text"
        :draggable="!item.labeled"
        @click="emit('select', item.comment.id)"
        @dragstart="!item.labeled ? onCommentDragStart($event, item.comment.id) : undefined"
      >
        <div class="line-clamp-2">
          {{ item.comment.raw_text }}
        </div>
        <div class="ch-muted-text mt-0.5 flex flex-wrap items-center gap-1">
          <span>{{ item.project_name }} · {{ item.comment.file_path }}:{{ item.comment.line_number }}</span>
          <span
            v-if="!item.in_manuscript"
            class="ch-chip ch-chip-idle"
            title="This remark is no longer in the .tex file."
          >Left the manuscript</span>
        </div>
        <div
          v-if="leafTypeLabel(item)"
          class="ch-muted-text mt-0.5"
        >
          {{ leafTypeLabel(item) }}
        </div>
      </button>
      <p v-if="!loading && items.length === 0" class="ch-muted-text p-2">
        {{ emptyCopy }}
      </p>
    </div>
    <div v-else class="flex min-h-0 flex-1 flex-col">
      <div
        class="min-h-0 min-w-0 w-full flex-1 overflow-auto"
        :class="{ 'p-3 text-xs leading-5': items.length > 0 }"
      >
        <slot />
      </div>
      <CommentPagination
        v-model="currentPage"
        :page-count="pageIds.length"
      />
    </div>
  </div>
</template>
