import type { InboxItemJson, LabelOption, TaxonomyCommentJson } from '../api/client.ts'
import type { DropAction } from './dropAction.ts'
import { workbenchHref } from './commentSelectors.ts'

export type EntryMode = 'unlabeled' | 'observations'
export type InspectorKind = 'comment' | 'label'
export type CommentsLayout = 'list' | 'tree' | 'one'

export function entryMode(routeName: string | symbol | undefined | null): EntryMode {
  if (routeName === 'label') { return 'observations' }
  return 'unlabeled'
}

export function inspectorKind(routeName: string | symbol | undefined | null): InspectorKind {
  if (routeName === 'label') { return 'label' }
  return 'comment'
}

export function inboxItemFromObservation(row: TaxonomyCommentJson, label: LabelOption): InboxItemJson {
  const { project_name, permalink, label: accepted, ...comment } = row
  return {
    comment,
    project_name,
    permalink,
    guess: null,
    in_manuscript: comment.status === 'active',
    labeled: true,
    label: accepted ?? label,
    assignment: null,
    in_working_set: comment.status === 'active',
    local_file: false,
  }
}

export function showAssignLabel(labeled: boolean): boolean {
  return !labeled
}

export function clearLabelBeforeLoad(currentId: string, requestedId: string): boolean {
  return !requestedId || currentId !== requestedId
}

export function shouldApplyLabelLoad(gen: number, latestGen: number): boolean {
  return gen === latestGen
}

export function labelLoadErrorView(status: number | null): 'missing' | 'error' {
  return status === 404 ? 'missing' : 'error'
}

export function labelRouteAfterRemove(labelId: string, deletedIds: string[]): string | null {
  if (labelId && deletedIds.includes(labelId)) { return '/' }
  return null
}

export function labelIdAfterLeave(href: string | null, viewing: string): string {
  return href ? '' : viewing
}

export function afterHomeChange(): { href: string, labelId: string } {
  return { href: '/', labelId: '' }
}

export function homeSaveFollowUpOrder(): readonly ['reload', 'llm'] {
  return ['reload', 'llm']
}

export function selectGroupHref(id: string, unlabeled: boolean): string {
  return workbenchHref(id, { unlabeled, labelChipOff: unlabeled })
}

export function afterLabelTreeChangeParts() {
  return { labels: true, label: true, inbox: true } as const
}

export function afterMergeNavigation(
  chips: { unlabeled: boolean, detailsId: string },
  targetId: string,
  commentId = '',
  viewing = '',
  sourceId = '',
): { href: string, labelId: string, replace: boolean } {
  const replace = !chips.detailsId || viewing === sourceId || viewing === targetId
  const href = workbenchHref(targetId, {
    unlabeled: chips.unlabeled,
    labelChipOff: chips.unlabeled,
    commentId: commentId || undefined,
  })
  return { href, labelId: targetId, replace }
}

export function labeledLabelIdForComment(items: InboxItemJson[], commentId: string): string | null {
  return items.find((item) => item.comment.id === commentId)?.label?.id ?? null
}

export function allowChangeDrop(labeled: boolean, actionType: DropAction['type']): boolean {
  return actionType !== 'change' || !labeled
}
