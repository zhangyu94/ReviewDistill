<script setup lang="ts">
/** List card: text selects and (if unlabeled) drags; menu and file control cannot nest inside a wrapping button. Label menu is compact chrome on its own line. */
import type { InboxItemJson, TaxonomyNode } from '../../api/client.ts'
import { computed } from 'vue'
import { fileRevealAccessibleName, fileRevealLabel } from '../../inboxLocation.ts'
import { shouldAssignOnSelect } from '../../workbench/assignLabel.ts'
import { commentListLocationLabel } from '../../workbench/commentList.ts'
import { DRAG_MIME, serializeDragPayload } from '../../workbench/dropAction.ts'
import { assignableLabelRows } from '../../workbench/taxonomyTree.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const props = defineProps<{
  item: InboxItemJson
  selected: boolean
  forest: TaxonomyNode[]
  location?: 'full' | 'line'
}>()

const emit = defineEmits<{
  select: [id: string]
  assign: [commentId: string, labelId: string]
  reveal: [id: string]
}>()

const changeLabels = computed(() =>
  assignableLabelRows(props.forest, props.item.label?.id),
)
const changeEmpty = computed(() => changeLabels.value.length === 0)
const menuValue = computed(() => props.item.label?.id ?? '')
const changeMenuTitle = computed(() => (
  changeEmpty.value
    ? 'No labels yet. Accept a new-label suggestion first.'
    : 'The menu shows the current label. Pick another label to assign it.'
))
const locationLabel = computed(() => commentListLocationLabel(props.item.comment.line_number))

function onAssignId(value: unknown) {
  if (typeof value !== 'string') { return }
  if (!shouldAssignOnSelect(props.item.label?.id, value)) { return }
  emit('assign', props.item.comment.id, value)
}

function onCommentDragStart(event: DragEvent) {
  if (props.item.labeled || !event.dataTransfer) { return }
  event.dataTransfer.setData(DRAG_MIME, serializeDragPayload({ kind: 'comment', id: props.item.comment.id }))
  event.dataTransfer.effectAllowed = 'move'
}
</script>

<template>
  <div
    class="w-full border-b border-[var(--ch-color-border)] px-2 py-1.5 text-xs"
    :class="selected ? 'bg-[var(--ch-color-background-muted)]' : ''"
  >
    <button
      type="button"
      class="block w-full text-left"
      :title="item.comment.raw_text"
      :draggable="!item.labeled"
      @click="emit('select', item.comment.id)"
      @dragstart="!item.labeled ? onCommentDragStart($event) : undefined"
    >
      <div class="line-clamp-2">
        {{ item.comment.raw_text }}
      </div>
    </button>
    <div class="ch-muted-text mt-0.5 flex flex-wrap items-center gap-1">
      <span v-if="location !== 'line'">{{ item.project_name }} · <button
        v-if="item.local_file"
        class="ch-link cursor-pointer border-0 bg-transparent p-0 text-left"
        type="button"
        :title="fileRevealLabel()"
        :aria-label="fileRevealAccessibleName(item.comment.file_path)"
        @click="emit('reveal', item.comment.id)"
      >{{ item.comment.file_path }}</button><template
        v-else
      >{{ item.comment.file_path }}</template> · {{ locationLabel }}</span>
      <span v-else>{{ locationLabel }}</span>
      <span
        v-if="!item.in_manuscript"
        class="ch-chip ch-chip-idle"
        title="This remark is no longer in the .tex file."
      >Left the manuscript</span>
    </div>
    <div class="mt-0.5 flex min-w-0 items-center gap-1.5">
      <span class="ch-muted-text shrink-0">Label</span>
      <Select
        :model-value="menuValue || undefined"
        :disabled="changeEmpty"
        @update:model-value="onAssignId"
      >
        <SelectTrigger class="h-6 w-auto max-w-full" :title="changeMenuTitle">
          <SelectValue placeholder="Choose a label…" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="row in changeLabels" :key="row.id" :value="row.id">
            <span :style="{ paddingLeft: `${row.depth * 12}px` }">{{ row.name }}</span>
          </SelectItem>
        </SelectContent>
      </Select>
    </div>
  </div>
</template>
