import { describe, expect, it } from 'vitest'
import { nextSelectedId, selectedIdAfterAction } from './select.ts'

describe('nextSelectedId', () => {
  it('selects the following id', () => {
    expect(nextSelectedId(['a', 'b', 'c'], 'a')).toBe('b')
  })
  it('selects the previous id when acting on the last', () => {
    expect(nextSelectedId(['a', 'b', 'c'], 'c')).toBe('b')
  })
  it('returns undefined for a single-item list', () => {
    expect(nextSelectedId(['a'], 'a')).toBeUndefined()
  })
  it('falls back to first when the acted id is missing', () => {
    expect(nextSelectedId(['a', 'b'], 'z')).toBe('a')
  })
  it('returns undefined for an empty list', () => {
    expect(nextSelectedId([], 'a')).toBeUndefined()
  })
})

describe('selectedIdAfterAction', () => {
  it('keeps the acted id when it is still in the list', () => {
    expect(selectedIdAfterAction(['a', 'b', 'c'], 'b', ['a', 'b', 'c'])).toBe('b')
  })
  it('advances when the acted id left the list', () => {
    expect(selectedIdAfterAction(['a', 'b', 'c'], 'a', ['b', 'c'])).toBe('b')
  })
  it('selects the previous id when the last item left', () => {
    expect(selectedIdAfterAction(['a', 'b', 'c'], 'c', ['a', 'b'])).toBe('b')
  })
  it('returns undefined when the list is empty after the action', () => {
    expect(selectedIdAfterAction(['a'], 'a', [])).toBeUndefined()
  })
})
