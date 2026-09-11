import { describe, expect, it } from 'vitest'
import { DRAG_MIME, dropAction, parseDragPayload, serializeDragPayload } from './dropAction.ts'

describe('dropAction', () => {
  it('assigns a comment dropped on an issue type', () => {
    expect(
      dropAction({ kind: 'comment', id: 'c1' }, { kind: 'issue', id: 't1' }),
    ).toEqual({ type: 'change', commentId: 'c1', issueTypeId: 't1' })
  })

  it('ignores a comment dropped on the type it already has', () => {
    expect(
      dropAction({ kind: 'comment', id: 'c1' }, { kind: 'issue', id: 't1' }, 't1'),
    ).toEqual({ type: 'ignore' })
  })

  it('merges an issue dropped on a different issue', () => {
    expect(
      dropAction({ kind: 'issue', id: 'src' }, { kind: 'issue', id: 'dst' }),
    ).toEqual({ type: 'merge', sourceId: 'src', targetId: 'dst' })
  })

  it('ignores an issue dropped on itself', () => {
    expect(
      dropAction({ kind: 'issue', id: 't1' }, { kind: 'issue', id: 't1' }),
    ).toEqual({ type: 'ignore' })
  })

  it('moves an issue dropped on a category', () => {
    expect(
      dropAction({ kind: 'issue', id: 't1' }, { kind: 'category', name: 'Clarity' }),
    ).toEqual({ type: 'move', issueTypeId: 't1', category: 'Clarity' })
  })

  it('still merges when dropping A on B even if they share a category', () => {
    expect(
      dropAction({ kind: 'issue', id: 'a' }, { kind: 'issue', id: 'b' }),
    ).toEqual({ type: 'merge', sourceId: 'a', targetId: 'b' })
  })
})

describe('parseDragPayload', () => {
  it('reads the ReviewDistill MIME payload', () => {
    expect(parseDragPayload('{"kind":"comment","id":"c1"}')).toEqual({
      kind: 'comment',
      id: 'c1',
    })
  })

  it('returns null for garbage', () => {
    expect(parseDragPayload('not-json')).toBeNull()
    expect(parseDragPayload('{"kind":"nope"}')).toBeNull()
  })

  it('exports a stable MIME type', () => {
    expect(DRAG_MIME).toBe('application/x-reviewdistill')
  })

  it('round-trips an issue payload for the groups panel', () => {
    const raw = serializeDragPayload({ kind: 'issue', id: 't1' })
    expect(parseDragPayload(raw)).toEqual({ kind: 'issue', id: 't1' })
  })
})
