import { describe, expect, it } from 'vitest'
import { commentsTotalLabel } from './commentsHeader.ts'

describe('commentsTotalLabel', () => {
  it('is the to-distill queue size when no chips', () => {
    expect(commentsTotalLabel(12, {}, 12)).toBe('12 to distill')
    expect(commentsTotalLabel(0, {}, 0)).toBe('0 to distill')
  })

  it('keeps to distill beside the match count when chips AND', () => {
    expect(commentsTotalLabel(2, { unlabeled: true, labelOn: false }, 3)).toBe('2 matching · 3 to distill')
    expect(commentsTotalLabel(1, { unlabeled: false, labelOn: true }, 3)).toBe('1 matching · 3 to distill')
    expect(commentsTotalLabel(0, { unlabeled: true, labelOn: true }, 3)).toBe('0 matching · 3 to distill')
  })
})
