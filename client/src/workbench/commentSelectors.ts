import type { InboxItemJson } from '../api/client.ts'

/** URL chips for Comments. Present chips AND. No chips = comments to distill. */
export interface CommentSelectorChips {
  unlabeled: boolean
  typeSubtreeIds: string[]
}

export function parseUnlabeledQuery(value: unknown): boolean {
  return value === '1'
}

export function typeChipOffFromQuery(value: unknown): boolean {
  return value === '0'
}

export function typeChipVisible(detailsId: string, typechipQuery: unknown): boolean {
  return Boolean(detailsId) && !typeChipOffFromQuery(typechipQuery)
}

export function workbenchHref(
  detailsId: string,
  opts: { unlabeled: boolean, typeChipOff: boolean, commentId?: string },
): string {
  // Issue Details is the path id. unlabeled=1 and typechip=0 encode the bar.
  const query = new URLSearchParams()
  if (opts.unlabeled) { query.set('unlabeled', '1') }
  if (detailsId && opts.typeChipOff) { query.set('typechip', '0') }
  if (opts.commentId) { query.set('id', opts.commentId) }
  const path = detailsId ? `/taxonomy/${encodeURIComponent(detailsId)}` : '/'
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
  const typeOn = chips.typeSubtreeIds.length > 0
  const typeSet = new Set(chips.typeSubtreeIds)
  return pool.filter((row) => {
    if (!chips.unlabeled && !typeOn) { return row.in_working_set }
    if (chips.unlabeled && !inboxIds.has(row.comment.id)) { return false }
    if (typeOn) {
      // Subtree membership: one accepted type per comment, not ITL ancestor names.
      const issueId = row.issue?.id
      if (!row.in_working_set || !row.labeled || !issueId || !typeSet.has(issueId)) { return false }
    }
    return true
  })
}

export function commentsEmptyCopy(chips: { unlabeled: boolean, typeOn: boolean }): string {
  if (chips.unlabeled && chips.typeOn) { return 'No comments match these selectors.' }
  if (chips.unlabeled) { return 'No unlabeled observations.' }
  if (chips.typeOn) { return 'No labeled comments on this type yet.' }
  return 'No comments to distill.'
}
