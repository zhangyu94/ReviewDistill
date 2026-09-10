export const DRAG_MIME = 'application/x-reviewdistill'

export type DragPayload =
  | { kind: 'comment'; id: string }
  | { kind: 'issue'; id: string }

export type DropTarget =
  | { kind: 'issue'; id: string }
  | { kind: 'category'; name: string }

export type DropAction =
  | { type: 'change'; commentId: string; issueTypeId: string }
  | { type: 'merge'; sourceId: string; targetId: string }
  | { type: 'move'; issueTypeId: string; category: string }
  | { type: 'ignore' }

/** Map HTML5 drag payload + drop target to Change / merge / move. No extra DnD library. */
export function dropAction(payload: DragPayload, target: DropTarget): DropAction {
  if (payload.kind === 'comment' && target.kind === 'issue')
    return { type: 'change', commentId: payload.id, issueTypeId: target.id }
  if (payload.kind === 'issue' && target.kind === 'issue') {
    if (payload.id === target.id)
      return { type: 'ignore' }
    return { type: 'merge', sourceId: payload.id, targetId: target.id }
  }
  if (payload.kind === 'issue' && target.kind === 'category')
    return { type: 'move', issueTypeId: payload.id, category: target.name }
  return { type: 'ignore' }
}

export function parseDragPayload(raw: string): DragPayload | null {
  try {
    const data = JSON.parse(raw) as { kind?: unknown; id?: unknown }
    if ((data.kind === 'comment' || data.kind === 'issue') && typeof data.id === 'string' && data.id)
      return { kind: data.kind, id: data.id }
  }
  catch {
    return null
  }
  return null
}

export function serializeDragPayload(payload: DragPayload): string {
  return JSON.stringify(payload)
}
