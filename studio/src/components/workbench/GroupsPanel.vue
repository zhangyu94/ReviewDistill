<script setup lang="ts">
import type { TaxonomyListResponse } from '../../api/client.ts'
import {
  DRAG_MIME,
  parseDragPayload,
  serializeDragPayload,
  type DragPayload,
  type DropTarget,
} from '../../workbench/dropAction.ts'

defineProps<{
  list: TaxonomyListResponse | null
  selectedId: string
}>()

const emit = defineEmits<{
  select: [id: string]
  drop: [payload: DragPayload, target: DropTarget]
}>()

let dragging = false

function onIssueDragStart(event: DragEvent, id: string) {
  if (!event.dataTransfer)
    return
  dragging = true
  event.dataTransfer.setData(DRAG_MIME, serializeDragPayload({ kind: 'issue', id }))
  event.dataTransfer.effectAllowed = 'move'
}

function onIssueDragEnd() {
  dragging = false
}

function onIssueClick(id: string) {
  if (dragging) {
    dragging = false
    return
  }
  emit('select', id)
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer)
    event.dataTransfer.dropEffect = 'move'
}

function emitDrop(event: DragEvent, target: DropTarget) {
  event.preventDefault()
  const payload = parseDragPayload(event.dataTransfer?.getData(DRAG_MIME) ?? '')
  if (payload)
    emit('drop', payload, target)
}
</script>

<template>
  <div class="flex h-full min-h-0 w-56 shrink-0 flex-col border-r border-[var(--ch-color-border)] bg-[var(--ch-color-background)]">
    <div class="flex h-9 shrink-0 items-center border-b border-[var(--ch-color-border)] px-2">
      <span class="text-xs font-medium">Issue Taxonomy</span>
    </div>
    <div class="min-h-0 flex-1 overflow-auto p-2 text-xs">
      <template v-if="list">
        <div
          v-for="(issues, category) in list.grouped"
          :key="category"
          class="mb-3"
          @dragover="onDragOver"
          @drop="emitDrop($event, { kind: 'category', name: String(category) })"
        >
          <h2 class="ch-kicker">{{ category }}</h2>
          <button
            v-for="row in issues"
            :key="row.id"
            type="button"
            draggable="true"
            class="mb-0.5 flex w-full items-start justify-between gap-1.5 rounded-[4px] px-1.5 py-1 text-left"
            :class="row.id === selectedId ? 'bg-[var(--ch-color-background-muted)]' : ''"
            :title="`Show details for ${row.name}`"
            @click="onIssueClick(row.id)"
            @dragstart="onIssueDragStart($event, row.id)"
            @dragend="onIssueDragEnd"
            @dragover="onDragOver"
            @drop.stop="emitDrop($event, { kind: 'issue', id: row.id })"
          >
            <span class="min-w-0 leading-4">{{ row.name }}</span>
            <span
              class="ch-muted-text shrink-0 tabular-nums leading-4"
              :title="`${row.count} accepted`"
            >{{ row.count }}</span>
          </button>
        </div>
        <p v-if="Object.keys(list.grouped).length === 0" class="ch-muted-text">No issue types yet.</p>
      </template>
    </div>
  </div>
</template>
