import { describe, expect, it } from 'vitest'
import { leftTheManuscriptLabel, leftTheManuscriptTitle } from './manuscriptPresence.ts'

describe('left the manuscript chip', () => {
  it('locks the badge copy', () => {
    expect(leftTheManuscriptLabel()).toBe('Left the manuscript')
    expect(leftTheManuscriptTitle()).toBe('This remark is no longer in the .tex file.')
  })
})
