/** Pointer → sibling before/after, nest inner, or leaf merge chip. */
export type DropPlacement = 'before' | 'inner' | 'after' | 'merge'

export function dropPlacement(args: {
  clientY: number
  clientX?: number
  row: { top: number, height: number }
  mergeRect: { left: number, right: number, top: number, bottom: number } | null
  isLeaf: boolean
}): DropPlacement {
  const { clientY, clientX = 0, row, mergeRect, isLeaf } = args
  if (
    isLeaf
    && mergeRect
    && clientX > mergeRect.left
    && clientX < mergeRect.right
    && clientY > mergeRect.top
    && clientY < mergeRect.bottom
  ) {
    return 'merge'
  }
  const rel = row.height === 0 ? 0.5 : (clientY - row.top) / row.height
  if (rel < 0.25) { return 'before' }
  if (rel > 0.75) { return 'after' }
  return 'inner'
}
