<script setup lang="ts">
import type { TaxonomyDetail } from '../../api/client.ts'
import { ref, watch } from 'vue'
import {
  editIssue,
  moveIssue,
  renameIssue,
  splitIssue,
} from '../../api/client.ts'

const props = defineProps<{
  issue: TaxonomyDetail | null
  selectedId: string
  selectedCount: number
  missing: boolean
}>()

const emit = defineEmits<{
  updated: []
  removed: []
  failed: [message: string]
}>()

const editingType = ref(false)
const editingDefinition = ref(false)
const editName = ref('')
const editCode = ref('')
const editCategory = ref('')
const editDefinition = ref('')
const editNotes = ref('')
const left = ref({ code: '', name: '', category: '', definition: '' })
const right = ref({ code: '', name: '', category: '', definition: '' })

function syncFromIssue(issue: TaxonomyDetail) {
  editName.value = issue.name
  editCode.value = issue.code
  editCategory.value = issue.category
  editDefinition.value = issue.definition
  editNotes.value = issue.notes ?? ''
  left.value = {
    code: `${issue.code}A`,
    name: `${issue.name} (A)`,
    category: issue.category,
    definition: issue.definition,
  }
  right.value = {
    code: `${issue.code}B`,
    name: `${issue.name} (B)`,
    category: issue.category,
    definition: issue.definition,
  }
}

watch(
  () => props.issue,
  (issue) => {
    editingType.value = false
    editingDefinition.value = false
    if (!issue) { return }
    syncFromIssue(issue)
  },
  { immediate: true },
)

async function wrap(fn: () => Promise<unknown>, after?: () => void) {
  try {
    await fn()
    after?.()
  }
  catch (err) {
    emit('failed', err instanceof Error ? err.message : String(err))
  }
}

function startTypeEdit() {
  if (!props.issue) { return }
  syncFromIssue(props.issue)
  editingType.value = true
}

function cancelTypeEdit() {
  if (props.issue) { syncFromIssue(props.issue) }
  editingType.value = false
}

function startDefinitionEdit() {
  if (!props.issue) { return }
  syncFromIssue(props.issue)
  editingDefinition.value = true
}

function cancelDefinitionEdit() {
  if (props.issue) { syncFromIssue(props.issue) }
  editingDefinition.value = false
}

async function saveType() {
  const issue = props.issue
  if (!issue) { return }
  await wrap(async () => {
    await renameIssue(issue.id, editName.value, editCode.value)
    if (editCategory.value !== issue.category) { await moveIssue(issue.id, editCategory.value) }
    emit('updated')
  }, () => {
    editingType.value = false
  })
}

async function saveDefinition() {
  const issue = props.issue
  if (!issue) { return }
  await wrap(async () => {
    await editIssue(issue.id, {
      definition: editDefinition.value,
      notes: editNotes.value,
      category: issue.category,
    })
    emit('updated')
  }, () => {
    editingDefinition.value = false
  })
}
</script>

<template>
  <div>
    <p v-if="!selectedId" class="ch-muted-text">
      Select a group.
    </p>
    <p v-else-if="missing">
      This issue type was not found.
    </p>
    <template v-else-if="issue">
      <div class="flex w-full flex-col gap-3">
        <section class="ch-panel">
          <div class="mb-1.5 flex items-center justify-between gap-2">
            <h2 class="ch-kicker mb-0">
              Issue type
            </h2>
            <button
              v-if="!editingType"
              class="ch-btn ch-btn-outline"
              type="button"
              title="Edit this issue type’s name, code, and category"
              @click="startTypeEdit"
            >
              Edit
            </button>
            <div v-else class="flex gap-1.5">
              <button
                class="ch-btn ch-btn-outline"
                type="button"
                title="Discard name, code, and category changes"
                @click="cancelTypeEdit"
              >
                Cancel
              </button>
              <button
                class="ch-btn ch-btn-default"
                type="button"
                title="Save name, code, and category"
                :disabled="!editName.trim() || !editCode.trim() || !editCategory.trim()"
                @click="saveType"
              >
                Save
              </button>
            </div>
          </div>
          <dl class="grid grid-cols-[7.5rem_1fr] gap-x-2 gap-y-1 leading-4">
            <dt class="ch-muted-text">
              Name
            </dt>
            <dd v-if="!editingType" class="font-semibold text-[var(--ch-color-foreground)]">
              {{ issue.name }}
            </dd>
            <dd v-else>
              <input v-model="editName" class="ch-input">
            </dd>
            <dt class="ch-muted-text">
              Code
            </dt>
            <dd v-if="!editingType" class="break-all font-[var(--ch-font-mono)]">
              {{ issue.code }}
            </dd>
            <dd v-else>
              <input v-model="editCode" class="ch-input font-[var(--ch-font-mono)]">
            </dd>
            <dt class="ch-muted-text">
              Category
            </dt>
            <dd v-if="!editingType">
              {{ issue.category }}
            </dd>
            <dd v-else>
              <input v-model="editCategory" class="ch-input" placeholder="e.g. Argumentation">
            </dd>
            <dt class="ch-muted-text">
              Labeled comments
            </dt>
            <dd>{{ selectedCount }}</dd>
          </dl>
        </section>

        <section class="ch-panel">
          <div class="mb-1.5 flex items-center justify-between gap-2">
            <h2 class="ch-kicker mb-0">
              Definition
            </h2>
            <button
              v-if="!editingDefinition"
              class="ch-btn ch-btn-outline"
              type="button"
              title="Edit this issue type’s definition and notes"
              @click="startDefinitionEdit"
            >
              Edit
            </button>
            <div v-else class="flex gap-1.5">
              <button
                class="ch-btn ch-btn-outline"
                type="button"
                title="Discard definition and notes changes"
                @click="cancelDefinitionEdit"
              >
                Cancel
              </button>
              <button
                class="ch-btn ch-btn-default"
                type="button"
                title="Save definition and notes"
                :disabled="!editDefinition.trim()"
                @click="saveDefinition"
              >
                Save
              </button>
            </div>
          </div>
          <template v-if="!editingDefinition">
            <p class="ch-prose whitespace-pre-wrap text-[var(--ch-color-body)]">
              {{ issue.definition }}
            </p>
            <template v-if="issue.notes">
              <p class="ch-muted-text mt-2">
                Notes
              </p>
              <p class="ch-prose mt-0.5 whitespace-pre-wrap">
                {{ issue.notes }}
              </p>
            </template>
            <p class="ch-muted-text mt-2">
              Labeled comments in the Comments panel are the examples for this type.
            </p>
          </template>
          <template v-else>
            <label class="ch-field-label">Definition</label>
            <textarea v-model="editDefinition" class="ch-input mb-2 h-20 py-1.5" />
            <label class="ch-field-label">Notes (optional)</label>
            <textarea v-model="editNotes" class="ch-input h-12 py-1.5" placeholder="Internal notes" />
          </template>
        </section>

        <details class="ch-panel">
          <summary class="cursor-pointer font-medium">
            Split into two types
          </summary>
          <p class="ch-muted-text mt-2 mb-2">
            Replace this type with two more specific ones. This type is deactivated; labeled comments return to Unlabeled so you can assign types again.
          </p>
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <h3 class="mb-1.5 font-medium">
                First type
              </h3>
              <label class="ch-field-label">Code</label>
              <input v-model="left.code" class="ch-input mb-1.5 font-[var(--ch-font-mono)]">
              <label class="ch-field-label">Name</label>
              <input v-model="left.name" class="ch-input mb-1.5">
              <label class="ch-field-label">Category</label>
              <input v-model="left.category" class="ch-input mb-1.5">
              <label class="ch-field-label">Definition</label>
              <textarea v-model="left.definition" class="ch-input h-16 py-1.5" />
            </div>
            <div>
              <h3 class="mb-1.5 font-medium">
                Second type
              </h3>
              <label class="ch-field-label">Code</label>
              <input v-model="right.code" class="ch-input mb-1.5 font-[var(--ch-font-mono)]">
              <label class="ch-field-label">Name</label>
              <input v-model="right.name" class="ch-input mb-1.5">
              <label class="ch-field-label">Category</label>
              <input v-model="right.category" class="ch-input mb-1.5">
              <label class="ch-field-label">Definition</label>
              <textarea v-model="right.definition" class="ch-input h-16 py-1.5" />
            </div>
          </div>
          <button
            class="ch-btn ch-btn-outline mt-3"
            type="button"
            title="Deactivate this type and create the two types described above"
            @click="wrap(async () => { await splitIssue(issue!.id, left, right); emit('removed') })"
          >
            Split
          </button>
        </details>
      </div>
    </template>
  </div>
</template>
