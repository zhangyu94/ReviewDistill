import type { InboxItemJson } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import {
  applyCommentSelectors,
  commentsEmptyCopy,
  labelChipOffFromQuery,
  labelChipVisible,
  mergeCommentPool,
  parseUnlabeledQuery,
  staleCommentQuery,
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
      context_offset: null,
      section: null,
      git_commit: null,
      git_url: null,
      status: 'active',
      verified: false,
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      ...rest.comment,
    },
    project_name: 'paper',
    permalink: null,
    guess: null,
    in_manuscript: true,
    labeled: false,
    label: null,
    assignment: null,
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

  it('shows the type chip on a details page unless labelchip=0', () => {
    expect(labelChipVisible('t1', undefined)).toBe(true)
    expect(labelChipVisible('t1', '0')).toBe(false)
    expect(labelChipVisible('', undefined)).toBe(false)
    expect(labelChipOffFromQuery('0')).toBe(true)
  })
})

describe('workbenchHref', () => {
  it('builds ITL URLs', () => {
    expect(workbenchHref('', { unlabeled: false, labelChipOff: false })).toBe('/')
    expect(workbenchHref('', { unlabeled: true, labelChipOff: false })).toBe('/?unlabeled=1')
    expect(workbenchHref('t1', { unlabeled: false, labelChipOff: false })).toBe('/labels/t1')
    expect(workbenchHref('t1', { unlabeled: true, labelChipOff: false })).toBe('/labels/t1?unlabeled=1')
    expect(workbenchHref('t1', { unlabeled: false, labelChipOff: true })).toBe('/labels/t1?labelchip=0')
    expect(workbenchHref('t1', { unlabeled: true, labelChipOff: true })).toBe(
      '/labels/t1?unlabeled=1&labelchip=0',
    )
    expect(workbenchHref('t1', { unlabeled: true, labelChipOff: false, commentId: 'c1' })).toBe(
      '/labels/t1?unlabeled=1&id=c1',
    )
  })

  it('ignores labelchip=0 when there is no details id', () => {
    expect(workbenchHref('', { unlabeled: false, labelChipOff: true })).toBe('/')
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
    label: { id: 'child', name: 'Child', parent_id: 't1' },
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
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: false, labelSubtreeIds: [] }).map((row) => row.comment.id)).toEqual(['u', 'l'])
  })

  it('unlabeled keeps the inbox queue', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: true, labelSubtreeIds: [] }).map((row) => row.comment.id)).toEqual(['u', 'a'])
  })

  it('type keeps subtree labeled comments to distill', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: false, labelSubtreeIds: ['t1', 'child'] }).map((row) => row.comment.id)).toEqual(['l'])
  })

  it('type excludes labeled comments that are not to distill', () => {
    const labeledAbsent = item({
      id: 'gone',
      labeled: true,
      in_working_set: false,
      in_manuscript: false,
      label: { id: 'child', name: 'Child', parent_id: 't1' },
    })
    expect(
      applyCommentSelectors(
        [...pool, labeledAbsent],
        new Set([...inboxIds, 'gone']),
        { unlabeled: false, labelSubtreeIds: ['t1', 'child'] },
      ).map((row) => row.comment.id),
    ).toEqual(['l'])
  })

  it('and Unlabeled with a type', () => {
    expect(applyCommentSelectors(pool, inboxIds, { unlabeled: true, labelSubtreeIds: ['t1', 'child'] })).toEqual([])
  })
})

describe('mergeCommentPool', () => {
  it('unions by comment id, inbox row last so assignment wins', () => {
    const working = item({ id: 'u', assignment: null })
    const inbox = item({
      id: 'u',
      assignment: {
        id: 'c',
        status: 'proposed',
        label_id: null,
        proposed_label_name: 'n',
        confidence: null,
        rationale: null,
        kind: 'new',
      },
    })
    expect(mergeCommentPool([working], [inbox])[0].assignment?.id).toBe('c')
  })
})

describe('commentsEmptyCopy', () => {
  it('names the empty AND', () => {
    expect(commentsEmptyCopy({ unlabeled: true, labelOn: true, loaded: true })).toBe('No comments match these selectors.')
    expect(commentsEmptyCopy({ unlabeled: true, labelOn: false, loaded: true })).toBe('No unlabeled observations.')
    expect(commentsEmptyCopy({ unlabeled: false, labelOn: true, loaded: true })).toBe('No comments matched.')
    expect(commentsEmptyCopy({ unlabeled: false, labelOn: false, loaded: true })).toBe('No comments to distill.')
  })

  it('is blank when comments never loaded', () => {
    expect(commentsEmptyCopy({ unlabeled: false, labelOn: false, loaded: false })).toBe('')
    expect(commentsEmptyCopy({ unlabeled: false, labelOn: true, loaded: false })).toBe('')
    expect(commentsEmptyCopy({ unlabeled: true, labelOn: false, loaded: false })).toBe('')
  })
})
