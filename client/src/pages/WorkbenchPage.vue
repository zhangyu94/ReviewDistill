<script setup lang="ts">
import type { InboxItemJson } from '../api/client.ts'
import type { DragPayload, DropTarget } from '../workbench/dropAction.ts'
import type { CommentsLayout } from '../workbench/workbenchMode.ts'
import type { InvalidateParts } from '../workbench/workbenchStore.ts'
import { storeToRefs } from 'pinia'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  changeInbox,
  createIssue,
  flattenIssue,
  mergeIssues,
  moveIssue,
  postInbox,
  postInboxCode,
  removeIssue,
} from '../api/client.ts'
import CommentInspector from '../components/workbench/CommentInspector.vue'
import EntriesPanel from '../components/workbench/EntriesPanel.vue'
import GroupsPanel from '../components/workbench/GroupsPanel.vue'
import IssueInspector from '../components/workbench/IssueInspector.vue'
import SelectorsBar from '../components/workbench/SelectorsBar.vue'
import { inboxLocationRows, safeHttpHref } from '../inboxLocation.ts'
import { selectedIdAfterAction } from '../select.ts'
import { splitContextText } from '../workbench/contextParts.ts'
import { dropAction } from '../workbench/dropAction.ts'
import { descendantIds, findNode, moveBody } from '../workbench/taxonomyTree.ts'
import {
  activeSelector,
  afterMergeNavigation,
  allowChangeDrop,
  chipTypeId,
  dismissTypeHref,
  entryMode,
  groupIdFromRoute,
  inboxItemFromObservation,
  issueIdAfterLeave,
  labeledTypeIdForComment,
  nextChangeId,
  taxonClickHref,
  thisTypeHref,
  typeRouteAfterRemove,
  typeSelectorLabel,
  unlabeledHref,
} from '../workbench/workbenchMode.ts'
import { useWorkbenchStore } from '../workbench/workbenchStore.ts'

function queryStr(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

const route = useRoute()
const router = useRouter()
const mode = computed(() => entryMode(route.name))
const paramsIssueId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))
const groupId = computed(() => groupIdFromRoute(paramsIssueId.value, queryStr(route.query.type)))
const selector = computed(() => activeSelector(route.name, paramsIssueId.value))

const store = useWorkbenchStore()
const { inbox, taxonomy, issue, missing, error, loading } = storeToRefs(store)
const { loadInbox, openSettings } = store

async function loadIssue() {
  await store.loadIssue(groupId.value)
}

async function loadAll() {
  await store.loadAll(groupId.value)
}

async function invalidate(parts: InvalidateParts, issueId = groupId.value) {
  await store.invalidate(parts, issueId)
}
const notice = ref('')
const labeling = ref(false)
const changeId = ref('')

const lastTypeId = ref('')
watch(groupId, (id) => {
  if (id) { lastTypeId.value = id }
})

const chipTypeIdValue = computed(() =>
  chipTypeId(groupId.value, lastTypeId.value, (id) => Boolean(findNode(taxonomy.value?.forest ?? [], id))),
)

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
  return findNode(taxonomy.value?.forest ?? [], id) ?? undefined
}

const selectedCount = computed(() => typeRow(groupId.value)?.count ?? 0)
const chipTypeName = computed(() => typeRow(chipTypeIdValue.value)?.name ?? issue.value?.name ?? '')
const chipTypeCode = computed(() => typeRow(chipTypeIdValue.value)?.code ?? issue.value?.code ?? '')
const chipTypeCount = computed(() => typeRow(chipTypeIdValue.value)?.count ?? selectedCount.value)
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
  if (!row || !issue.value) { return undefined }
  return inboxItemFromObservation(row, {
    id: issue.value.id,
    code: issue.value.code,
    name: issue.value.name,
    parent_id: issue.value.parent_id,
  })
})

const inspectorItem = computed(() =>
  mode.value === 'observations' ? selectedObservation.value : selectedComment.value,
)

const inspectorView = computed(() => {
  if (mode.value === 'observations') { return 'observation' as const }
  return 'unlabeled' as const
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

const canLabelWithAi = computed(() =>
  Boolean(inbox.value?.llm_provider && inbox.value.pending_code_count),
)

function labelWithAiTitle(): string {
  if (!inbox.value?.llm_provider) { return 'Configure llm.provider and .reviewdistill/.env first' }
  if (!inbox.value.pending_code_count) { return 'No unlabeled comments need suggestions' }
  return 'Ask the LLM to propose issue types for every unlabeled comment'
}

watch(
  [inbox, inspectorItem],
  () => {
    changeId.value = nextChangeId(
      inbox.value?.issues ?? [],
      inspectorItem.value?.issue?.id ?? null,
      changeId.value,
    )
  },
)

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

async function labelWithAi() {
  if (labeling.value) { return }
  labeling.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await postInboxCode()
    if (result.privacy_warning) { notice.value = result.privacy_warning }
    await invalidate({ inbox: true, taxonomy: true })
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    labeling.value = false
  }
}

function commentQueueIds(): string[] {
  if (mode.value === 'observations') {
    return (issue.value?.comments ?? []).map((row) => row.id)
  }
  return queueItems.value.map((item) => item.comment.id)
}

function afterCommentAction(next?: string) {
  if (mode.value === 'observations') {
    selectedObservationId.value = next
    return
  }
  void router.replace({ query: typeQuery(next) })
}

async function act(action: 'accept' | 'verify' | 'drop') {
  const current = inspectorItem.value
  if (!current) { return }
  error.value = ''
  const actedId = current.comment.id
  const idsBefore = commentQueueIds()
  try {
    await postInbox(actedId, action)
    await invalidate({ inbox: true, taxonomy: true, issue: true })
    afterCommentAction(selectedIdAfterAction(idsBefore, actedId, commentQueueIds()))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function change() {
  const current = inspectorItem.value
  if (!current || !changeId.value) { return }
  error.value = ''
  const actedId = current.comment.id
  const idsBefore = commentQueueIds()
  try {
    await changeInbox(actedId, changeId.value)
    await invalidate({ inbox: true, taxonomy: true, issue: true })
    afterCommentAction(selectedIdAfterAction(idsBefore, actedId, commentQueueIds()))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onDrop(payload: DragPayload, target: DropTarget) {
  const labeledTypeId = payload.kind === 'comment'
    ? labeledTypeIdForComment(queueItems.value, payload.id)
    : null
  const source = payload.kind === 'issue'
    ? findNode(taxonomy.value?.forest ?? [], payload.id)
    : null
  const action = dropAction(payload, target, labeledTypeId, source ? descendantIds(source) : [])
  if (action.type === 'ignore' || !allowChangeDrop(mode.value, action.type)) { return }
  error.value = ''
  try {
    if (action.type === 'change') {
      const actedId = action.commentId
      const idsBefore = queueItems.value.map((item) => item.comment.id)
      await changeInbox(actedId, action.issueTypeId)
      await invalidate({ inbox: true, taxonomy: true, issue: true })
      await router.replace({
        query: typeQuery(selectedIdAfterAction(idsBefore, actedId, commentQueueIds())),
      })
      return
    }
    if (action.type === 'merge') {
      await mergeIssues([action.sourceId], action.targetId)
      const next = afterMergeNavigation(
        selector.value,
        action.targetId,
        selectedCommentId.value ?? '',
        groupId.value,
        action.sourceId,
      )
      if (next.replace) { await router.replace(next.href) }
      else { await router.push(next.href) }
      await invalidate({ inbox: true, taxonomy: true, issue: true }, next.issueId)
      return
    }
    if (action.type === 'move') {
      const body = moveBody(taxonomy.value?.forest ?? [], action.issueTypeId, action.targetId, action.placement)
      if (!body) { return }
      await moveIssue(action.issueTypeId, body.parent_id, body.position)
      await invalidate({ taxonomy: true, issue: true })
    }
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onCreateType(parentId: string | null) {
  error.value = ''
  try {
    const created = await createIssue(parentId)
    await invalidate({ taxonomy: true, issue: true })
    await router.push(`/taxonomy/${created.id}`)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onFlattenType(id: string) {
  error.value = ''
  const viewing = groupId.value
  const node = findNode(taxonomy.value?.forest ?? [], id)
  const href = typeRouteAfterRemove(viewing, node ? descendantIds(node) : [])
  try {
    await flattenIssue(id)
    if (href) { await router.replace(href) }
    await invalidate({ taxonomy: true, inbox: true, issue: true }, issueIdAfterLeave(href, viewing))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onRemoveType(id: string) {
  error.value = ''
  const viewing = groupId.value
  const node = findNode(taxonomy.value?.forest ?? [], id)
  const deletedIds = node ? [id, ...descendantIds(node)] : [id]
  const href = typeRouteAfterRemove(viewing, deletedIds)
  try {
    await removeIssue(id)
    if (href) { await router.replace(href) }
    await invalidate({ taxonomy: true, inbox: true, issue: true }, issueIdAfterLeave(href, viewing))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onIssueUpdated() {
  error.value = ''
  await invalidate({ taxonomy: true, issue: true })
}

async function onIssueRemoved() {
  error.value = ''
  lastTypeId.value = ''
  await invalidate({ taxonomy: true })
  await router.replace('/')
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

onMounted(() => {
  void loadAll()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
watch(() => route.name, () => { void loadInbox() })
watch(groupId, () => { void loadIssue() })
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <SelectorsBar
      :selector="selector"
      :unlabeled-count="inbox?.unlabeled_count ?? 0"
      :type-href="thisTypeHref(chipTypeIdValue)"
      :type-label="typeChipLabel"
      :type-title="chipTypeName"
      :unlabeled-href="unlabeledHref(chipTypeIdValue)"
      @dismiss-type="onDismissType"
    />
    <div class="flex min-h-0 flex-1">
      <GroupsPanel
        :list="taxonomy"
        :selected-id="groupId"
        @select="onSelectGroup"
        @drop="onDrop"
        @create="onCreateType"
        @flatten="onFlattenType"
        @remove="onRemoveType"
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
            :has-children="Boolean(findNode(taxonomy?.forest ?? [], groupId)?.children.length)"
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
          :show-label-with-ai="mode === 'unlabeled'"
          :labeling="labeling"
          :can-label-with-ai="canLabelWithAi"
          :label-with-ai-title="labelWithAiTitle()"
          @select="onSelectEntry"
          @update:layout="onCommentsLayout"
          @label-with-ai="labelWithAi"
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
            :forest="taxonomy?.forest ?? []"
            @update:change-id="changeId = $event"
            @accept="act('accept')"
            @change="change"
            @verify="act('verify')"
            @drop="act('drop')"
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
