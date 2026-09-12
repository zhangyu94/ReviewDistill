import { describe, expect, it } from 'vitest'
import {
  acceptTooltip,
  changeTooltip,
  dropTooltip,
  verifyTooltip,
} from './inboxTooltips.ts'

describe('inboxTooltips', () => {
  it('explains Accept when an AI suggestion exists', () => {
    expect(acceptTooltip(true)).toMatch(/AI suggestion/i)
    expect(acceptTooltip(true)).toMatch(/issue type/i)
  })

  it('explains why Accept is disabled without an AI suggestion', () => {
    expect(acceptTooltip(false)).toMatch(/no AI suggestion/i)
    expect(acceptTooltip(false)).toMatch(/Label with AI/i)
  })

  it('explains Change as assigning the selected issue type', () => {
    expect(changeTooltip(true)).toMatch(/dropdown/i)
    expect(changeTooltip(false)).toMatch(/no issue types/i)
  })

  it('explains Verify and Drop', () => {
    expect(verifyTooltip()).toMatch(/quality/i)
    expect(dropTooltip()).toMatch(/distill/i)
    expect(dropTooltip()).toMatch(/history/i)
  })
})
