import type { InboxItemJson, TaxonomyCommentJson } from '../api/client.ts'
import type { DropAction } from './dropAction.ts'

export type EntryMode = 'uncoded' | 'disappeared' | 'observations'
export type InspectorKind = 'comment' | 'issue'

export function entryMode(routeName: string | symbol | undefined | null): EntryMode {
  if (routeName === 'disappeared')
    return 'disappeared'
  if (routeName === 'taxonomy' || routeName === 'issue')
    return 'observations'
  return 'uncoded'
}

export function inspectorKind(routeName: string | symbol | undefined | null): InspectorKind {
  if (routeName === 'taxonomy' || routeName === 'issue')
    return 'issue'
  return 'comment'
}

export type SelectorId = 'uncoded' | 'disappeared' | 'type'

export function activeSelector(
  routeName: string | symbol | undefined | null,
  selectedIssueId: string,
): SelectorId {
  if (routeName === 'disappeared')
    return 'disappeared'
  if (routeName === 'issue' && selectedIssueId)
    return 'type'
  return 'uncoded'
}

export function groupIdFromRoute(paramsId: string, queryType: string): string {
  return paramsId || queryType
}

export function uncodedHref(typeId: string): string {
  return typeId ? `/?type=${encodeURIComponent(typeId)}` : '/'
}

export function disappearedHref(typeId: string): string {
  return typeId ? `/inbox/disappeared?type=${encodeURIComponent(typeId)}` : '/inbox/disappeared'
}

export function thisTypeHref(typeId: string): string {
  return typeId ? `/taxonomy/${typeId}` : ''
}

export function taxonClickHref(typeId: string): string {
  return thisTypeHref(typeId)
}

export function dismissTypeHref(selector: SelectorId): string {
  if (selector === 'disappeared')
    return '/inbox/disappeared'
  return '/'
}

export function typeSelectorLabel(code: string, count: number): string {
  return `${code} (${count})`
}

export type CommentsLayout = 'list' | 'one'

export function inboxItemFromObservation(row: TaxonomyCommentJson): InboxItemJson {
  const { project_name, permalink, ...comment } = row
  return {
    comment,
    project_name,
    permalink,
    guess: null,
    coding: null,
  }
}

export function allowChangeDrop(mode: EntryMode, actionType: DropAction['type']): boolean {
  return actionType !== 'change' || mode === 'uncoded'
}
