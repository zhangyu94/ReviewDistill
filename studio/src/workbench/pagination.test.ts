import { describe, expect, it } from 'vitest'
import {
  commentPageTitle,
  idForPage,
  nextCommentTitle,
  pageForId,
  pagerItems,
  previousCommentTitle,
} from './pagination.ts'

describe('pageForId', () => {
  it('is the 1-based index of the selected id', () => {
    expect(pageForId(['a', 'b', 'c'], 'b')).toBe(2)
  })

  it('falls back to page 1 when the id is missing', () => {
    expect(pageForId(['a', 'b'], 'z')).toBe(1)
    expect(pageForId(['a'], undefined)).toBe(1)
  })
})

describe('idForPage', () => {
  it('returns the id at the 1-based page', () => {
    expect(idForPage(['a', 'b', 'c'], 3)).toBe('c')
  })
})

describe('pagerItems', () => {
  it('lists every page when there are few', () => {
    expect(pagerItems(2, 3)).toEqual([1, 2, 3])
  })

  it('ellipsizes a long range like Element Plus pager', () => {
    expect(pagerItems(1, 12)).toEqual([1, 2, 3, 4, 5, 6, 'ellipsis', 12])
    expect(pagerItems(6, 12)).toEqual([1, 'ellipsis', 4, 5, 6, 7, 8, 'ellipsis', 12])
    expect(pagerItems(12, 12)).toEqual([1, 'ellipsis', 7, 8, 9, 10, 11, 12])
  })
})

describe('comment page titles', () => {
  it('explains previous and next', () => {
    expect(previousCommentTitle(1)).toMatch(/first comment/i)
    expect(previousCommentTitle(2)).toMatch(/previous comment/i)
    expect(nextCommentTitle(3, 3)).toMatch(/last comment/i)
    expect(nextCommentTitle(2, 3)).toMatch(/next comment/i)
  })

  it('explains jumping to a numbered comment', () => {
    expect(commentPageTitle(2, 3, 1)).toBe('Show comment 2 of 3')
    expect(commentPageTitle(1, 3, 1)).toMatch(/showing/i)
  })
})
