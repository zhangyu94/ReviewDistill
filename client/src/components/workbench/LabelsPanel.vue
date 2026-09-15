<script setup lang="ts">
import type { TaxonomyListResponse, TaxonomyNode } from '../../api/client.ts'
import type { DragPayload, DropTarget } from '../../workbench/dropAction.ts'
import type { DropPlacement } from '../../workbench/dropPlacement.ts'
import { computed, ref } from 'vue'
import {
  allowDropHighlight,
  DRAG_MIME,
  parseDragPayload,
  serializeDragPayload,
  showSiblingDropGuide,
} from '../../workbench/dropAction.ts'
import { dropPlacement } from '../../workbench/dropPlacement.ts'
import { canLeafSplit } from '../../workbench/splitControls.ts'
import { descendantIds, findNode, flattenForest, isLeaf } from '../../workbench/taxonomyTree.ts'

const props = defineProps<{
  list: TaxonomyListResponse | null
  selectedId: string
  headerSplitEnabled: boolean
  headerRecycleEnabled: boolean
  llmConfigured: boolean
  splitting: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  drop: [payload: DragPayload, target: DropTarget]
  create: [parentId: string | null]
  flatten: [id: string]
  remove: [id: string]
  split: [id: string | null]
  recycle: []
}>()

let dragging = false
const collapsed = ref(new Set<string>())
const hoverId = ref('')
const dragKind = ref<'comment' | 'label' | ''>('')
const dragId = ref('')
const overId = ref('')
const overPlacement = ref<DropPlacement>('inner')

const rows = computed(() => flattenForest(props.list?.forest ?? []))

function toggle(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) { next.delete(id) }
  else { next.add(id) }
  collapsed.value = next
}

function visibleRows() {
  const out: { node: TaxonomyNode, depth: number, ancestors: string[] }[] = []
  const walk = (nodes: TaxonomyNode[], depth: number, ancestors: string[]) => {
    for (const node of nodes) {
      if (ancestors.some((id) => collapsed.value.has(id))) { continue }
      out.push({ node, depth, ancestors })
      walk(node.children, depth + 1, [...ancestors, node.id])
    }
  }
  walk(props.list?.forest ?? [], 0, [])
  return out
}

const shown = computed(() => visibleRows())

function onLabelDragStart(event: DragEvent, id: string) {
  if (!event.dataTransfer) { return }
  dragging = true
  dragKind.value = 'label'
  dragId.value = id
  event.dataTransfer.setData(DRAG_MIME, serializeDragPayload({ kind: 'label', id }))
  event.dataTransfer.effectAllowed = 'move'
}

function onLabelDragEnd() {
  dragging = false
  dragKind.value = ''
  dragId.value = ''
  overId.value = ''
}

function isDescendantTarget(node: TaxonomyNode): boolean {
  if (!dragId.value) { return false }
  const source = findNode(props.list?.forest ?? [], dragId.value)
  return Boolean(source && descendantIds(source).includes(node.id))
}

function onLabelClick(id: string) {
  if (dragging) {
    dragging = false
    return
  }
  emit('select', id)
}

function placementFor(event: DragEvent, node: TaxonomyNode): DropPlacement {
  const rowEl = (event.currentTarget as HTMLElement).closest('[data-tree-row]') as HTMLElement | null
  const row = rowEl?.getBoundingClientRect() ?? { top: 0, height: 1 }
  const mergeEl = rowEl?.querySelector('[data-merge-zone]')
  const mergeRect = mergeEl ? mergeEl.getBoundingClientRect() : null
  return dropPlacement({
    clientY: event.clientY,
    clientX: event.clientX,
    row: { top: row.top, height: row.height },
    mergeRect,
    isLeaf: isLeaf(node),
  })
}

function onDragOver(event: DragEvent, node: TaxonomyNode) {
  event.preventDefault()
  if (event.dataTransfer) { event.dataTransfer.dropEffect = 'move' }
  if (!allowDropHighlight({
    dragKind: dragKind.value,
    isLeaf: isLeaf(node),
    isSelf: node.id === dragId.value,
    isDescendant: isDescendantTarget(node),
  })) {
    overId.value = ''
    return
  }
  overId.value = node.id
  overPlacement.value = placementFor(event, node)
}

function emitDrop(event: DragEvent, node: TaxonomyNode) {
  event.preventDefault()
  const payload = parseDragPayload(event.dataTransfer?.getData(DRAG_MIME) ?? '')
  const placement = placementFor(event, node)
  overId.value = ''
  dragKind.value = ''
  if (payload) {
    emit('drop', payload, { kind: 'label', id: node.id, placement, isLeaf: isLeaf(node) })
  }
}

function rowClass(node: TaxonomyNode) {
  const selected = node.id === props.selectedId
  const over = overId.value === node.id
  return [
    selected ? 'bg-[var(--ch-color-background-muted)]' : '',
    over && overPlacement.value === 'inner'
      ? 'outline outline-1 outline-[var(--ch-color-foreground)]'
      : '',
  ]
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)]">
    <div class="flex h-9 shrink-0 items-center justify-between border-b border-[var(--ch-color-border)] px-2">
      <span class="text-xs font-medium">Label Taxonomy</span>
      <div class="flex items-center gap-0.5">
        <!-- Header order: fork, plus, recycle. Tree remove uses trash, not comment Delete's trash-can. -->
        <button
          type="button"
          class="inline-flex h-5 w-5 items-center justify-center rounded-[3px] text-[var(--ch-color-muted-foreground)] hover:bg-[var(--ch-color-background-muted)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
          title="Split unlabeled comments into labels with AI"
          :disabled="splitting || !headerSplitEnabled"
          @click="emit('split', null)"
        >
          <span class="i-fa6-solid:code-fork h-3 w-3" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="inline-flex h-5 w-5 items-center justify-center rounded-[3px] text-[var(--ch-color-muted-foreground)] hover:bg-[var(--ch-color-background-muted)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
          title="Add a new root label"
          :disabled="splitting"
          @click="emit('create', null)"
        >
          <span class="i-fa6-solid:plus h-3 w-3" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="inline-flex h-5 w-5 items-center justify-center rounded-[3px] text-[var(--ch-color-muted-foreground)] hover:bg-[var(--ch-color-background-muted)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
          title="Group unlabeled comments into a new label"
          :disabled="splitting || !headerRecycleEnabled"
          @click="emit('recycle')"
        >
          <span class="i-fa6-solid:recycle h-3 w-3" aria-hidden="true" />
        </button>
      </div>
    </div>
    <div class="min-h-0 flex-1 overflow-auto p-1 text-xs">
      <div
        v-for="{ node, depth } in shown"
        :key="node.id"
        class="relative"
      >
        <div
          v-if="overId === node.id && showSiblingDropGuide(dragKind, overPlacement) && overPlacement === 'before'"
          class="absolute left-0 right-0 top-0 h-px bg-[var(--ch-color-foreground)]"
        />
        <div
          v-if="overId === node.id && showSiblingDropGuide(dragKind, overPlacement) && overPlacement === 'after'"
          class="absolute bottom-0 left-0 right-0 h-px bg-[var(--ch-color-foreground)]"
        />
        <div
          data-tree-row
          class="mb-px flex w-full items-center gap-0.5 rounded-[3px] px-1 py-0.5"
          :class="rowClass(node)"
          :style="{ paddingLeft: `${4 + depth * 12}px` }"
          draggable="true"
          @mouseenter="hoverId = node.id"
          @mouseleave="hoverId = ''"
          @dragstart="onLabelDragStart($event, node.id)"
          @dragend="onLabelDragEnd"
          @dragover="onDragOver($event, node)"
          @drop="emitDrop($event, node)"
        >
          <button
            v-if="node.children.length"
            type="button"
            class="inline-flex h-4 w-3 shrink-0 items-center justify-center text-[10px] text-[var(--ch-color-muted-foreground)]"
            :title="collapsed.has(node.id) ? 'Expand' : 'Collapse'"
            @click.stop="toggle(node.id)"
          >
            {{ collapsed.has(node.id) ? '▸' : '▾' }}
          </button>
          <span v-else class="inline-block w-3 shrink-0" />
          <span
            class="min-w-0 flex-1 cursor-pointer truncate leading-4"
            :title="`Show details for ${node.name}`"
            @click="onLabelClick(node.id)"
          >{{ node.name }}</span>
          <div
            v-if="isLeaf(node) && dragKind === 'label' && overId === node.id && (overPlacement === 'inner' || overPlacement === 'merge')"
            data-merge-zone
            class="shrink-0 rounded-[2px] border px-1 leading-4 text-[var(--ch-color-muted-foreground)]"
            :class="overPlacement === 'merge' ? 'border-[var(--ch-color-foreground)]' : 'border-[var(--ch-color-border)]'"
          >
            merge
          </div>
          <template v-if="hoverId === node.id">
            <button
              v-if="canLeafSplit({ isLeaf: isLeaf(node), count: node.count, llmConfigured })"
              type="button"
              class="inline-flex h-4 w-4 shrink-0 items-center justify-center text-[var(--ch-color-muted-foreground)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
              title="Split this label into more specific labels with AI"
              :disabled="splitting"
              @click.stop="emit('split', node.id)"
            >
              <span class="i-fa6-solid:code-fork h-3 w-3" aria-hidden="true" />
            </button>
            <button
              type="button"
              class="inline-flex h-4 w-4 shrink-0 items-center justify-center text-[var(--ch-color-muted-foreground)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
              title="Add a child label"
              :disabled="splitting"
              @click.stop="emit('create', node.id)"
            >
              <span class="i-fa6-solid:plus h-3 w-3" aria-hidden="true" />
            </button>
            <button
              v-if="node.children.length"
              type="button"
              class="inline-flex h-4 w-4 shrink-0 items-center justify-center text-[var(--ch-color-muted-foreground)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
              title="Flatten descendants into this label"
              :disabled="splitting"
              @click.stop="emit('flatten', node.id)"
            >
              <span class="i-fa6-solid:code-merge h-3 w-3" aria-hidden="true" />
            </button>
            <button
              type="button"
              class="inline-flex h-4 w-4 shrink-0 items-center justify-center text-[var(--ch-color-muted-foreground)] hover:text-[var(--ch-color-foreground)] disabled:pointer-events-none disabled:opacity-50"
              title="Remove this label and its descendants"
              :disabled="splitting"
              @click.stop="emit('remove', node.id)"
            >
              <span class="i-fa6-solid:trash h-3 w-3" aria-hidden="true" />
            </button>
          </template>
          <span
            class="ch-muted-text shrink-0 tabular-nums leading-4"
            :title="`${node.count} in subtree`"
          >{{ node.count }}</span>
        </div>
      </div>
      <p v-if="!list || rows.length === 0" class="ch-muted-text px-1.5 py-1">
        No labels yet.
      </p>
    </div>
  </div>
</template>
