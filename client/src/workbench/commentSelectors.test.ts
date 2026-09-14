import type { InboxItemJson } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import {
  applyCommentSelectors,
  commentsEmptyCopy,
  mergeCommentPool,
  parseUnlabeledQuery,
  staleCommentQuery,
  typeChipOffFromQuery,
  typeChipVisible,
  workbenchHref,
} from './commentSelectors'

function item(partial: Partial<InboxItemJson> & { id: string }): InboxItemJson {
  const { id, ...rest } = partial
  return {
    comment: {
      id,
      project_id: 'p',
      source_type: 'latex_command',
      source_command: 'myremark',
      file_path: 'main.tex',
      line_number: 1,
      raw_text: 'x',
      context_text: '',
      section: null,
      git_commit: null,
      git_url: null,
      fingerprint: 'fp',
      status: 'active',
      quality: 'unreviewed',
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      ...rest.comment,
    },
    project_name: 'paper',
    permalink: null,
    guess: null,
    in_manuscript: true,
    labeled: false,
    issue: null,
    coding: null,
    in_working_set: true,
    local_file: false,
    ...rest,
  }
}

describe('query flags', () => {
  it('reads unlabeled=1', () => {
    expect(parseUnlabeledQuery('1')).toBe(true)
    expect(parseUnlabeledQuery(undefined)).toBe(false)
    expect(parseUnlabeledQuery('0')).toBe(false)
  })

  it('shows the type chip on a details page unless typechip=0', () => {
    expect(typeChipVisible('t1', undefined)).toBe(true)
    expect(typeChipVisible('t1', '0')).toBe(false)
    expect(typeChipVisible('', undefined)).toBe(false)
    expect(typeChipOffFromQuery('0')).toBe(true)
  })
})

describe('workbenchHref', () => {
  it('builds ITL URLs', () => {
    expect(workbenchHref('', { unlabeled: false, typeChipOff: false })).toBe('/')
    expect(workbenchHref('', { unlabeled: true, typeChipOff: false })).toBe('/?unlabeled=1')
    expect(workbenchHref('t1', { unlabeled: false, typeChipOff: false })).toBe('/taxonomy/t1')
    expect(workbenchHref('t1', { unlabeled: true, typeChipOff: false })).toBe('/taxonomy/t1?unlabeled=1')
    expect(workbenchHref('t1', { unlabeled: false, typeChipOff: true })).toBe('/taxonomy/t1?typechip=0')
    expect(workbenchHref('t1', { unlabeled: true, typeChipOff: true })).toBe(
      '/taxonomy/t1?unlabeled=1&typechip=0',
    )
    expect(workbenchHref('t1', { unlabeled: true, typeChipOff: false, commentId: 'c1' })).toBe(
      '/taxonomy/t1?unlabeled=1&id=c1',
    )
  })

  it('ignores typechip=0 when there is no details id', () => {
    expect(workbenchHref('', { unlabeled: false, typeChipOff: true })).toBe('/')
  })
})

describe('staleCommentQuery', () => {
  it('is stale when the query id is not in the match', () => {
    expect(staleCommentQuery('gone', ['a', 'b'])).toBe(true)
    expect(staleCommentQuery('a', ['a', 'b'])).toBe(false)
    expect(staleCommentQuery('', ['a'])).toBe(false)
    expect(staleCommentQuery('a', [])).toBe(true)
  })
})

describe('applyCommentSelectors', () => {
  const unlabeled = item({ id: 'u', labeled: false, in_working_set: true })
  const labeled = item({
    id: 'l',
    labeled: true,
    in_working_set: true,
    issue: { id: 'child', name: 'Child', parent_id: 't1' },
  })
  const absentInbox = item({
    id: 'a',
    labeled: false,
    in_working_set: false,
    in_manuscript: false,
  })
  const inboxIds = new Set(['u', 'a'])
  const pool = [unlabeled, labeled, absentInbox]

  it('with no chips keeps comments to distill', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: false, typeSubtreeIds: [] }).map((row) => row.comment.id)).toEqual(['u', 'l'])
  })

  it('unlabeled keeps the inbox queue', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: true, typeSubtreeIds: [] }).map((row) => row.comment.id)).toEqual(['u', 'a'])
  })

  it('type keeps subtree labeled comments to distill', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: false, typeSubtreeIds: ['t1', 'child'] }).map((row) => row.comment.id)).toEqual(['l'])
  })

  it('type excludes labeled comments that are not to distill', () => {
    const labeledAbsent = item({
      id: 'gone',
      labeled: true,
      in_working_set: false,
      in_manuscript: false,
      issue: { id: 'child', name: 'Child', parent_id: 't1' },
    })
    expect(
      applyCommentSelectors(
        [...pool, labeledAbsent],
        new Set([...inboxIds, 'gone']),
        { unlabeled: false, typeSubtreeIds: ['t1', 'child'] },
      ).map((row) => row.comment.id),
    ).toEqual(['l'])
  })

  it('and Unlabeled with a type', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: true, typeSubtreeIds: ['t1', 'child'] })).toEqual([])
  })
})

describe('mergeCommentPool', () => {
  it('unions by comment id, inbox row last so coding wins', () => {
    const working = item({ id: 'u', coding: null })
    const inbox = item({
      id: 'u',
      coding: {
        id: 'c',
        status: 'proposed',
        issue_type_id: null,
        proposed_issue_name: 'n',
        confidence: null,
        rationale: null,
        kind: 'new',
      },
    })
    expect(mergeCommentPool([working], [inbox])[0].coding?.id).toBe('c')
  })
})

describe('commentsEmptyCopy', () => {
  it('names the empty AND', () => {
    expect(commentsEmptyCopy({ unlabeled: true, typeOn: true })).toBe('No comments match these selectors.')
    expect(commentsEmptyCopy({ unlabeled: true, typeOn: false })).toBe('No unlabeled observations.')
    expect(commentsEmptyCopy({ unlabeled: false, typeOn: true })).toBe('No labeled comments on this type yet.')
    expect(commentsEmptyCopy({ unlabeled: false, typeOn: false })).toBe('No comments to distill.')
  })
})
