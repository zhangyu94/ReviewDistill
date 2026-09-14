import { describe, expect, it } from 'vitest'
import { progressParts } from './commentProgress'

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
})
