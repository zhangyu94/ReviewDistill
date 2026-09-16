<script setup lang="ts">
import type { InboxItemJson, TaxonomyNode } from '../../api/client.ts'
import type { CommentsLayout } from '../../workbench/workbenchMode.ts'
import { computed } from 'vue'
import { fileRevealAccessibleName, fileRevealLabel } from '../../inboxLocation.ts'
import { commentsTotalLabel } from '../../workbench/commentsHeader.ts'
import { commentTree, flattenCommentTree } from '../../workbench/commentTree.ts'
import { idForPage, pageForId } from '../../workbench/pagination.ts'
import CommentListRow from './CommentListRow.vue'
import CommentPagination from './CommentPagination.vue'

const props = defineProps<{
  layout: CommentsLayout
  items: InboxItemJson[]
  selectedId: string | undefined
  collapsed: Set<string>
  forest?: TaxonomyNode[]
  totalCount: number
  toDistillCount: number
  unlabeled: boolean
  labelOn: boolean
  loading: boolean
  emptyCopy: string
  showLabelWithAi: boolean
  labeling: boolean
  canLabelWithAi: boolean
  labelWithAiTitle: string
}>()

const emit = defineEmits<{
  'select': [id: string]
  'update:layout': [layout: CommentsLayout]
  'update:collapsed': [collapsed: Set<string>]
  'labelWithAi': []
  'assign': [commentId: string, labelId: string]
  'reveal': [id: string]
}>()

const pageIds = computed(() => props.items.map((item) => item.comment.id))
const treeRows = computed(() => flattenCommentTree(commentTree(props.items), props.collapsed))

const currentPage = computed({
  get: () => pageForId(pageIds.value, props.selectedId),
  set: (page: number) => {
    const id = idForPage(pageIds.value, page)
    if (id) { emit('select', id) }
  },
})

function toggleCollapsed(id: string) {
  const next = new Set(props.collapsed)
  if (next.has(id)) { next.delete(id) }
  else { next.add(id) }
  emit('update:collapsed', next)
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
          class="inline-flex h-6 w-6 items-center justify-center p-0.5 rounded-none text-xs font-medium border-e border-[var(--ch-color-border)] hover:bg-[var(--ch-color-background-muted)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--ch-color-ring)]"
          :class="layout === 'tree'
            ? 'bg-[#e5e5e5] text-[var(--ch-color-foreground)]'
            : 'text-[var(--ch-color-muted-foreground)]'"
          type="button"
          title="Show comments in a project file tree"
          aria-label="Show comments in a project file tree"
          :aria-pressed="layout === 'tree'"
          @click="emit('update:layout', 'tree')"
        >
          <span class="i-fa6-solid:folder-tree h-3.5 w-3.5" aria-hidden="true" />
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
    <div v-if="layout === 'list'" class="min-h-0 flex-1 overflow-auto">
      <CommentListRow
        v-for="item in items"
        :key="item.comment.id"
        :item="item"
        :selected="item.comment.id === selectedId"
        :forest="forest ?? []"
        @select="emit('select', $event)"
        @assign="(commentId, labelId) => emit('assign', commentId, labelId)"
        @reveal="emit('reveal', $event)"
      />
      <p v-if="!loading && items.length === 0 && emptyCopy" class="ch-muted-text p-2">
        {{ emptyCopy }}
      </p>
    </div>
    <div v-else-if="layout === 'tree'" class="min-h-0 flex-1 overflow-auto">
      <template v-for="row in treeRows" :key="row.id">
        <div
          v-if="row.kind === 'group'"
          class="flex w-full items-center gap-1 border-b border-[var(--ch-color-border)] py-1 pr-2 text-xs"
          :style="{ paddingLeft: `${8 + row.depth * 12}px` }"
        >
          <button
            type="button"
            class="inline-flex h-4 w-3 shrink-0 items-center justify-center text-[var(--ch-color-muted-foreground)]"
            :title="collapsed.has(row.id) ? 'Expand' : 'Collapse'"
            :aria-label="collapsed.has(row.id) ? `Expand ${row.name}` : `Collapse ${row.name}`"
            :aria-expanded="!collapsed.has(row.id)"
            @click="toggleCollapsed(row.id)"
          >
            <span aria-hidden="true">{{ collapsed.has(row.id) ? '▸' : '▾' }}</span>
          </button>
          <button
            v-if="row.revealId"
            class="ch-link min-w-0 truncate cursor-pointer border-0 bg-transparent p-0 text-left"
            type="button"
            :title="fileRevealLabel()"
            :aria-label="fileRevealAccessibleName(row.name)"
            @click="emit('reveal', row.revealId)"
          >
            {{ row.name }}
          </button>
          <button
            v-else
            class="min-w-0 truncate border-0 bg-transparent p-0 text-left"
            type="button"
            :title="collapsed.has(row.id) ? 'Expand' : 'Collapse'"
            @click="toggleCollapsed(row.id)"
          >
            {{ row.name }}
          </button>
          <span class="ch-muted-text shrink-0">{{ row.count }}</span>
        </div>
        <div v-else-if="row.kind === 'comment'" :style="{ paddingLeft: `${row.depth * 12}px` }">
          <CommentListRow
            :item="row.item"
            :selected="row.item.comment.id === selectedId"
            :forest="forest ?? []"
            location="line"
            @select="emit('select', $event)"
            @assign="(commentId, labelId) => emit('assign', commentId, labelId)"
            @reveal="emit('reveal', $event)"
          />
        </div>
      </template>
      <p v-if="!loading && items.length === 0 && emptyCopy" class="ch-muted-text p-2">
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
