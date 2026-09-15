import { describe, expect, it } from 'vitest'
import {
  afterRecycleHref,
  afterSplitHref,
  canHeaderRecycle,
  canHeaderRecycleFromState,
  canHeaderSplit,
  canHeaderSplitFromState,
  canLeafSplit,
} from './splitControls.ts'

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
    expect(afterSplitHref('abc')).toBe('/labels/abc?unlabeled=1&labelchip=0')
    expect(afterSplitHref(null)).toBe('/?unlabeled=1')
  })
})

describe('header recycle', () => {
  it('enables only on a nonempty forest with enough unlabeled comments', () => {
    expect(canHeaderRecycle({ forestEmpty: false, unlabeledCount: 2 })).toBe(true)
    expect(canHeaderRecycle({ forestEmpty: true, unlabeledCount: 2 })).toBe(false)
    expect(canHeaderRecycle({ forestEmpty: false, unlabeledCount: 1 })).toBe(false)
    expect(canHeaderRecycle({ forestEmpty: false, unlabeledCount: 2, llmConfigured: false })).toBe(true)
  })

  it('keeps recycle off until taxonomy has loaded', () => {
    expect(canHeaderRecycleFromState({
      forest: undefined,
      unlabeledWorkingCount: 2,
    })).toBe(false)
    expect(canHeaderRecycleFromState({
      forest: [],
      unlabeledWorkingCount: 2,
    })).toBe(false)
    expect(canHeaderRecycleFromState({
      forest: [{ id: 't1' }],
      unlabeledWorkingCount: 2,
    })).toBe(true)
  })

  it('routes to the new label with Unlabeled off and the label chip on', () => {
    expect(afterRecycleHref('abc')).toBe('/labels/abc')
  })
})
