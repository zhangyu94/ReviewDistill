<script setup lang="ts">
import type { TaxonomyDetail } from '../../api/client.ts'
import { computed, ref, watch } from 'vue'
import { editIssue, renameIssue } from '../../api/client.ts'
import {
  canSaveIssueEdit,
  canShowIssueEdit,
  issueDetailsErrorText,
  issueEditSaves,
  nextIssueSaveError,
  shouldReloadAfterIssueSaves,
  shouldSyncIssueEditFromProps,
} from '../../workbench/issueDetailsEdit.ts'

const props = defineProps<{
  issue: TaxonomyDetail | null
  selectedId: string
  missing: boolean
  error: string
}>()

const emit = defineEmits<{
  updated: []
}>()

const editing = ref(false)
const saving = ref(false)
const saveError = ref('')
const editName = ref('')
const editDefinition = ref('')

const showEdit = computed(() => canShowIssueEdit({
  selectedId: props.selectedId,
  missing: props.missing,
  issue: props.issue,
}))

const canSave = computed(() => canSaveIssueEdit(editName.value, editDefinition.value))

const errorText = computed(() => issueDetailsErrorText(saveError.value, props.error))

function syncFromIssue(issue: TaxonomyDetail) {
  editName.value = issue.name
  editDefinition.value = issue.definition
}

watch(
  () => props.issue,
  (issue) => {
    const keepDraft = !shouldSyncIssueEditFromProps(saving.value) && editing.value
    saving.value = false
    saveError.value = nextIssueSaveError({ keepDraft, current: saveError.value })
    if (keepDraft) { return }
    editing.value = false
    if (!issue) { return }
    syncFromIssue(issue)
  },
  { immediate: true },
)

function startEdit() {
  if (!props.issue) { return }
  saveError.value = ''
  syncFromIssue(props.issue)
  editing.value = true
}

function cancelEdit() {
  saveError.value = ''
  if (props.issue) { syncFromIssue(props.issue) }
  editing.value = false
}

async function save() {
  const issue = props.issue
  if (!issue || !canSave.value) { return }
  const calls = issueEditSaves({
    currentName: issue.name,
    currentDefinition: issue.definition,
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
        await renameIssue(issue.id, call.name)
      }
      else {
        await editIssue(issue.id, { definition: call.definition })
      }
      completed += 1
    }
    emit('updated')
    editing.value = false
  }
  catch (err) {
    saveError.value = err instanceof Error ? err.message : String(err)
    if (shouldReloadAfterIssueSaves(completed)) {
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
      <span class="text-xs font-medium">Issue Details</span>
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
      <p v-if="!selectedId" class="ch-muted-text">
        Select a group.
      </p>
      <p v-else-if="missing">
        This issue type was not found.
      </p>
      <template v-else-if="issue">
        <div class="flex w-full flex-col gap-2">
          <section>
            <label v-if="editing" class="ch-field-label" for="issue-details-name">Name</label>
            <p
              v-if="!editing"
              class="font-semibold leading-5 text-[var(--ch-color-foreground)]"
            >
              {{ issue.name }}
            </p>
            <input
              v-else
              id="issue-details-name"
              v-model="editName"
              class="ch-input"
            >
          </section>
          <section>
            <label v-if="editing" class="ch-field-label" for="issue-details-definition">Definition</label>
            <p
              v-if="!editing"
              class="ch-prose whitespace-pre-wrap text-[var(--ch-color-body)]"
            >
              {{ issue.definition }}
            </p>
            <textarea
              v-else
              id="issue-details-definition"
              v-model="editDefinition"
              class="ch-input h-20 py-1.5"
            />
          </section>
        </div>
      </template>
    </div>
  </div>
</template>
