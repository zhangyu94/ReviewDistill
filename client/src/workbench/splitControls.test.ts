import { describe, expect, it } from 'vitest'
import { afterSplitHref, canHeaderSplit, canHeaderSplitFromState, canLeafSplit } from './splitControls.ts'

describe('splitControls', () => {
  it('enables the header fork only on an empty forest with enough unlabeled comments and an LLM', () => {
    expect(canHeaderSplit({ forestEmpty: true, unlabeledCount: 2, llmConfigured: true })).toBe(true)
    expect(canHeaderSplit({ forestEmpty: false, unlabeledCount: 2, llmConfigured: true })).toBe(false)
    expect(canHeaderSplit({ forestEmpty: true, unlabeledCount: 1, llmConfigured: true })).toBe(false)
    expect(canHeaderSplit({ forestEmpty: true, unlabeledCount: 2, llmConfigured: false })).toBe(false)
  })

  it('keeps the header fork off until taxonomy has loaded', () => {
    expect(canHeaderSplitFromState({
      forest: undefined,
      unlabeledWorkingCount: 2,
      llmConfigured: true,
    })).toBe(false)
    expect(canHeaderSplitFromState({
      forest: [],
      unlabeledWorkingCount: 2,
      llmConfigured: true,
    })).toBe(true)
    expect(canHeaderSplitFromState({
      forest: [{ id: 't1' }],
      unlabeledWorkingCount: 2,
      llmConfigured: true,
    })).toBe(false)
  })

  it('counts working-set unlabeled comments, not the unlabeled queue', () => {
    expect(canHeaderSplitFromState({
      forest: [],
      unlabeledWorkingCount: 0,
      llmConfigured: true,
    })).toBe(false)
    expect(canHeaderSplitFromState({
      forest: [],
      unlabeledWorkingCount: 2,
      llmConfigured: true,
    })).toBe(true)
  })

  it('shows the row fork only on a leaf with at least two labeled comments and an LLM', () => {
    expect(canLeafSplit({ isLeaf: true, count: 2, llmConfigured: true })).toBe(true)
    expect(canLeafSplit({ isLeaf: true, count: 2, llmConfigured: false })).toBe(false)
    expect(canLeafSplit({ isLeaf: true, count: 1, llmConfigured: true })).toBe(false)
    expect(canLeafSplit({ isLeaf: false, count: 5, llmConfigured: true })).toBe(false)
  })

  it('routes to unlabeled with the type chip off after split', () => {
    expect(afterSplitHref('abc')).toBe('/taxonomy/abc?unlabeled=1&typechip=0')
    expect(afterSplitHref(null)).toBe('/?unlabeled=1')
  })
})
