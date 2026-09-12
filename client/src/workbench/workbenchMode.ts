import type { InboxItemJson, IssueOption, TaxonomyCommentJson } from '../api/client.ts'
import type { DropAction } from './dropAction.ts'

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

export type SelectorId = 'unlabeled' | 'type'

export function activeSelector(
  routeName: string | symbol | undefined | null,
  selectedIssueId: string,
): SelectorId {
  if (routeName === 'issue' && selectedIssueId) { return 'type' }
  return 'unlabeled'
}

export function groupIdFromRoute(paramsId: string, queryType: string): string {
  return paramsId || queryType
}

export function unlabeledHref(typeId: string): string {
  return typeId ? `/?type=${encodeURIComponent(typeId)}` : '/'
}

export function thisTypeHref(typeId: string): string {
  return typeId ? `/taxonomy/${typeId}` : ''
}

export function taxonClickHref(typeId: string): string {
  return thisTypeHref(typeId)
}

export function dismissTypeHref(_selector: SelectorId): string {
  return '/'
}

export function typeSelectorLabel(code: string, count: number): string {
  return `${code} (${count})`
}

export type CommentsLayout = 'list' | 'one'

export function inboxItemFromObservation(row: TaxonomyCommentJson, issue: IssueOption): InboxItemJson {
  const { project_name, permalink, ...comment } = row
  return {
    comment,
    project_name,
    permalink,
    guess: null,
    in_manuscript: comment.status === 'active',
    labeled: true,
    issue,
    coding: null,
  }
}

export function showAssignType(view: 'unlabeled' | 'observation', labeled: boolean): boolean {
  return view === 'unlabeled' && !labeled
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

export function labeledTypeIdForComment(items: InboxItemJson[], commentId: string): string | null {
  return items.find((item) => item.comment.id === commentId)?.issue?.id ?? null
}

export function changeIssueOptions(issues: IssueOption[], currentTypeId: string | null): IssueOption[] {
  if (!currentTypeId) { return issues }
  return issues.filter((issue) => issue.id !== currentTypeId)
}

export function nextChangeId(
  issues: IssueOption[],
  currentTypeId: string | null,
  selectedId: string,
): string {
  const options = changeIssueOptions(issues, currentTypeId)
  if (options.some((issue) => issue.id === selectedId)) { return selectedId }
  return options[0]?.id ?? ''
}

export function allowChangeDrop(mode: EntryMode, actionType: DropAction['type']): boolean {
  return actionType !== 'change' || mode === 'unlabeled'
}
