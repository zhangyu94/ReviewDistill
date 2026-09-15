<script setup lang="ts">
import type { LabelDetail } from '../../api/client.ts'
import { computed, ref, watch } from 'vue'
import { editLabel, renameLabel } from '../../api/client.ts'
import {
  canSaveLabelEdit,
  canShowLabelEdit,
  labelDetailsEmptyCopy,
  labelDetailsErrorText,
  labelEditSaves,
  nextLabelSaveError,
  shouldReloadAfterLabelSaves,
  shouldSyncLabelEditFromProps,
} from '../../workbench/labelDetailsEdit.ts'

const props = defineProps<{
  label: LabelDetail | null
  selectedId: string
  missing: boolean
  error: string
  loading: boolean
}>()

const emit = defineEmits<{
  updated: []
}>()

const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const editName = ref('')
const editDefinition = ref('')

const showEdit = computed(() => canShowLabelEdit({
  selectedId: props.selectedId,
  missing: props.missing,
  label: props.label,
}))

const canSave = computed(() => canSaveLabelEdit(editName.value, editDefinition.value))

const errorText = computed(() => labelDetailsErrorText(saveError.value, props.error, props.loading))

const emptyCopy = computed(() => labelDetailsEmptyCopy({
  selectedId: props.selectedId,
  missing: props.missing,
  hasLabel: props.label != null,
  loading: props.loading,
  hasError: Boolean(errorText.value),
}))

function syncFromLabel(label: LabelDetail) {
  editName.value = label.name
  editDefinition.value = label.definition
}

watch(
  () => props.label,
  (label) => {
    const keepDraft = !shouldSyncLabelEditFromProps(saving.value) && editing.value
    saving.value = false
    saveError.value = nextLabelSaveError({ keepDraft, current: saveError.value })
    if (keepDraft) { return }
    editing.value = false
    if (!label) { return }
    syncFromLabel(label)
  },
  { immediate: true },
)

function startEdit() {
  if (!props.label) { return }
  saveError.value = ''
  syncFromLabel(props.label)
  editing.value = true
}

function cancelEdit() {
  saveError.value = ''
  if (props.label) { syncFromLabel(props.label) }
  editing.value = false
}

async function save() {
  const label = props.label
  if (!label || !canSave.value) { return }
  const calls = labelEditSaves({
    currentName: label.name,
    currentDefinition: label.definition,
    nextName: editName.value,
    nextDefinition: editDefinition.value,
  })
  if (calls.length === 0) {
    editing.value = false
    return
  }
  let completed = 0
  saving.value = true
  saveError.value = ''
  try {
    for (const call of calls) {
      if (call.kind === 'rename') {
        await renameLabel(label.id, call.name)
      }
      else {
        await editLabel(label.id, { definition: call.definition })
      }
      completed += 1
    }
    emit('updated')
    editing.value = false
  }
  catch (err) {
    saveError.value = err instanceof Error ? err.message : String(err)
    if (shouldReloadAfterLabelSaves(completed)) {
      emit('updated')
    }
    else {
      saving.value = false
    }
  }
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 shrink-0 flex-col">
    <div class="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-[var(--ch-color-border)] px-2">
      <span class="text-xs font-medium">Label Details</span>
      <template v-if="showEdit">
        <button
          v-if="!editing"
          class="ch-btn ch-btn-outline"
          type="button"
          title="Edit name and definition"
          @click="startEdit"
        >
          Edit
        </button>
        <div v-else class="flex gap-1.5">
          <button
            class="ch-btn ch-btn-outline"
            type="button"
            title="Discard name and definition changes"
            @click="cancelEdit"
          >
            Cancel
          </button>
          <button
            class="ch-btn ch-btn-default"
            type="button"
            title="Save name and definition"
            :disabled="!canSave"
            @click="save"
          >
            Save
          </button>
        </div>
      </template>
    </div>
    <div class="min-h-0 max-h-40 overflow-auto p-3 text-xs leading-5">
      <p v-if="errorText" class="ch-error-text mb-3">
        {{ errorText }}
      </p>
      <p
        v-if="emptyCopy"
        :class="missing ? '' : 'ch-muted-text'"
      >
        {{ emptyCopy }}
      </p>
      <template v-else-if="label">
        <div class="flex w-full flex-col gap-2">
          <section>
            <label v-if="editing" class="ch-field-label" for="label-details-name">Name</label>
            <p
              v-if="!editing"
              class="font-semibold leading-5 text-[var(--ch-color-foreground)]"
            >
              {{ label.name }}
            </p>
            <input
              v-else
              id="label-details-name"
              v-model="editName"
              class="ch-input"
            >
          </section>
          <section>
            <label v-if="editing" class="ch-field-label" for="label-details-definition">Definition</label>
            <p
              v-if="!editing"
              class="ch-prose whitespace-pre-wrap text-[var(--ch-color-body)]"
            >
              {{ label.definition }}
            </p>
            <textarea
              v-else
              id="label-details-definition"
              v-model="editDefinition"
              class="ch-input h-20 py-1.5"
            />
          </section>
        </div>
      </template>
    </div>
  </div>
</template>
