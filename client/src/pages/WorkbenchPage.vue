<script setup lang="ts">
import type { InboxItemJson } from '../api/client.ts'
import type { DragPayload, DropTarget } from '../workbench/dropAction.ts'
import type { CommentsLayout } from '../workbench/workbenchMode.ts'
import type { InvalidateParts } from '../workbench/workbenchStore.ts'
import { storeToRefs } from 'pinia'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import withProgressBar from 'with-progress-bar'
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
import ProgressBar from '../components/workbench/ProgressBar.vue'
import SelectorsBar from '../components/workbench/SelectorsBar.vue'
import { inboxLocationRows, safeHttpHref } from '../inboxLocation.ts'
import { selectedIdAfterAction } from '../select.ts'
import {
  applyCommentSelectors,
  commentsEmptyCopy,
  mergeCommentPool,
  parseUnlabeledQuery,
  staleCommentQuery,
  typeChipVisible,
  workbenchHref,
} from '../workbench/commentSelectors.ts'
import { splitContextText } from '../workbench/contextParts.ts'
import { dropAction } from '../workbench/dropAction.ts'
import { descendantIds, findNode, moveBody } from '../workbench/taxonomyTree.ts'
import {
  afterMergeNavigation,
  allowChangeDrop,
  groupIdFromRoute,
  issueIdAfterLeave,
  labeledTypeIdForComment,
  typeRouteAfterRemove,
  typeSelectorLabel,
} from '../workbench/workbenchMode.ts'
import { useWorkbenchStore } from '../workbench/workbenchStore.ts'

function queryStr(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

const route = useRoute()
const router = useRouter()
const paramsIssueId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))
const detailsId = computed(() => groupIdFromRoute(paramsIssueId.value))
const groupId = detailsId
const unlabeledOn = computed(() => parseUnlabeledQuery(route.query.unlabeled))
const typeOn = computed(() => typeChipVisible(detailsId.value, route.query.typechip))
const commentIdQuery = computed(() => queryStr(route.query.id))

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

const commentsLayout = ref<CommentsLayout>('one')

function typeRow(id: string) {
  if (!id) { return undefined }
  return findNode(taxonomy.value?.forest ?? [], id) ?? undefined
}

const selectedCount = computed(() => typeRow(groupId.value)?.count ?? 0)
const typeChipLabel = computed(() => {
  const name = typeRow(detailsId.value)?.name ?? issue.value?.name ?? ''
  if (!name) { return '' }
  return typeSelectorLabel(name, typeRow(detailsId.value)?.count ?? selectedCount.value)
})
const typeChipTitle = computed(() => typeRow(detailsId.value)?.name ?? issue.value?.name ?? '')

const pool = computed(() =>
  mergeCommentPool(inbox.value?.working_items ?? [], inbox.value?.items ?? []),
)
const inboxIds = computed(() => new Set((inbox.value?.items ?? []).map((row) => row.comment.id)))
const typeSubtreeIds = computed(() => {
  if (!typeOn.value) { return [] as string[] }
  const node = findNode(taxonomy.value?.forest ?? [], detailsId.value)
  if (!node) { return detailsId.value ? [detailsId.value] : [] }
  return [node.id, ...descendantIds(node)]
})
const matchedItems = computed(() => applyCommentSelectors(pool.value, inboxIds.value, {
  unlabeled: unlabeledOn.value,
  typeSubtreeIds: typeSubtreeIds.value,
}))

const selectedCommentId = computed(() => {
  const id = commentIdQuery.value || undefined
  if (id && matchedItems.value.some((item) => item.comment.id === id)) { return id }
  return matchedItems.value[0]?.comment.id
})

const selectedComment = computed(() =>
  matchedItems.value.find((item) => item.comment.id === selectedCommentId.value),
)

const listSelectedId = computed(() => selectedCommentId.value)

const inspectorItem = computed(() => selectedComment.value)

const inspectorView = computed(() => {
  if (inspectorItem.value?.labeled) { return 'observation' as const }
  return 'unlabeled' as const
})

const commentTotal = computed(() => matchedItems.value.length)

const emptyCopy = computed(() => commentsEmptyCopy({
  unlabeled: unlabeledOn.value,
  typeOn: typeOn.value,
}))

function commentHref(commentId?: string): string {
  return workbenchHref(detailsId.value, {
    unlabeled: unlabeledOn.value,
    typeChipOff: !typeOn.value,
    commentId,
  })
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

const canLabelWithAi = computed(() =>
  Boolean(inbox.value?.llm_provider && inbox.value.pending_code_count),
)

function labelWithAiTitle(): string {
  if (!inbox.value?.llm_provider) { return 'Configure the assistant in Settings first' }
  if (!inbox.value.pending_code_count) { return 'No unlabeled comments need suggestions' }
  return 'Ask the LLM to propose issue types for every unlabeled comment'
}

function selectComment(id: string) {
  void router.replace(commentHref(id))
}

function onSelectGroup(id: string) {
  if (!id) { return }
  void router.push(workbenchHref(id, {
    unlabeled: unlabeledOn.value,
    typeChipOff: false,
  }))
}

function onSelectEntry(id: string) {
  selectComment(id)
}

const runLabelWithAi = withProgressBar(async () => {
  const result = await postInboxCode()
  if (result.privacy_warning) { notice.value = result.privacy_warning }
  await invalidate({ inbox: true, taxonomy: true })
})

async function labelWithAi() {
  if (labeling.value) { return }
  labeling.value = true
  error.value = ''
  notice.value = ''
  try {
    await runLabelWithAi()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    labeling.value = false
  }
}

function commentQueueIds(): string[] {
  return matchedItems.value.map((item) => item.comment.id)
}

function afterCommentAction(next?: string) {
  void router.replace(commentHref(next))
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

async function change(issueTypeId: string) {
  const current = inspectorItem.value
  if (!current || !issueTypeId) { return }
  error.value = ''
  const actedId = current.comment.id
  const idsBefore = commentQueueIds()
  try {
    await changeInbox(actedId, issueTypeId)
    await invalidate({ inbox: true, taxonomy: true, issue: true })
    afterCommentAction(selectedIdAfterAction(idsBefore, actedId, commentQueueIds()))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function onDrop(payload: DragPayload, target: DropTarget) {
  const dragged = payload.kind === 'comment'
    ? pool.value.find((row) => row.comment.id === payload.id)
    : null
  const labeledTypeId = payload.kind === 'comment'
    ? labeledTypeIdForComment(pool.value, payload.id)
    : null
  const source = payload.kind === 'issue'
    ? findNode(taxonomy.value?.forest ?? [], payload.id)
    : null
  const action = dropAction(payload, target, labeledTypeId, source ? descendantIds(source) : [])
  if (action.type === 'ignore' || !allowChangeDrop(Boolean(dragged?.labeled), action.type)) { return }
  error.value = ''
  try {
    if (action.type === 'change') {
      const actedId = action.commentId
      const idsBefore = matchedItems.value.map((item) => item.comment.id)
      await changeInbox(actedId, action.issueTypeId)
      await invalidate({ inbox: true, taxonomy: true, issue: true })
      await router.replace(commentHref(selectedIdAfterAction(idsBefore, actedId, commentQueueIds())))
      return
    }
    if (action.type === 'merge') {
      await mergeIssues([action.sourceId], action.targetId)
      const next = afterMergeNavigation(
        { unlabeled: unlabeledOn.value, detailsId: detailsId.value },
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
    await router.push(workbenchHref(created.id, {
      unlabeled: unlabeledOn.value,
      typeChipOff: false,
    }))
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
  await invalidate({ taxonomy: true })
  await router.replace(workbenchHref('', {
    unlabeled: unlabeledOn.value,
    typeChipOff: false,
  }))
}

function onCommentsLayout(layout: CommentsLayout) {
  commentsLayout.value = layout
}

function onKey(event: KeyboardEvent) {
  const tag = (event.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return }
  if (event.key !== 'j' && event.key !== 'k') { return }
  const ids = matchedItems.value.map((item) => item.comment.id)
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
watch(
  () => [commentIdQuery.value, matchedItems.value.map((item) => item.comment.id)] as const,
  ([queryId, ids]) => {
    if (!staleCommentQuery(queryId, ids)) { return }
    void router.replace(commentHref(ids[0]))
  },
)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <SelectorsBar
      :unlabeled-on="unlabeledOn"
      :dismiss-unlabeled-href="workbenchHref(detailsId, { unlabeled: false, typeChipOff: !typeOn, commentId: selectedCommentId })"
      :toggle-unlabeled-href="workbenchHref(detailsId, { unlabeled: !unlabeledOn, typeChipOff: !typeOn, commentId: selectedCommentId })"
      :type-chip="typeOn && typeChipLabel ? {
        label: typeChipLabel,
        title: typeChipTitle,
        dismissHref: workbenchHref(detailsId, { unlabeled: unlabeledOn, typeChipOff: true, commentId: selectedCommentId }),
      } : null"
    />
    <!-- Issues ~38rem | Comments flex-1. Selectors and Progress stay full-width. -->
    <div class="flex min-h-0 flex-1 gap-2 p-2">
      <div class="flex min-h-0 min-w-0 w-[38rem] max-w-[38rem] shrink overflow-hidden rounded-[var(--ch-radius)] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)]">
        <GroupsPanel
          :list="taxonomy"
          :selected-id="groupId"
          @select="onSelectGroup"
          @drop="onDrop"
          @create="onCreateType"
          @flatten="onFlattenType"
          @remove="onRemoveType"
        />
        <div class="flex min-h-0 min-w-0 flex-1 flex-col">
          <div class="flex h-9 shrink-0 items-center border-b border-[var(--ch-color-border)] px-2">
            <span class="text-xs font-medium">Issue Details</span>
          </div>
          <div class="min-h-0 flex-1 overflow-auto p-3 text-xs leading-5">
            <p v-if="error" class="ch-error-text mb-3">
              {{ error }}
            </p>
            <IssueInspector
              :issue="issue"
              :selected-id="groupId"
              :missing="missing"
              :has-children="Boolean(findNode(taxonomy?.forest ?? [], groupId)?.children.length)"
              @updated="onIssueUpdated"
              @removed="onIssueRemoved"
              @failed="error = $event"
            />
          </div>
        </div>
      </div>
      <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--ch-radius)] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)]">
        <EntriesPanel
          :layout="commentsLayout"
          :items="matchedItems"
          :selected-id="listSelectedId"
          :total-count="commentTotal"
          :loading="loading"
          :empty-copy="emptyCopy"
          :error="error"
          :notice="notice"
          :show-label-with-ai="Boolean(inbox?.pending_code_count)"
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
            :forest="taxonomy?.forest ?? []"
            @accept="act('accept')"
            @assign="change"
            @verify="act('verify')"
            @drop="act('drop')"
            @configure-llm="openSettings"
          />
          <p v-else-if="!loading" class="ch-muted-text">
            {{ emptyCopy }}
          </p>
        </EntriesPanel>
      </div>
    </div>
    <ProgressBar :progress="inbox?.progress ?? null" />
  </div>
</template>
