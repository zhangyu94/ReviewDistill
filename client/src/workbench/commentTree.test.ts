import type { CommentJson, InboxItemJson } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import { adjacentVisibleCommentId, ancestorGroupIds, commentTree, commentTreeIds, expandAncestors, flattenCommentTree, selectedIdAfterTreeCollapse, visibleCommentTreeIds } from './commentTree'

function item(partial: Partial<Omit<InboxItemJson, 'comment'>> & {
  id: string
  comment?: Partial<CommentJson>
}): InboxItemJson {
  const { id, comment, ...rest } = partial
  return {
    comment: {
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
      ...comment,
      id: comment?.id ?? id,
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

function names(rows: ReturnType<typeof flattenCommentTree>): string[] {
  return rows.map((row) => row.kind === 'group' ? `${row.groupKind}:${row.name}` : row.item.comment.id)
}

describe('commentTree', () => {
  it('is empty when there are no comments', () => {
    expect(commentTree([])).toEqual([])
  })

  it('nests a root file under the project', () => {
    const a = item({ id: 'a', comment: { file_path: 'main.tex', line_number: 4 } })
    const forest = commentTree([a])
    expect(forest).toHaveLength(1)
    expect(forest[0]).toMatchObject({
      kind: 'group',
      groupKind: 'project',
      name: 'paper',
      count: 1,
      depth: 0,
    })
    expect(forest[0].children).toHaveLength(1)
    expect(forest[0].children[0]).toMatchObject({
      kind: 'group',
      groupKind: 'file',
      name: 'main.tex',
      count: 1,
      depth: 1,
    })
    const file = forest[0].children[0]
    if (file.kind !== 'group') { throw new Error('expected file group') }
    expect(file.children).toEqual([
      expect.objectContaining({ kind: 'comment', id: 'a', depth: 2, item: a }),
    ])
  })

  it('groups comments under the full file path', () => {
    const a = item({
      id: 'a',
      comment: { project_id: 'p1', file_path: 'sections/eval.tex', line_number: 10 },
      project_name: 'FlowGuard',
    })
    const b = item({
      id: 'b',
      comment: { project_id: 'p1', file_path: 'sections/eval.tex', line_number: 11 },
      project_name: 'FlowGuard',
    })
    const rows = flattenCommentTree(commentTree([b, a]), new Set())
    expect(names(rows)).toEqual([
      'project:FlowGuard',
      'file:sections/eval.tex',
      'a',
      'b',
    ])
    expect(rows[0]).toMatchObject({ kind: 'group', count: 2, depth: 0 })
    expect(rows[1]).toMatchObject({ kind: 'group', groupKind: 'file', count: 2, depth: 1 })
    expect(rows[2]).toMatchObject({ kind: 'comment', depth: 2, id: 'a' })
    expect(rows[3]).toMatchObject({ kind: 'comment', depth: 2, id: 'b' })
  })

  it('keeps projects separate and sorts by name then path then line', () => {
    const late = item({
      id: 'late',
      comment: { project_id: 'p-z', file_path: 'a.tex', line_number: 1 },
      project_name: 'zeta',
    })
    const deep = item({
      id: 'deep',
      comment: { project_id: 'p-a', file_path: 'z/end.tex', line_number: 2 },
      project_name: 'alpha',
    })
    const early = item({
      id: 'early',
      comment: { project_id: 'p-a', file_path: 'a.tex', line_number: 9 },
      project_name: 'alpha',
    })
    expect(names(flattenCommentTree(commentTree([late, deep, early]), new Set()))).toEqual([
      'project:alpha',
      'file:a.tex',
      'early',
      'file:z/end.tex',
      'deep',
      'project:zeta',
      'file:a.tex',
      'late',
    ])
    expect(commentTreeIds([late, deep, early])).toEqual(['early', 'deep', 'late'])
  })

  it('hides descendants of a collapsed group and keeps the group row', () => {
    const a = item({
      id: 'a',
      comment: { file_path: 'sections/eval.tex', line_number: 10 },
    })
    const forest = commentTree([a])
    const file = forest[0]?.children[0]
    if (file?.kind !== 'group') { throw new Error('expected file') }
    const rows = flattenCommentTree(forest, new Set([file.id]))
    expect(names(rows)).toEqual(['project:paper', 'file:sections/eval.tex'])
    expect(rows[1]).toMatchObject({ count: 1 })
  })

  it('lists visible comment ids and skips collapsed files in j/k', () => {
    const a = item({
      id: 'a',
      comment: { file_path: 'a.tex', line_number: 1 },
    })
    const b = item({
      id: 'b',
      comment: { file_path: 'b.tex', line_number: 1 },
    })
    const c = item({
      id: 'c',
      comment: { file_path: 'b.tex', line_number: 2 },
    })
    const items = [a, b, c]
    const forest = commentTree(items)
    const fileB = forest[0]?.children.find((row) => row.kind === 'group' && row.name === 'b.tex')
    if (fileB?.kind !== 'group') { throw new Error('expected b.tex') }
    const collapsed = new Set([fileB.id])
    expect(visibleCommentTreeIds(items, collapsed)).toEqual(['a'])
    expect(adjacentVisibleCommentId(items, collapsed, 'a', 1)).toBeUndefined()
    expect(adjacentVisibleCommentId(items, collapsed, 'b', 1)).toBeUndefined()
    expect(adjacentVisibleCommentId(items, collapsed, 'b', -1)).toBe('a')
    expect(adjacentVisibleCommentId(items, collapsed, 'c', -1)).toBe('a')
    expect(adjacentVisibleCommentId(items, new Set(), 'a', 1)).toBe('b')
    expect(adjacentVisibleCommentId(items, new Set(), 'b', -1)).toBe('a')
  })

  it('expands ancestors of the selected comment', () => {
    const a = item({
      id: 'a',
      comment: { file_path: 'sections/eval.tex', line_number: 10 },
    })
    const forest = commentTree([a])
    const project = forest[0]
    const file = project?.children[0]
    if (project?.kind !== 'group' || file?.kind !== 'group') { throw new Error('expected groups') }
    const collapsed = new Set([project.id, file.id, 'other'])
    expect(ancestorGroupIds([a], 'a')).toEqual([project.id, file.id])
    expect([...expandAncestors(collapsed, [a], 'a')].sort()).toEqual(['other'])
  })

  it('reveals from a local file group, not from a missing checkout', () => {
    const local = item({
      id: 'a',
      comment: { file_path: 'sections/eval.tex', line_number: 10 },
      local_file: true,
    })
    const missing = item({
      id: 'b',
      comment: { file_path: 'gone.tex', line_number: 2 },
      local_file: false,
    })
    const forest = commentTree([local, missing])
    const files = forest[0]?.children ?? []
    expect(files).toEqual([
      expect.objectContaining({ groupKind: 'file', name: 'gone.tex', revealId: null }),
      expect.objectContaining({ groupKind: 'file', name: 'sections/eval.tex', revealId: 'a' }),
    ])
  })

  it('keeps selection when collapse leaves that comment visible', () => {
    const a = item({ id: 'a', comment: { file_path: 'a.tex', line_number: 1 } })
    const b = item({ id: 'b', comment: { file_path: 'b.tex', line_number: 1 } })
    const forest = commentTree([a, b])
    const fileA = forest[0]?.children.find((row) => row.kind === 'group' && row.name === 'a.tex')
    if (fileA?.kind !== 'group') { throw new Error('expected a.tex') }
    expect(selectedIdAfterTreeCollapse([a, b], new Set([fileA.id]), 'b')).toBe('b')
  })

  it('moves selection to a visible neighbor when collapse hides the open comment', () => {
    const a = item({ id: 'a', comment: { file_path: 'a.tex', line_number: 1 } })
    const b = item({ id: 'b', comment: { file_path: 'b.tex', line_number: 1 } })
    const c = item({ id: 'c', comment: { file_path: 'b.tex', line_number: 2 } })
    const forest = commentTree([a, b, c])
    const fileB = forest[0]?.children.find((row) => row.kind === 'group' && row.name === 'b.tex')
    if (fileB?.kind !== 'group') { throw new Error('expected b.tex') }
    expect(selectedIdAfterTreeCollapse([a, b, c], new Set([fileB.id]), 'b')).toBe('a')
    expect(selectedIdAfterTreeCollapse([a, b, c], new Set([fileB.id]), 'c')).toBe('a')
  })

  it('keeps the hidden id when collapse hides every comment', () => {
    const a = item({ id: 'a', comment: { file_path: 'a.tex', line_number: 1 } })
    const forest = commentTree([a])
    const file = forest[0]?.children[0]
    if (file?.kind !== 'group') { throw new Error('expected file') }
    expect(selectedIdAfterTreeCollapse([a], new Set([file.id]), 'a')).toBe('a')
  })
})
