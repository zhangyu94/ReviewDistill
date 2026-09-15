import { describe, expect, it } from 'vitest'
import { allowDropHighlight, dropAction, parseDragPayload, serializeDragPayload, showSiblingDropGuide } from './dropAction.ts'

describe('dropAction', () => {
  it('assigns a comment dropped on a leaf', () => {
    expect(
      dropAction({ kind: 'comment', id: 'c1' }, { kind: 'label', id: 't1', placement: 'inner', isLeaf: true }),
    ).toEqual({ type: 'change', commentId: 'c1', labelId: 't1' })
  })

  it('ignores a comment dropped on a parent', () => {
    expect(
      dropAction({ kind: 'comment', id: 'c1' }, { kind: 'label', id: 't1', placement: 'inner', isLeaf: false }),
    ).toEqual({ type: 'ignore' })
  })

  it('ignores a comment dropped on the type it already has', () => {
    expect(
      dropAction({ kind: 'comment', id: 'c1' }, { kind: 'label', id: 't1', placement: 'inner', isLeaf: true }, 't1'),
    ).toEqual({ type: 'ignore' })
  })

  it('merges only on the merge placement of a leaf', () => {
    expect(
      dropAction({ kind: 'label', id: 'src' }, { kind: 'label', id: 'dst', placement: 'merge', isLeaf: true }),
    ).toEqual({ type: 'merge', sourceId: 'src', targetId: 'dst' })
  })

  it('ignores merge on a parent', () => {
    expect(
      dropAction({ kind: 'label', id: 'src' }, { kind: 'label', id: 'dst', placement: 'merge', isLeaf: false }),
    ).toEqual({ type: 'ignore' })
  })

  it('nests when dropping inner on another label', () => {
    expect(
      dropAction({ kind: 'label', id: 'src' }, { kind: 'label', id: 'dst', placement: 'inner', isLeaf: false }),
    ).toEqual({ type: 'move', labelId: 'src', targetId: 'dst', placement: 'inner' })
  })

  it('ignores a label dropped on itself', () => {
    expect(
      dropAction({ kind: 'label', id: 't1' }, { kind: 'label', id: 't1', placement: 'inner', isLeaf: true }),
    ).toEqual({ type: 'ignore' })
  })

  it('ignores merge onto a descendant', () => {
    expect(
      dropAction(
        { kind: 'label', id: 'src' },
        { kind: 'label', id: 'kid', placement: 'merge', isLeaf: true },
        null,
        ['kid'],
      ),
    ).toEqual({ type: 'ignore' })
  })

  it('ignores move onto a descendant', () => {
    expect(
      dropAction(
        { kind: 'label', id: 'src' },
        { kind: 'label', id: 'kid', placement: 'inner', isLeaf: true },
        null,
        ['kid'],
      ),
    ).toEqual({ type: 'ignore' })
  })
})

describe('allowDropHighlight', () => {
  it('hides parent highlight while dragging a comment', () => {
    expect(allowDropHighlight({ dragKind: '', isLeaf: false, isSelf: false, isDescendant: false })).toBe(false)
    expect(allowDropHighlight({ dragKind: '', isLeaf: true, isSelf: false, isDescendant: false })).toBe(true)
  })

  it('keeps parent highlight while dragging a label', () => {
    expect(allowDropHighlight({ dragKind: 'label', isLeaf: false, isSelf: false, isDescendant: false })).toBe(true)
    expect(allowDropHighlight({ dragKind: 'label', isLeaf: false, isSelf: true, isDescendant: false })).toBe(false)
    expect(allowDropHighlight({ dragKind: 'label', isLeaf: true, isSelf: false, isDescendant: true })).toBe(false)
  })
})

describe('showSiblingDropGuide', () => {
  it('shows before/after bars only while dragging a type', () => {
    expect(showSiblingDropGuide('label', 'before')).toBe(true)
    expect(showSiblingDropGuide('label', 'after')).toBe(true)
    expect(showSiblingDropGuide('label', 'inner')).toBe(false)
    expect(showSiblingDropGuide('comment', 'before')).toBe(false)
    expect(showSiblingDropGuide('comment', 'after')).toBe(false)
    expect(showSiblingDropGuide('', 'before')).toBe(false)
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

  it('round-trips a label payload for the labels panel', () => {
    const raw = serializeDragPayload({ kind: 'label', id: 't1' })
    expect(parseDragPayload(raw)).toEqual({ kind: 'label', id: 't1' })
  })
})
