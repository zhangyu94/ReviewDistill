import { describe, expect, it } from 'vitest'
import {
  acceptTooltip,
  changeTooltip,
  keepTooltip,
  rejectTooltip,
  retractTooltip,
} from './inboxTooltips.ts'

describe('inboxTooltips', () => {
  it('explains Accept when an AI suggestion exists', () => {
    expect(acceptTooltip(true)).toMatch(/AI suggestion/i)
    expect(acceptTooltip(true)).toMatch(/issue type/i)
  })

  it('explains why Accept is disabled without an AI suggestion', () => {
    expect(acceptTooltip(false)).toMatch(/no AI suggestion/i)
    expect(acceptTooltip(false)).toMatch(/Get AI suggestions/i)
  })

  it('explains Reject as leaving the comment unassigned', () => {
    expect(rejectTooltip()).toMatch(/not assign/i)
    expect(rejectTooltip()).toMatch(/Uncoded/i)
  })

  it('explains Change as assigning the selected issue type', () => {
    expect(changeTooltip(true)).toMatch(/dropdown/i)
    expect(changeTooltip(false)).toMatch(/no issue types/i)
  })

  it('explains Keep and Retract', () => {
    expect(keepTooltip()).toMatch(/working dataset/i)
    expect(retractTooltip()).toMatch(/working dataset/i)
    expect(retractTooltip()).toMatch(/history/i)
  })
})
