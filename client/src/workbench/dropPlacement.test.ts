import { describe, expect, it } from 'vitest'
import { dropPlacement } from './dropPlacement.ts'

const row = { top: 100, height: 40 }

describe('dropPlacement', () => {
  it('before on the top quarter', () => {
    expect(dropPlacement({ clientY: 105, row, mergeRect: null, isLeaf: true })).toBe('before')
  })

  it('after on the bottom quarter', () => {
    expect(dropPlacement({ clientY: 135, row, mergeRect: null, isLeaf: true })).toBe('after')
  })

  it('inner in the middle', () => {
    expect(dropPlacement({ clientY: 120, row, mergeRect: null, isLeaf: false })).toBe('inner')
  })

  it('merge when pointer is in the chip', () => {
    expect(dropPlacement({
      clientY: 120,
      clientX: 200,
      row,
      mergeRect: { left: 190, right: 240, top: 110, bottom: 130 },
      isLeaf: true,
    })).toBe('merge')
  })

  it('inner not merge when not a leaf', () => {
    expect(dropPlacement({
      clientY: 120,
      clientX: 200,
      row,
      mergeRect: { left: 190, right: 240, top: 110, bottom: 130 },
      isLeaf: false,
    })).toBe('inner')
  })
})
