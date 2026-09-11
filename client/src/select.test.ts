import { describe, expect, it } from 'vitest'
import { nextSelectedId } from './select.ts'

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
