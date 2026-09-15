import type { InboxResponse, LabelDetail, TaxonomyListResponse } from '../api/client.ts'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError, fetchInbox, fetchLabel, fetchLabels } from '../api/client.ts'
import { clearLabelBeforeLoad, labelLoadErrorView, shouldApplyLabelLoad } from './workbenchMode.ts'

export interface InvalidateParts {
  inbox?: boolean
  labels?: boolean
  label?: boolean
}

export const useWorkbenchStore = defineStore('workbench', () => {
  const inbox = ref<InboxResponse | null>(null)
  const labels = ref<TaxonomyListResponse | null>(null)
  const label = ref<LabelDetail | null>(null)
  const missing = ref(false)
  const error = ref('')
  const loading = ref(false)
  const settingsOpen = ref(false)
  let labelLoadGen = 0

  function openSettings() {
    settingsOpen.value = true
  }

  function closeSettings() {
    settingsOpen.value = false
  }

  async function loadInbox() {
    inbox.value = await fetchInbox()
  }

  async function loadLabels() {
    labels.value = await fetchLabels()
  }

  async function loadLabel(id: string) {
    const gen = ++labelLoadGen
    if (clearLabelBeforeLoad(label.value?.id ?? '', id)) {
      label.value = null
    }
    if (!id) {
      missing.value = false
      error.value = ''
      return
    }
    try {
      const next = await fetchLabel(id)
      if (!shouldApplyLabelLoad(gen, labelLoadGen)) { return }
      label.value = next
      missing.value = false
      error.value = ''
    }
    catch (err) {
      if (!shouldApplyLabelLoad(gen, labelLoadGen)) { return }
      const status = err instanceof ApiError ? err.status : null
      if (labelLoadErrorView(status) === 'missing') {
        label.value = null
        missing.value = true
        error.value = ''
      }
      else {
        missing.value = false
        error.value = err instanceof Error ? err.message : String(err)
      }
    }
  }

  async function invalidate(parts: InvalidateParts, labelId = '') {
    const jobs: Promise<void>[] = []
    if (parts.inbox) { jobs.push(loadInbox()) }
    if (parts.labels) { jobs.push(loadLabels()) }
    if (parts.label) { jobs.push(loadLabel(labelId)) }
    await Promise.all(jobs)
  }

  async function refreshAfterHistory(labelId = '') {
    await invalidate({ inbox: true, labels: true, label: true }, labelId)
  }

  async function loadAll(labelId = '') {
    loading.value = true
    error.value = ''
    try {
      await invalidate({ inbox: true, labels: true, label: true }, labelId)
    }
    catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    }
    finally {
      loading.value = false
    }
  }

  return {
    inbox,
    labels,
    label,
    missing,
    error,
    loading,
    settingsOpen,
    openSettings,
    closeSettings,
    loadInbox,
    loadLabels,
    loadLabel,
    invalidate,
    refreshAfterHistory,
    loadAll,
  }
})
