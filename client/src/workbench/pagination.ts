export type PagerItem = number | 'ellipsis'

const PAGER_COUNT = 7

export function pageForId(ids: string[], id: string | undefined): number {
  if (!id) { return 1 }
  const i = ids.indexOf(id)
  return i < 0 ? 1 : i + 1
}

export function idForPage(ids: string[], page: number): string | undefined {
  return ids[page - 1]
}

/** Same pager window as Element Plus (`pager-count` 7): first, last, current neighborhood, ellipses. */
export function pagerItems(currentPage: number, pageCount: number): PagerItem[] {
  if (pageCount <= 0) { return [] }
  if (pageCount === 1) { return [1] }

  const half = (PAGER_COUNT - 1) / 2
  let showPrevMore = false
  let showNextMore = false
  if (pageCount > PAGER_COUNT) {
    if (currentPage > PAGER_COUNT - half) { showPrevMore = true }
    if (currentPage < pageCount - half) { showNextMore = true }
  }

  const middle: number[] = []
  if (showPrevMore && !showNextMore) {
    const startPage = pageCount - (PAGER_COUNT - 2)
    for (let i = startPage; i < pageCount; i++) { middle.push(i) }
  }
  else if (!showPrevMore && showNextMore) {
    for (let i = 2; i < PAGER_COUNT; i++) { middle.push(i) }
  }
  else if (showPrevMore && showNextMore) {
    const offset = Math.floor(PAGER_COUNT / 2) - 1
    for (let i = currentPage - offset; i <= currentPage + offset; i++) { middle.push(i) }
  }
  else {
    for (let i = 2; i < pageCount; i++) { middle.push(i) }
  }

  const items: PagerItem[] = [1]
  if (showPrevMore) { items.push('ellipsis') }
  items.push(...middle)
  if (showNextMore) { items.push('ellipsis') }
  items.push(pageCount)
  return items
}

export function previousCommentTitle(currentPage: number): string {
  return currentPage <= 1 ? 'Already on the first comment' : 'Show the previous comment'
}

export function nextCommentTitle(currentPage: number, pageCount: number): string {
  return currentPage >= pageCount ? 'Already on the last comment' : 'Show the next comment'
}

export function commentPageTitle(page: number, pageCount: number, currentPage: number): string {
  if (page === currentPage) { return `Comment ${page} of ${pageCount} (showing)` }
  return `Show comment ${page} of ${pageCount}`
}
