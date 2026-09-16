// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { shouldIgnoreCommentHotkey } from './commentHotkey.ts'

function el(tag: string, attrs: Record<string, string> = {}, parent?: HTMLElement): HTMLElement {
  const node = document.createElement(tag)
  for (const [key, value] of Object.entries(attrs)) { node.setAttribute(key, value) }
  parent?.append(node)
  return node
}

describe('shouldIgnoreCommentHotkey', () => {
  it('ignores native fields', () => {
    expect(shouldIgnoreCommentHotkey(el('input'))).toBe(true)
    expect(shouldIgnoreCommentHotkey(el('textarea'))).toBe(true)
    expect(shouldIgnoreCommentHotkey(el('select'))).toBe(true)
  })

  it('ignores combobox, listbox, and menu targets', () => {
    const combo = el('button', { role: 'combobox' })
    expect(shouldIgnoreCommentHotkey(el('span', {}, combo))).toBe(true)
    expect(shouldIgnoreCommentHotkey(el('div', { role: 'listbox' }))).toBe(true)
    expect(shouldIgnoreCommentHotkey(el('div', { role: 'menu' }))).toBe(true)
  })

  it('allows j and k from a comment row', () => {
    expect(shouldIgnoreCommentHotkey(el('button'))).toBe(false)
    expect(shouldIgnoreCommentHotkey(null)).toBe(false)
  })
})
