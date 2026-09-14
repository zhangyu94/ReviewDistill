import { describe, expect, it } from 'vitest'
import { commentsTotalLabel } from './commentsHeader.ts'

describe('commentsTotalLabel', () => {
  it('is the queue size only', () => {
    expect(commentsTotalLabel(12)).toBe('12 total')
    expect(commentsTotalLabel(0)).toBe('0 total')
    expect(commentsTotalLabel(12)).not.toMatch(/selected/)
  })
})
