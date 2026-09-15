import type { InboxItemJson } from '../api/client.ts'

/** URL chips for Comments. Present chips AND. No chips = comments to distill. */
export interface CommentSelectorChips {
  unlabeled: boolean
  labelSubtreeIds: string[]
}

export function parseUnlabeledQuery(value: unknown): boolean {
  return value === '1'
}

export function labelChipOffFromQuery(value: unknown): boolean {
  return value === '0'
}

export function labelChipVisible(detailsId: string, labelchipQuery: unknown): boolean {
  return Boolean(detailsId) && !labelChipOffFromQuery(labelchipQuery)
}

export function workbenchHref(
  detailsId: string,
  opts: { unlabeled: boolean, labelChipOff: boolean, commentId?: string },
): string {
  // Label Details is the path id. unlabeled=1 and labelchip=0 encode the bar.
  const query = new URLSearchParams()
  if (opts.unlabeled) { query.set('unlabeled', '1') }
  if (detailsId && opts.labelChipOff) { query.set('labelchip', '0') }
  if (opts.commentId) { query.set('id', opts.commentId) }
  const path = detailsId ? `/labels/${encodeURIComponent(detailsId)}` : '/'
  const search = query.toString()
  return search ? `${path}?${search}` : path
}

export function staleCommentQuery(queryId: string, matchedIds: readonly string[]): boolean {
  return Boolean(queryId) && !matchedIds.includes(queryId)
}

export function mergeCommentPool(
  workingItems: InboxItemJson[],
  inboxItems: InboxItemJson[],
): InboxItemJson[] {
  const byId = new Map<string, InboxItemJson>()
  for (const row of workingItems) { byId.set(row.comment.id, row) }
  for (const row of inboxItems) { byId.set(row.comment.id, row) }
  return [...byId.values()]
}

export function applyCommentSelectors(
  pool: InboxItemJson[],
  inboxIds: ReadonlySet<string>,
  chips: CommentSelectorChips,
): InboxItemJson[] {
  const labelOn = chips.labelSubtreeIds.length > 0
  const labelSet = new Set(chips.labelSubtreeIds)
  return pool.filter((row) => {
    if (!chips.unlabeled && !labelOn) { return row.in_working_set }
    if (chips.unlabeled && !inboxIds.has(row.comment.id)) { return false }
    if (labelOn) {
      const labelId = row.label?.id
      if (!row.in_working_set || !row.labeled || !labelId || !labelSet.has(labelId)) { return false }
    }
    return true
  })
}

export function commentsEmptyCopy(chips: { unlabeled: boolean, labelOn: boolean }): string {
  if (chips.unlabeled && chips.labelOn) { return 'No comments match these selectors.' }
  if (chips.unlabeled) { return 'No unlabeled observations.' }
  if (chips.labelOn) { return 'No labeled comments on this label yet.' }
  return 'No comments to distill.'
}
