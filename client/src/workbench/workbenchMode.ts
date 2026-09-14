import type { InboxItemJson, IssueOption, TaxonomyCommentJson } from '../api/client.ts'
import type { DropAction } from './dropAction.ts'
import { workbenchHref } from './commentSelectors.ts'

export type EntryMode = 'unlabeled' | 'observations'
export type InspectorKind = 'comment' | 'issue'

export function entryMode(routeName: string | symbol | undefined | null): EntryMode {
  if (routeName === 'issue') { return 'observations' }
  return 'unlabeled'
}

export function inspectorKind(routeName: string | symbol | undefined | null): InspectorKind {
  if (routeName === 'issue') { return 'issue' }
  return 'comment'
}

export function groupIdFromRoute(paramsId: string, _queryType?: string): string {
  return paramsId
}

export function thisTypeHref(typeId: string): string {
  return typeId ? `/taxonomy/${typeId}` : ''
}

export function taxonClickHref(typeId: string): string {
  return thisTypeHref(typeId)
}

export function typeSelectorLabel(name: string, count: number): string {
  return `${name} (${count})`
}

export function unlabeledSelectorLabel(): string {
  return 'Unlabeled'
}

export type CommentsLayout = 'list' | 'one'

export function inboxItemFromObservation(row: TaxonomyCommentJson, issue: IssueOption): InboxItemJson {
  const { project_name, permalink, issue: accepted, ...comment } = row
  return {
    comment,
    project_name,
    permalink,
    guess: null,
    in_manuscript: comment.status === 'active',
    labeled: true,
    issue: accepted ?? issue,
    coding: null,
    in_working_set: comment.status === 'active',
  }
}

export function showAssignType(labeled: boolean): boolean {
  return !labeled
}

export function clearIssueBeforeLoad(currentId: string, requestedId: string): boolean {
  return !requestedId || currentId !== requestedId
}

export function shouldApplyIssueLoad(gen: number, latestGen: number): boolean {
  return gen === latestGen
}

export function issueLoadErrorView(status: number | null): 'missing' | 'error' {
  return status === 404 ? 'missing' : 'error'
}

export function typeRouteAfterDeactivate(groupId: string, deactivatedId: string): string | null {
  if (groupId && groupId === deactivatedId) { return '/' }
  return null
}

export function typeRouteAfterRemove(groupId: string, deletedIds: string[]): string | null {
  if (groupId && deletedIds.includes(groupId)) { return '/' }
  return null
}

export function issueIdAfterLeave(href: string | null, viewing: string): string {
  return href ? '' : viewing
}

export function afterMergeNavigation(
  chips: { unlabeled: boolean, detailsId: string },
  targetId: string,
  commentId = '',
  viewing = '',
  sourceId = '',
): { href: string, issueId: string, replace: boolean } {
  const replace = !chips.detailsId || viewing === sourceId || viewing === targetId
  const href = workbenchHref(targetId, {
    unlabeled: chips.unlabeled,
    typeChipOff: false,
    commentId: commentId || undefined,
  })
  return { href, issueId: targetId, replace }
}

export function labeledTypeIdForComment(items: InboxItemJson[], commentId: string): string | null {
  return items.find((item) => item.comment.id === commentId)?.issue?.id ?? null
}

export function changeIssueOptions(issues: IssueOption[]): IssueOption[] {
  return issues
}

export function allowChangeDrop(labeled: boolean, actionType: DropAction['type']): boolean {
  return actionType !== 'change' || !labeled
}
