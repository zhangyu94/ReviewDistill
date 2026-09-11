<script setup lang="ts">
import type { InboxItemJson, InboxResponse, TaxonomyDetail, TaxonomyListResponse } from '../api/client.ts'
import type { DragPayload, DropTarget } from '../workbench/dropAction.ts'
import type { CommentsLayout } from '../workbench/workbenchMode.ts'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  changeInbox,
  fetchInbox,
  fetchIssue,
  fetchTaxonomy,
  mergeIssues,
  moveIssue,
  postInbox,
  postInboxCode,
} from '../api/client.ts'
import CommentInspector from '../components/workbench/CommentInspector.vue'
import EntriesPanel from '../components/workbench/EntriesPanel.vue'
import GroupsPanel from '../components/workbench/GroupsPanel.vue'
import IssueInspector from '../components/workbench/IssueInspector.vue'
import SelectorsBar from '../components/workbench/SelectorsBar.vue'
import { inboxLocationRows, safeHttpHref } from '../inboxLocation.ts'
import { nextSelectedId } from '../select.ts'
import { splitContextText } from '../workbench/contextParts.ts'
import { dropAction } from '../workbench/dropAction.ts'
import {
  activeSelector,
  allowChangeDrop,
  disappearedHref,
  dismissTypeHref,
  entryMode,
  groupIdFromRoute,
  inboxItemFromObservation,
  taxonClickHref,
  thisTypeHref,
  typeSelectorLabel,
  uncodedHref,
} from '../workbench/workbenchMode.ts'

function queryStr(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

const route = useRoute()
const router = useRouter()
const mode = computed(() => entryMode(route.name))
const paramsIssueId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))
const groupId = computed(() => groupIdFromRoute(paramsIssueId.value, queryStr(route.query.type)))
const selector = computed(() => activeSelector(route.name, paramsIssueId.value))

const inbox = ref<InboxResponse | null>(null)
const taxonomy = ref<TaxonomyListResponse | null>(null)
const issue = ref<TaxonomyDetail | null>(null)
const missing = ref(false)
const error = ref('')
const notice = ref('')
const loading = ref(false)
const coding = ref(false)
const changeId = ref('')

const lastTypeId = ref('')
watch(groupId, (id) => {
  if (id) { lastTypeId.value = id }
})

const chipTypeId = computed(() => groupId.value || lastTypeId.value)

const queueItems = computed(() => inbox.value?.items ?? [])

const selectedCommentId = computed(() => {
  const q = route.query.id
  const id = typeof q === 'string' ? q : undefined
  if (id && queueItems.value.some((item) => item.comment.id === id)) { return id }
  return queueItems.value[0]?.comment.id
})

const selectedComment = computed(() =>
  queueItems.value.find((item) => item.comment.id === selectedCommentId.value),
)

const selectedObservationId = ref<string | undefined>()
watch(() => mode.value, () => {
  selectedObservationId.value = undefined
})

const commentsLayout = ref<CommentsLayout>('one')

function typeRow(id: string): { code: string, name: string, count: number } | undefined {
  if (!id) { return undefined }
  const grouped = taxonomy.value?.grouped ?? {}
  for (const rows of Object.values(grouped)) {
    const row = rows.find((item) => item.id === id)
    if (row) { return row }
  }
  return undefined
}

const selectedCount = computed(() => typeRow(groupId.value)?.count ?? 0)
const chipTypeName = computed(() => typeRow(chipTypeId.value)?.name ?? issue.value?.name ?? '')
const chipTypeCode = computed(() => typeRow(chipTypeId.value)?.code ?? issue.value?.code ?? '')
const chipTypeCount = computed(() => typeRow(chipTypeId.value)?.count ?? selectedCount.value)
const typeChipLabel = computed(() =>
  chipTypeCode.value ? typeSelectorLabel(chipTypeCode.value, chipTypeCount.value) : '',
)

const listSelectedId = computed(() => {
  if (mode.value !== 'observations') { return selectedCommentId.value }
  return selectedObservationId.value
    ?? (commentsLayout.value === 'one' ? issue.value?.comments[0]?.id : undefined)
})

const selectedObservation = computed(() => {
  const rows = issue.value?.comments ?? []
  const id = listSelectedId.value
  const row = rows.find((item) => item.id === id) ?? rows[0]
  return row ? inboxItemFromObservation(row) : undefined
})

const inspectorItem = computed(() =>
  mode.value === 'observations' ? selectedObservation.value : selectedComment.value,
)

const inspectorView = computed(() => {
  if (mode.value === 'disappeared') { return 'disappeared' as const }
  if (mode.value === 'observations') { return 'observation' as const }
  return 'uncoded' as const
})

const commentTotal = computed(() =>
  mode.value === 'observations' ? (issue.value?.comments.length ?? 0) : queueItems.value.length,
)

const commentSelectedCount = computed(() => (listSelectedId.value ? 1 : 0))

function typeQuery(commentId?: string): Record<string, string> {
  const query: Record<string, string> = {}
  if (groupId.value) { query.type = groupId.value }
  if (commentId) { query.id = commentId }
  return query
}

function gitHref(item: InboxItemJson): string | null {
  return safeHttpHref(item.permalink) ?? safeHttpHref(item.comment.git_url)
}

const locationRows = computed(() => {
  const item = inspectorItem.value
  if (!item) { return [] }
  return inboxLocationRows({
    projectName: item.project_name,
    command: item.comment.source_command,
    filePath: item.comment.file_path,
    lineNumber: item.comment.line_number,
    heading: item.comment.section,
    gitUrl: item.comment.git_url,
    gitCommit: item.comment.git_commit,
    gitHref: gitHref(item),
  })
})

const contextParts = computed(() => splitContextText(inspectorItem.value?.comment.context_text ?? ''))

const suggestionTitle = computed(() => {
  const codingRow = inspectorItem.value?.coding
  if (!codingRow) { return null }
  if (codingRow.kind === 'new') { return codingRow.proposed_issue_name || 'New issue type' }
  const match = inbox.value?.issues.find((row) => row.id === codingRow.issue_type_id)
  return match?.name ?? 'Existing issue type'
})

const canRequestSuggestions = computed(() =>
  Boolean(inbox.value?.llm_provider && inbox.value.pending_code_count),
)

function codeAllTitle(): string {
  if (!inbox.value?.llm_provider) { return 'Configure llm.provider and .reviewdistill/.env first' }
  if (!inbox.value.pending_code_count) { return 'No uncoded comments need suggestions' }
  return 'Ask the LLM to propose issue types for every uncoded comment'
}

async function loadInbox() {
  inbox.value = await fetchInbox(mode.value === 'disappeared' ? 'disappeared' : 'uncoded')
  if (inbox.value.issues[0] && !changeId.value) { changeId.value = inbox.value.issues[0].id }
}

async function loadTaxonomy() {
  taxonomy.value = await fetchTaxonomy()
}

async function loadIssue() {
  missing.value = false
  issue.value = null
  if (!groupId.value) { return }
  try {
    issue.value = await fetchIssue(groupId.value)
  }
  catch {
    missing.value = true
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadInbox(), loadTaxonomy(), loadIssue()])
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    loading.value = false
  }
}

function selectComment(id: string) {
  void router.replace({ query: typeQuery(id) })
}

function onDismissType() {
  lastTypeId.value = ''
  void router.push(dismissTypeHref(selector.value))
}

function onSelectGroup(id: string) {
  const href = taxonClickHref(id)
  if (href) { void router.push(href) }
}

function onSelectEntry(id: string) {
  if (mode.value === 'observations') {
    selectedObservationId.value = id
    return
  }
  selectComment(id)
}

async function codeAll() {
  if (coding.value) { return }
  coding.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await postInboxCode()
    if (result.privacy_warning) { notice.value = result.privacy_warning }
    await loadInbox()
    await loadTaxonomy()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    coding.value = false
  }
}

async function act(action: 'accept' | 'reject' | 'keep' | 'retract') {
  const current = selectedComment.value
  if (!current) { return }
  error.value = ''
  const next = nextSelectedId(queueItems.value.map((item) => item.comment.id), current.comment.id)
  try {
    await postInbox(current.comment.id, action)
    await loadInbox()
    await loadTaxonomy()
    if (action === 'accept') { await loadIssue() }
    await router.replace({ query: typeQuery(next) })
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function change() {
  const current = selectedComment.value
  if (!current || !changeId.value) { return }
  error.value = ''
  const next = nextSelectedId(queueItems.value.map((item) => item.comment.id), current.comment.id)
  try {
    await changeInbox(current.comment.id, changeId.value)
    await loadInbox()
    await loadTaxonomy()
    await loadIssue()
    await router.replace({ query: typeQuery(next) })
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onDrop(payload: DragPayload, target: DropTarget) {
  const action = dropAction(payload, target)
  if (action.type === 'ignore' || !allowChangeDrop(mode.value, action.type)) { return }
  error.value = ''
  try {
    if (action.type === 'change') {
      const ids = queueItems.value.map((item) => item.comment.id)
      const next = nextSelectedId(ids, action.commentId)
      await changeInbox(action.commentId, action.issueTypeId)
      await loadInbox()
      await loadTaxonomy()
      await loadIssue()
      await router.replace({ query: typeQuery(next) })
      return
    }
    if (action.type === 'merge') {
      await mergeIssues([action.sourceId], action.targetId)
      await loadAll()
      if (selector.value === 'type') { await router.push(`/taxonomy/${action.targetId}`) }
      else { await router.replace({ query: { type: action.targetId, ...(selectedCommentId.value ? { id: selectedCommentId.value } : {}) } }) }
      return
    }
    await moveIssue(action.issueTypeId, action.category)
    await loadTaxonomy()
    await loadIssue()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onIssueUpdated() {
  error.value = ''
  await loadTaxonomy()
  await loadIssue()
}

async function onIssueRemoved() {
  error.value = ''
  lastTypeId.value = ''
  await loadTaxonomy()
  await router.push(selector.value === 'disappeared' ? '/inbox/disappeared' : '/')
}

function onCommentsLayout(layout: CommentsLayout) {
  commentsLayout.value = layout
  if (layout === 'one' && mode.value === 'observations' && !selectedObservationId.value) { selectedObservationId.value = issue.value?.comments[0]?.id }
}

function onKey(event: KeyboardEvent) {
  const tag = (event.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return }
  if (event.key !== 'j' && event.key !== 'k') { return }
  const ids = mode.value === 'observations'
    ? (issue.value?.comments ?? []).map((row) => row.id)
    : queueItems.value.map((item) => item.comment.id)
  const current = listSelectedId.value
  const i = current ? ids.indexOf(current) : -1
  const next = event.key === 'j' && i >= 0 && i + 1 < ids.length
    ? ids[i + 1]
    : event.key === 'k' && i > 0
      ? ids[i - 1]
      : undefined
  if (next) { onSelectEntry(next) }
}

async function onTaxonomyChanged() {
  await loadAll()
  if (groupId.value && !typeRow(groupId.value)) { await onIssueRemoved() }
}

async function onLlmChanged() {
  await loadInbox()
}

function openSettings() {
  window.dispatchEvent(new CustomEvent('reviewdistill:open-settings'))
}

onMounted(() => {
  void loadAll()
  window.addEventListener('keydown', onKey)
  window.addEventListener('reviewdistill:taxonomy-changed', onTaxonomyChanged)
  window.addEventListener('reviewdistill:llm-changed', onLlmChanged)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('reviewdistill:taxonomy-changed', onTaxonomyChanged)
  window.removeEventListener('reviewdistill:llm-changed', onLlmChanged)
})
watch(() => route.name, () => { void loadInbox() })
watch(groupId, () => { void loadIssue() })
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <SelectorsBar
      :selector="selector"
      :uncoded-count="inbox?.uncoded_count ?? 0"
      :disappeared-count="inbox?.disappeared_count ?? 0"
      :type-href="thisTypeHref(chipTypeId)"
      :type-label="typeChipLabel"
      :type-title="chipTypeName"
      :uncoded-href="uncodedHref(chipTypeId)"
      :disappeared-href="disappearedHref(chipTypeId)"
      :coding="coding"
      :can-request-suggestions="canRequestSuggestions"
      :code-all-title="codeAllTitle()"
      :show-code-all="mode === 'uncoded'"
      @code-all="codeAll"
      @dismiss-type="onDismissType"
    />
    <div class="flex min-h-0 flex-1">
      <GroupsPanel
        :list="taxonomy"
        :selected-id="groupId"
        @select="onSelectGroup"
        @drop="onDrop"
      />
      <div class="flex min-h-0 min-w-0 flex-1 flex-col border-r border-[var(--ch-color-border)] bg-[var(--ch-color-background-soft)]">
        <div class="flex h-9 shrink-0 items-center border-b border-[var(--ch-color-border)] bg-[var(--ch-color-background)] px-2">
          <span class="text-xs font-medium">Issue Details</span>
        </div>
        <div class="min-h-0 flex-1 overflow-auto p-3 text-xs leading-5">
          <p v-if="error" class="ch-error-text mb-3">
            {{ error }}
          </p>
          <IssueInspector
            :issue="issue"
            :selected-id="groupId"
            :selected-count="selectedCount"
            :missing="missing"
            @updated="onIssueUpdated"
            @removed="onIssueRemoved"
            @failed="error = $event"
          />
        </div>
      </div>
      <div class="flex w-[28rem] shrink-0 flex-col bg-[var(--ch-color-background)]">
        <EntriesPanel
          :mode="mode"
          :layout="commentsLayout"
          :items="queueItems"
          :observation-texts="issue?.comments ?? []"
          :selected-id="listSelectedId"
          :total-count="commentTotal"
          :selected-count="commentSelectedCount"
          :loading="loading"
          :error="error"
          :notice="notice"
          @select="onSelectEntry"
          @update:layout="onCommentsLayout"
        >
          <p v-if="error" class="ch-error-text mb-3">
            {{ error }}
          </p>
          <p v-if="notice" class="ch-muted-text mb-3">
            {{ notice }}
          </p>
          <CommentInspector
            v-if="inspectorItem"
            :view="inspectorView"
            :selected="inspectorItem"
            :data="inbox"
            error=""
            notice=""
            :location-rows="locationRows"
            :context-parts="contextParts"
            :suggestion-title="suggestionTitle"
            :change-id="changeId"
            :issues-empty="!(inbox?.issues.length)"
            @update:change-id="changeId = $event"
            @accept="act('accept')"
            @reject="act('reject')"
            @change="change"
            @keep="act('keep')"
            @retract="act('retract')"
            @configure-llm="openSettings"
          />
          <p v-else class="ch-muted-text">
            Select a comment.
          </p>
        </EntriesPanel>
      </div>
    </div>
  </div>
</template>
