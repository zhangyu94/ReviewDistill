import type { DropPlacement } from './dropPlacement.ts'

export const DRAG_MIME = 'application/x-reviewdistill'

export type DragPayload
  = | { kind: 'comment', id: string }
    | { kind: 'issue', id: string }

export interface DropTarget {
  kind: 'issue'
  id: string
  placement: DropPlacement
  isLeaf: boolean
}

export type DropAction
  = | { type: 'change', commentId: string, issueTypeId: string }
    | { type: 'merge', sourceId: string, targetId: string }
    | { type: 'move', issueTypeId: string, targetId: string, placement: 'before' | 'inner' | 'after' }
    | { type: 'ignore' }

/** Map HTML5 drag payload + drop target to Change / merge / move. No extra DnD library. */
export function dropAction(
  payload: DragPayload,
  target: DropTarget,
  labeledTypeId: string | null = null,
  sourceDescendantIds: string[] = [],
): DropAction {
  if (payload.kind === 'comment' && target.kind === 'issue') {
    if (!target.isLeaf) { return { type: 'ignore' } }
    if (labeledTypeId && target.id === labeledTypeId) { return { type: 'ignore' } }
    return { type: 'change', commentId: payload.id, issueTypeId: target.id }
  }
  if (payload.kind === 'issue' && target.kind === 'issue') {
    if (payload.id === target.id || sourceDescendantIds.includes(target.id)) {
      return { type: 'ignore' }
    }
    if (target.placement === 'merge') {
      if (!target.isLeaf) { return { type: 'ignore' } }
      return { type: 'merge', sourceId: payload.id, targetId: target.id }
    }
    return { type: 'move', issueTypeId: payload.id, targetId: target.id, placement: target.placement }
  }
  return { type: 'ignore' }
}

export function parseDragPayload(raw: string): DragPayload | null {
  try {
    const data = JSON.parse(raw) as { kind?: unknown, id?: unknown }
    if ((data.kind === 'comment' || data.kind === 'issue') && typeof data.id === 'string' && data.id) { return { kind: data.kind, id: data.id } }
  }
  catch {
    return null
  }
  return null
}

export function serializeDragPayload(payload: DragPayload): string {
  return JSON.stringify(payload)
}

export function allowDropHighlight(args: {
  dragKind: 'comment' | 'issue' | ''
  isLeaf: boolean
  isSelf: boolean
  isDescendant: boolean
}): boolean {
  if (args.isSelf || args.isDescendant) { return false }
  if (args.dragKind !== 'issue' && !args.isLeaf) { return false }
  return true
}

export function showSiblingDropGuide(
  dragKind: 'comment' | 'issue' | '',
  placement: DropPlacement,
): boolean {
  return dragKind === 'issue' && (placement === 'before' || placement === 'after')
}
