<script setup lang="ts">
import type { ExportFormat, TaxonomyListResponse } from '../../api/client.ts'
import { ref } from 'vue'
import {
  deactivateIssue,
  exportFilename,
  fetchExport,
  fetchTaxonomy,
} from '../../api/client.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const open = ref(false)
const fmt = ref<ExportFormat>('md')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const list = ref<TaxonomyListResponse | null>(null)
const deactivateId = ref('')

const formats: { id: ExportFormat, label: string }[] = [
  { id: 'md', label: 'Markdown' },
  { id: 'yaml', label: 'YAML' },
  { id: 'json', label: 'JSON' },
]

function allIssues() {
  const grouped = list.value?.grouped ?? {}
  return Object.entries(grouped).flatMap(([category, issues]) =>
    issues.map((row) => ({ ...row, category })),
  )
}

function onDeactivateId(value: unknown) {
  if (typeof value === 'string') { deactivateId.value = value }
}

async function loadList() {
  list.value = await fetchTaxonomy()
}

async function show() {
  open.value = true
  error.value = ''
  notice.value = ''
  await loadList()
}

function hide() {
  open.value = false
}

async function download() {
  busy.value = true
  error.value = ''
  try {
    const text = await fetchExport(fmt.value)
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const href = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = href
    link.download = exportFilename(fmt.value)
    link.click()
    URL.revokeObjectURL(href)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}

async function deactivate() {
  if (!deactivateId.value) { return }
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await deactivateIssue(deactivateId.value)
    notice.value = 'Group deactivated.'
    deactivateId.value = ''
    await loadList()
    window.dispatchEvent(new CustomEvent('reviewdistill:taxonomy-changed'))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}

defineExpose({ show })
</script>

<template>
  <button class="ch-chip ch-chip-idle gap-1" type="button" title="Download the rubric or deactivate a group" @click="show">
    <svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path stroke="currentColor" stroke-width="1.5" stroke-linecap="round" d="M8 3v7M5.5 7.5 8 10l2.5-2.5" />
      <path stroke="currentColor" stroke-width="1.5" stroke-linecap="round" d="M3.5 12.5h9" />
    </svg>
    Export
  </button>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="w-full max-w-md rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-4 text-xs shadow-lg">
      <h2 class="mb-3 font-semibold">
        Export
      </h2>
      <p v-if="error" class="ch-error-text mb-2">
        {{ error }}
      </p>
      <p v-if="notice" class="ch-muted-text mb-2">
        {{ notice }}
      </p>
      <p class="ch-muted-text mb-1.5">
        Format
      </p>
      <div class="mb-3 flex flex-wrap gap-1.5">
        <button
          v-for="row in formats"
          :key="row.id"
          class="ch-chip"
          :class="fmt === row.id ? 'ch-chip-active' : 'ch-chip-idle'"
          type="button"
          :title="`Export the rubric as ${row.label}`"
          @click="fmt = row.id"
        >
          {{ row.label }}
        </button>
      </div>
      <button
        class="ch-btn ch-btn-default mb-4"
        type="button"
        :title="`Download ${exportFilename(fmt)}`"
        :disabled="busy"
        @click="download"
      >
        Download {{ exportFilename(fmt) }}
      </button>
      <h3 class="mb-1.5 font-medium">
        Deactivate a group
      </h3>
      <p class="ch-muted-text mb-2">
        Hide a type from the active taxonomy. Labeled comments return to Unlabeled. Undo restores the labels.
      </p>
      <Select :model-value="deactivateId || undefined" @update:model-value="onDeactivateId">
        <SelectTrigger class="mb-2 w-full" title="Issue type to hide from the active taxonomy">
          <SelectValue placeholder="Choose a group" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="row in allIssues()" :key="row.id" :value="row.id">
            {{ row.code }} · {{ row.name }}
          </SelectItem>
        </SelectContent>
      </Select>
      <div class="flex justify-end gap-1.5">
        <button class="ch-btn ch-btn-outline" type="button" title="Close this dialog" @click="hide">
          Close
        </button>
        <button
          class="ch-btn ch-btn-outline"
          type="button"
          title="Hide the chosen type from the active taxonomy"
          :disabled="busy || !deactivateId"
          @click="deactivate"
        >
          Deactivate
        </button>
      </div>
    </div>
  </div>
</template>
