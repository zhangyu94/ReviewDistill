import type { InboxResponse, TaxonomyDetail, TaxonomyListResponse } from '../api/client.ts'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError, fetchInbox, fetchIssue, fetchTaxonomy } from '../api/client.ts'
import { clearIssueBeforeLoad, issueLoadErrorView, shouldApplyIssueLoad } from './workbenchMode.ts'

export interface InvalidateParts {
  inbox?: boolean
  taxonomy?: boolean
  issue?: boolean
}

export const useWorkbenchStore = defineStore('workbench', () => {
  const inbox = ref<InboxResponse | null>(null)
  const taxonomy = ref<TaxonomyListResponse | null>(null)
  const issue = ref<TaxonomyDetail | null>(null)
  const missing = ref(false)
  const error = ref('')
  const loading = ref(false)
  const settingsOpen = ref(false)
  let issueLoadGen = 0

  function openSettings() {
    settingsOpen.value = true
  }

  function closeSettings() {
    settingsOpen.value = false
  }

  async function loadInbox() {
    inbox.value = await fetchInbox()
  }

  async function loadTaxonomy() {
    taxonomy.value = await fetchTaxonomy()
  }

  async function loadIssue(id: string) {
    const gen = ++issueLoadGen
    if (clearIssueBeforeLoad(issue.value?.id ?? '', id)) {
      issue.value = null
    }
    if (!id) {
      missing.value = false
      error.value = ''
      return
    }
    try {
      const next = await fetchIssue(id)
      if (!shouldApplyIssueLoad(gen, issueLoadGen)) { return }
      issue.value = next
      missing.value = false
      error.value = ''
    }
    catch (err) {
      if (!shouldApplyIssueLoad(gen, issueLoadGen)) { return }
      const status = err instanceof ApiError ? err.status : null
      if (issueLoadErrorView(status) === 'missing') {
        issue.value = null
        missing.value = true
        error.value = ''
      }
      else {
        missing.value = false
        error.value = err instanceof Error ? err.message : String(err)
      }
    }
  }

  async function invalidate(parts: InvalidateParts, issueId = '') {
    const jobs: Promise<void>[] = []
    if (parts.inbox) { jobs.push(loadInbox()) }
    if (parts.taxonomy) { jobs.push(loadTaxonomy()) }
    if (parts.issue) { jobs.push(loadIssue(issueId)) }
    await Promise.all(jobs)
  }

  async function refreshAfterHistory(issueId = '') {
    await invalidate({ inbox: true, taxonomy: true, issue: true }, issueId)
  }

  async function loadAll(issueId = '') {
    loading.value = true
    error.value = ''
    try {
      await invalidate({ inbox: true, taxonomy: true, issue: true }, issueId)
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
    taxonomy,
    issue,
    missing,
    error,
    loading,
    settingsOpen,
    openSettings,
    closeSettings,
    loadInbox,
    loadTaxonomy,
    loadIssue,
    invalidate,
    refreshAfterHistory,
    loadAll,
  }
})
