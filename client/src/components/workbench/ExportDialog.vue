<script setup lang="ts">
import type { ExportFormat } from '../../api/client.ts'
import { computed, ref } from 'vue'
import { exportFilename, fetchExport } from '../../api/client.ts'
import {
  allTypeIds,
  canDownloadExport,
  toggleCheckedId,
} from '../../workbench/exportSelection.ts'
import { flattenForest } from '../../workbench/taxonomyTree.ts'
import { useWorkbenchStore } from '../../workbench/workbenchStore.ts'

const open = ref(false)
const fmt = ref<ExportFormat>('md')
const store = useWorkbenchStore()
const error = ref('')
const busy = ref(false)
const checked = ref<string[]>([])
const list = computed(() => store.taxonomy)
const rows = computed(() => flattenForest(list.value?.forest ?? []))
const canDownload = computed(() => canDownloadExport(checked.value))

const formats: { id: ExportFormat, label: string }[] = [
  { id: 'md', label: 'Markdown' },
  { id: 'yaml', label: 'YAML' },
  { id: 'json', label: 'JSON' },
]

async function show() {
  open.value = true
  error.value = ''
  await store.invalidate({ taxonomy: true })
  checked.value = allTypeIds(list.value?.forest ?? [])
}

function hide() {
  open.value = false
}

function onToggle(id: string) {
  checked.value = toggleCheckedId(list.value?.forest ?? [], checked.value, id)
}

async function download() {
  if (!canDownload.value) { return }
  busy.value = true
  error.value = ''
  try {
    const text = await fetchExport(fmt.value, checked.value)
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

defineExpose({ show })
</script>

<template>
  <button class="ch-chip ch-chip-idle gap-1" type="button" title="Download the rubric" @click="show">
    <span class="i-fa6-solid:download h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    Export
  </button>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="w-full max-w-md rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-4 text-xs shadow-lg">
      <div class="mb-3 flex items-center gap-1.5">
        <h2 class="font-semibold">
          Export
        </h2>
        <button
          class="ch-btn ch-btn-outline ml-auto px-1.5"
          type="button"
          title="Close"
          aria-label="Close"
          @click="hide"
        >
          <span class="i-fa6-solid:xmark h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <p v-if="error" class="ch-error-text mb-2">
        {{ error }}
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
      <p class="ch-muted-text mb-1.5">
        Types to include. Unchecked types stay in the taxonomy.
      </p>
      <div
        v-if="rows.length"
        class="mb-3 max-h-56 overflow-auto rounded-[4px] border border-[var(--ch-color-border)] py-1"
        role="tree"
        aria-label="Issue types to export"
        aria-multiselectable="true"
      >
        <label
          v-for="{ node, depth } in rows"
          :key="node.id"
          class="flex cursor-pointer items-center gap-1.5 px-2 py-0.5 hover:bg-[var(--ch-color-background-muted)]"
          :style="{ paddingLeft: `${8 + depth * 12}px` }"
          role="treeitem"
          :aria-checked="checked.includes(node.id)"
        >
          <input
            class="shrink-0"
            type="checkbox"
            :checked="checked.includes(node.id)"
            :title="`Include ${node.name} in the download`"
            @change="onToggle(node.id)"
          >
          <span class="truncate">{{ node.name }}</span>
        </label>
      </div>
      <p v-else class="ch-muted-text mb-3">
        No issue types yet.
      </p>
      <div class="flex justify-end">
        <button
          class="ch-btn ch-btn-default"
          type="button"
          :title="`Download ${exportFilename(fmt)}`"
          :disabled="busy || !canDownload"
          @click="download"
        >
          Download {{ exportFilename(fmt) }}
        </button>
      </div>
    </div>
  </div>
</template>
