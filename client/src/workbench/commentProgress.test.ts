import { describe, expect, it } from 'vitest'
import { EMPTY_PROGRESS, progressHeadlineLabel, progressParts, progressPartTitle } from './commentProgress'

describe('commentProgress', () => {
  it('shows unlabeled, verified, and dropped', () => {
    expect(progressParts({
      working_set: 42,
      unlabeled: 8,
      labeled: 34,
      unreviewed: 9,
      verified: 40,
      dropped: 2,
    }).map((row) => `${row.key} ${row.n}`)).toEqual([
      'unlabeled 8',
      'verified 40',
      'dropped 2',
    ])
  })

  it('starts empty at zero', () => {
    expect(EMPTY_PROGRESS.working_set).toBe(0)
    expect(progressParts(EMPTY_PROGRESS).every((row) => row.n === 0)).toBe(true)
    expect(EMPTY_PROGRESS).not.toHaveProperty('absent')
  })

  it('names the headline to distill', () => {
    expect(progressHeadlineLabel()).toBe('to distill')
  })

  it('explains each count on its own', () => {
    expect(progressPartTitle('working_set')).toBe(
      'The number of comments to distill. They are not dropped, and they are still in the manuscript or already verified.',
    )
    expect(progressPartTitle('unlabeled')).toBe(
      'The number of comments to distill that have no issue type. The Unlabeled chip is the inbox queue, not this count.',
    )
    expect(progressPartTitle('verified')).toBe(
      'The number of comments that are quality-assured. Does not confirm the issue type.',
    )
    expect(progressPartTitle('dropped')).toBe(
      'The number of comments not to distill (too local, or a bad extract). History is kept.',
    )
  })
})
