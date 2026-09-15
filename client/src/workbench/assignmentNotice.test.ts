import { describe, expect, it } from 'vitest'
import { assignmentNoticeText, workbenchSnackbar } from './assignmentNotice'

describe('assignmentNoticeText', () => {
  it('is empty when the count is missing or zero', () => {
    expect(assignmentNoticeText(0)).toBe('')
    expect(assignmentNoticeText(-1)).toBe('')
    expect(assignmentNoticeText(Number.NaN)).toBe('')
    expect(assignmentNoticeText(undefined)).toBe('')
  })

  it('points a single labeled comment at Label Taxonomy', () => {
    expect(assignmentNoticeText(1)).toBe(
      '1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.',
    )
  })

  it('points a batch at Label Taxonomy without listing labels', () => {
    expect(assignmentNoticeText(11)).toBe(
      '11 comments were labeled. They appear in Label Taxonomy. Change any that are wrong.',
    )
  })
})

describe('workbenchSnackbar', () => {
  it('prefers the error over an assignment notice', () => {
    expect(workbenchSnackbar(
      'LLM request failed (deepseek): Connection timed out after 60.0 seconds.',
      '1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.',
    )).toEqual({
      text: 'LLM request failed (deepseek): Connection timed out after 60.0 seconds.',
      kind: 'error',
    })
  })

  it('shows the assignment notice when there is no error', () => {
    expect(workbenchSnackbar(
      '',
      '11 comments were labeled. They appear in Label Taxonomy. Change any that are wrong.',
    )).toEqual({
      text: '11 comments were labeled. They appear in Label Taxonomy. Change any that are wrong.',
      kind: 'info',
    })
  })
})
