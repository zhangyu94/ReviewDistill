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
  createLabel,
  flattenLabel,
  mergeLabels,
  moveLabel,
  postInbox,
  postInboxCode,
  recycleUngrouped,
  removeLabel,
  revealInboxFile,
  splitForest,
  splitLabel,
} from '../api/client.ts'
import AssignmentSnackbar from '../components/workbench/AssignmentSnackbar.vue'
import CommentInspector from '../components/workbench/CommentInspector.vue'
import EntriesPanel from '../components/workbench/EntriesPanel.vue'
import LabelInspector from '../components/workbench/LabelInspector.vue'
import LabelsPanel from '../components/workbench/LabelsPanel.vue'
import ProgressBar from '../components/workbench/ProgressBar.vue'
import SelectorsBar from '../components/workbench/SelectorsBar.vue'
import { inboxLocationRows, safeHttpHref } from '../inboxLocation.ts'
import { selectedIdAfterAction } from '../select.ts'
import { assignmentNoticeText, workbenchSnackbar } from '../workbench/assignmentNotice.ts'
import {
  applyCommentSelectors,
  commentsEmptyCopy,
  labelChipVisible,
  mergeCommentPool,
  parseUnlabeledQuery,
  staleCommentQuery,
  workbenchHref,
} from '../workbench/commentSelectors.ts'
import { dropAction } from '../workbench/dropAction.ts'
import {
  afterRecycleHref,
  canHeaderRecycleFromState,
  canHeaderSplitFromState,
} from '../workbench/splitControls.ts'
import { descendantIds, findNode, moveBody } from '../workbench/taxonomyTree.ts'
import {
  afterLabelTreeChangeParts,
  afterMergeNavigation,
  allowChangeDrop,
  labeledLabelIdForComment,
  labelIdAfterLeave,
  labelRouteAfterRemove,
  selectGroupHref,
} from '../workbench/workbenchMode.ts'
import { useWorkbenchStore } from '../workbench/workbenchStore.ts'

function queryStr(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

const route = useRoute()
const router = useRouter()
const paramsLabelId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))
const detailsId = paramsLabelId
const labelId = detailsId
const unlabeledOn = computed(() => parseUnlabeledQuery(route.query.unlabeled))
const labelOn = computed(() => labelChipVisible(detailsId.value, route.query.labelchip))
const commentIdQuery = computed(() => queryStr(route.query.id))

const store = useWorkbenchStore()
const { inbox, labels, label, missing, error, loading, labelLoading, assignmentNotice, errorNotice } = storeToRefs(store)
const { loadInbox, openSettings } = store
const snackbar = computed(() => workbenchSnackbar(errorNotice.value, assignmentNotice.value))

function beginAction() {
  store.clearErrorNotice()
}

function showActionError(err: unknown) {
  store.setErrorNotice(err instanceof Error ? err.message : String(err))
}

function onSnackbarClose() {
  store.clearErrorNotice()
  store.clearAssignmentNotice()
}

async function loadLabel() {
  await store.loadLabel(labelId.value)
}

async function loadAll() {
  await store.loadAll(labelId.value)
}

async function invalidate(parts: InvalidateParts, id = labelId.value) {
  await store.invalidate(parts, id)
}
const labeling = ref(false)
const revealing = ref(false)

const commentsLayout = ref<CommentsLayout>('one')

function labelRow(id: string) {
  if (!id) { return undefined }
  return findNode(labels.value?.forest ?? [], id) ?? undefined
}

const selectedCount = computed(() => labelRow(labelId.value)?.count ?? 0)
const labelChipLabel = computed(() => {
  const name = labelRow(detailsId.value)?.name ?? label.value?.name ?? ''
  if (!name) { return '' }
  return `${name} (${labelRow(detailsId.value)?.count ?? selectedCount.value})`
})
const labelChipTitle = computed(() => labelRow(detailsId.value)?.name ?? label.value?.name ?? '')

const pool = computed(() =>
  mergeCommentPool(inbox.value?.working_items ?? [], inbox.value?.items ?? []),
)
const inboxIds = computed(() => new Set((inbox.value?.items ?? []).map((row) => row.comment.id)))
const labelSubtreeIds = computed(() => {
  if (!labelOn.value) { return [] as string[] }
  const node = findNode(labels.value?.forest ?? [], detailsId.value)
  if (!node) { return detailsId.value ? [detailsId.value] : [] }
  return [node.id, ...descendantIds(node)]
})
const matchedItems = computed(() => applyCommentSelectors(pool.value, inboxIds.value, {
  unlabeled: unlabeledOn.value,
  labelSubtreeIds: labelSubtreeIds.value,
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
const toDistillCount = computed(() => inbox.value?.progress.working_set ?? 0)

const emptyCopy = computed(() => commentsEmptyCopy({
  unlabeled: unlabeledOn.value,
  labelOn: labelOn.value,
  loaded: inbox.value != null,
}))

function commentHref(commentId?: string): string {
  return workbenchHref(detailsId.value, {
    unlabeled: unlabeledOn.value,
    labelChipOff: !labelOn.value,
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
    localFile: item.local_file,
  })
})

const canLabelWithAi = computed(() =>
  Boolean(inbox.value?.llm_provider && inbox.value.pending_code_count),
)

const headerSplitEnabled = computed(() => canHeaderSplitFromState({
  forest: labels.value?.forest,
  unlabeledWorkingCount: inbox.value?.progress.unlabeled ?? 0,
  llmConfigured: Boolean(inbox.value?.llm_provider),
}))

const headerRecycleEnabled = computed(() => canHeaderRecycleFromState({
  forest: labels.value?.forest,
  unlabeledWorkingCount: inbox.value?.progress.unlabeled ?? 0,
}))

function labelWithAiTitle(): string {
  if (!inbox.value?.llm_provider) { return 'Configure the assistant in Settings first' }
  if (!inbox.value.pending_code_count) { return 'No unlabeled comments need suggestions' }
  return 'Ask the LLM to propose a label assignment for every unlabeled comment'
}

function selectComment(id: string) {
  void router.replace(commentHref(id))
}

function onSelectGroup(id: string) {
  if (!id) { return }
  void router.push(selectGroupHref(id, unlabeledOn.value))
}

function onSelectEntry(id: string) {
  selectComment(id)
}

const runLabelWithAi = withProgressBar(async () => {
  const result = await postInboxCode()
  store.setAssignmentNotice(assignmentNoticeText(result.coded))
  await invalidate({ inbox: true, labels: true })
})

async function labelWithAi() {
  if (labeling.value) { return }
  labeling.value = true
  beginAction()
  try {
    await runLabelWithAi()
  }
  catch (err) {
    showActionError(err)
  }
  finally {
    labeling.value = false
  }
}

const runSplit = withProgressBar(async (id: string | null) => {
  const result = id ? await splitLabel(id) : await splitForest()
  store.setAssignmentNotice(assignmentNoticeText(result.labeled))
  await invalidate({ inbox: true, labels: true, label: true })
})

async function onSplitLabel(id: string | null) {
  if (labeling.value) { return }
  labeling.value = true
  beginAction()
  try {
    await runSplit(id)
  }
  catch (err) {
    showActionError(err)
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

async function act(action: 'accept' | 'verify' | 'delete') {
  const current = inspectorItem.value
  if (!current) { return }
  beginAction()
  const actedId = current.comment.id
  const idsBefore = commentQueueIds()
  try {
    await postInbox(actedId, action)
    await invalidate({ inbox: true, labels: true, label: true })
    if (action === 'verify') {
      afterCommentAction(actedId)
    }
    else {
      afterCommentAction(selectedIdAfterAction(idsBefore, actedId, commentQueueIds()))
    }
  }
  catch (err) {
    showActionError(err)
  }
}

async function revealFile() {
  const current = inspectorItem.value
  if (!current || revealing.value) { return }
  revealing.value = true
  beginAction()
  try {
    await revealInboxFile(current.comment.id)
  }
  catch (err) {
    showActionError(err)
  }
  finally {
    revealing.value = false
  }
}

async function change(nextLabelId: string) {
  const current = inspectorItem.value
  if (!current || !nextLabelId) { return }
  beginAction()
  const actedId = current.comment.id
  const idsBefore = commentQueueIds()
  try {
    await changeInbox(actedId, nextLabelId)
    await invalidate({ inbox: true, labels: true, label: true })
    afterCommentAction(selectedIdAfterAction(idsBefore, actedId, commentQueueIds()))
  }
  catch (err) {
    showActionError(err)
  }
}

async function onDrop(payload: DragPayload, target: DropTarget) {
  const dragged = payload.kind === 'comment'
    ? pool.value.find((row) => row.comment.id === payload.id)
    : null
  const labeledTypeId = payload.kind === 'comment'
    ? labeledLabelIdForComment(pool.value, payload.id)
    : null
  const source = payload.kind === 'label'
    ? findNode(labels.value?.forest ?? [], payload.id)
    : null
  const action = dropAction(payload, target, labeledTypeId, source ? descendantIds(source) : [])
  if (action.type === 'ignore' || !allowChangeDrop(Boolean(dragged?.labeled), action.type)) { return }
  beginAction()
  try {
    if (action.type === 'change') {
      const actedId = action.commentId
      const idsBefore = matchedItems.value.map((item) => item.comment.id)
      await changeInbox(actedId, action.labelId)
      await invalidate({ inbox: true, labels: true, label: true })
      await router.replace(commentHref(selectedIdAfterAction(idsBefore, actedId, commentQueueIds())))
      return
    }
    if (action.type === 'merge') {
      await mergeLabels([action.sourceId], action.targetId)
      const next = afterMergeNavigation(
        { unlabeled: unlabeledOn.value, detailsId: detailsId.value },
        action.targetId,
        selectedCommentId.value ?? '',
        labelId.value,
        action.sourceId,
      )
      if (next.replace) { await router.replace(next.href) }
      else { await router.push(next.href) }
      await invalidate({ inbox: true, labels: true, label: true }, next.labelId)
      return
    }
    if (action.type === 'move') {
      const body = moveBody(labels.value?.forest ?? [], action.labelId, action.targetId, action.placement)
      if (!body) { return }
      await moveLabel(action.labelId, body.parent_id, body.position)
      await invalidate(afterLabelTreeChangeParts())
    }
  }
  catch (err) {
    showActionError(err)
  }
}

async function onCreateLabel(parentId: string | null) {
  beginAction()
  try {
    const created = await createLabel(parentId)
    await invalidate(afterLabelTreeChangeParts())
    await router.push(selectGroupHref(created.id, unlabeledOn.value))
  }
  catch (err) {
    showActionError(err)
  }
}

async function onRecycleUngrouped() {
  beginAction()
  try {
    const created = await recycleUngrouped()
    await invalidate(afterLabelTreeChangeParts())
    await router.push(afterRecycleHref(created.id))
  }
  catch (err) {
    showActionError(err)
  }
}

async function onFlattenLabel(id: string) {
  beginAction()
  const viewing = labelId.value
  const node = findNode(labels.value?.forest ?? [], id)
  const href = labelRouteAfterRemove(viewing, node ? descendantIds(node) : [])
  try {
    await flattenLabel(id)
    if (href) { await router.replace(href) }
    await invalidate({ labels: true, inbox: true, label: true }, labelIdAfterLeave(href, viewing))
  }
  catch (err) {
    showActionError(err)
  }
}

async function onRemoveLabel(id: string) {
  beginAction()
  const viewing = labelId.value
  const node = findNode(labels.value?.forest ?? [], id)
  const deletedIds = node ? [id, ...descendantIds(node)] : [id]
  const href = labelRouteAfterRemove(viewing, deletedIds)
  try {
    await removeLabel(id)
    if (href) { await router.replace(href) }
    await invalidate({ labels: true, inbox: true, label: true }, labelIdAfterLeave(href, viewing))
  }
  catch (err) {
    showActionError(err)
  }
}

async function onLabelUpdated() {
  beginAction()
  try {
    await invalidate({ labels: true, label: true })
  }
  catch (err) {
    showActionError(err)
  }
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
watch(() => route.name, () => { void loadInbox().catch(showActionError) })
watch(labelId, () => { void loadLabel() })
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
      :dismiss-unlabeled-href="workbenchHref(detailsId, { unlabeled: false, labelChipOff: !labelOn, commentId: selectedCommentId })"
      :toggle-unlabeled-href="workbenchHref(detailsId, { unlabeled: !unlabeledOn, labelChipOff: !labelOn, commentId: selectedCommentId })"
      :label-chip="labelOn && labelChipLabel ? {
        label: labelChipLabel,
        title: labelChipTitle,
        dismissHref: workbenchHref(detailsId, { unlabeled: unlabeledOn, labelChipOff: true, commentId: selectedCommentId }),
      } : null"
    />
    <!-- Label Taxonomy over Label Details | Comments share the row equally. Selectors and Progress stay full-width. -->
    <div class="flex min-h-0 flex-1 gap-2 p-2">
      <div class="ch-workbench-card flex-col">
        <LabelsPanel
          :list="labels"
          :selected-id="labelId"
          :header-split-enabled="headerSplitEnabled"
          :header-recycle-enabled="headerRecycleEnabled"
          :llm-configured="Boolean(inbox?.llm_provider)"
          :splitting="labeling"
          @select="onSelectGroup"
          @drop="onDrop"
          @create="onCreateLabel"
          @recycle="onRecycleUngrouped"
          @flatten="onFlattenLabel"
          @remove="onRemoveLabel"
          @split="onSplitLabel"
        />
        <LabelInspector
          :label="label"
          :selected-id="labelId"
          :missing="missing"
          :error="error"
          :loading="labelLoading"
          @updated="onLabelUpdated"
        />
      </div>
      <div class="ch-workbench-card flex-col">
        <EntriesPanel
          :layout="commentsLayout"
          :items="matchedItems"
          :selected-id="listSelectedId"
          :forest="labels?.forest ?? []"
          :total-count="commentTotal"
          :to-distill-count="toDistillCount"
          :unlabeled="unlabeledOn"
          :label-on="labelOn"
          :loading="loading"
          :empty-copy="emptyCopy"
          :show-label-with-ai="Boolean(inbox?.pending_code_count)"
          :labeling="labeling"
          :can-label-with-ai="canLabelWithAi"
          :label-with-ai-title="labelWithAiTitle()"
          @select="onSelectEntry"
          @update:layout="onCommentsLayout"
          @label-with-ai="labelWithAi"
        >
          <CommentInspector
            v-if="inspectorItem"
            :view="inspectorView"
            :selected="inspectorItem"
            :data="inbox"
            error=""
            :location-rows="locationRows"
            :forest="labels?.forest ?? []"
            @accept="act('accept')"
            @assign="change"
            @verify="act('verify')"
            @delete="act('delete')"
            @reveal="revealFile"
            @configure-llm="openSettings"
          />
          <p v-else-if="!loading && emptyCopy" class="ch-muted-text p-2">
            {{ emptyCopy }}
          </p>
        </EntriesPanel>
      </div>
    </div>
    <AssignmentSnackbar
      :text="snackbar.text"
      :kind="snackbar.kind"
      @close="onSnackbarClose"
    />
    <ProgressBar :progress="inbox?.progress ?? null" />
  </div>
</template>
