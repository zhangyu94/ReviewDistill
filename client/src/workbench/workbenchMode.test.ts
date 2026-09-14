import { describe, expect, it } from 'vitest'
import { afterHomeChange, afterMergeNavigation, afterTypeTreeChangeParts, allowChangeDrop, clearIssueBeforeLoad, entryMode, homeSaveFollowUpOrder, inboxItemFromObservation, inspectorKind, issueIdAfterLeave, issueLoadErrorView, labeledTypeIdForComment, selectGroupHref, shouldApplyIssueLoad, showAssignType, typeRouteAfterDeactivate, typeRouteAfterRemove } from './workbenchMode.ts'

describe('workbenchMode', () => {
  it('uses the unlabeled queue on the inbox route', () => {
    expect(entryMode('inbox')).toBe('unlabeled')
  })

  it('uses observations on the issue route', () => {
    expect(entryMode('issue')).toBe('observations')
  })

  it('picks the inspector from the route', () => {
    expect(inspectorKind('inbox')).toBe('comment')
    expect(inspectorKind('issue')).toBe('issue')
  })

  it('allows comment-to-type drops only for unlabeled comments', () => {
    expect(allowChangeDrop(false, 'change')).toBe(true)
    expect(allowChangeDrop(true, 'change')).toBe(false)
    expect(allowChangeDrop(false, 'merge')).toBe(true)
    expect(allowChangeDrop(true, 'merge')).toBe(true)
  })

  it('offers Accept only for unlabeled comments', () => {
    expect(showAssignType(false)).toBe(true)
    expect(showAssignType(true)).toBe(false)
  })

  it('marks synthetic type-chip items as labeled with the current type', () => {
    const issue = {
      id: 't1',
      name: 'Overclaiming',
      parent_id: null,
    }
    const item = inboxItemFromObservation({
      id: 'c1',
      project_id: 'p1',
      source_type: 'latex_command',
      source_command: 'myremark',
      file_path: 'main.tex',
      line_number: 1,
      raw_text: 'Too strong.',
      context_text: '',
      section: null,
      git_commit: null,
      git_url: null,
      fingerprint: 'fp',
      status: 'active',
      quality: 'unreviewed',
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
    }, issue)
    expect(item.labeled).toBe(true)
    expect(item.issue).toEqual(issue)
    expect(item.comment.quality).toBe('unreviewed')
  })

  it('keeps the type-chip inspector while reloading the same issue', () => {
    expect(clearIssueBeforeLoad('t1', 't1')).toBe(false)
    expect(clearIssueBeforeLoad('t1', 't2')).toBe(true)
    expect(clearIssueBeforeLoad('t1', '')).toBe(true)
    expect(clearIssueBeforeLoad('', 't1')).toBe(true)
  })

  it('ignores stale issue loads', () => {
    expect(shouldApplyIssueLoad(1, 2)).toBe(false)
    expect(shouldApplyIssueLoad(2, 2)).toBe(true)
  })

  it('shows not-found only for 404; other failures are errors', () => {
    expect(issueLoadErrorView(404)).toBe('missing')
    expect(issueLoadErrorView(500)).toBe('error')
    expect(issueLoadErrorView(null)).toBe('error')
  })

  it('looks up the labeled type for a dragged comment', () => {
    const item = inboxItemFromObservation({
      id: 'c1',
      project_id: 'p1',
      source_type: 'latex_command',
      source_command: 'myremark',
      file_path: 'main.tex',
      line_number: 1,
      raw_text: 'Too strong.',
      context_text: '',
      section: null,
      git_commit: null,
      git_url: null,
      fingerprint: 'fp',
      status: 'active',
      quality: 'unreviewed',
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
    }, { id: 't1', name: 'Overclaiming', parent_id: null })
    expect(labeledTypeIdForComment([item], 'c1')).toBe('t1')
    expect(labeledTypeIdForComment([item], 'missing')).toBeNull()
    expect(labeledTypeIdForComment([{ ...item, issue: null }], 'c1')).toBeNull()
  })

  it('prefers the comment accepted type over the selected node', () => {
    const parent = { id: 'p', name: 'Parent', parent_id: null }
    const child = { id: 'c', name: 'Child', parent_id: 'p' }
    const item = inboxItemFromObservation({
      id: 'c1',
      project_id: 'p1',
      source_type: 'latex_command',
      source_command: 'myremark',
      file_path: 'main.tex',
      line_number: 1,
      raw_text: 'Too strong.',
      context_text: '',
      section: null,
      git_commit: null,
      git_url: null,
      fingerprint: 'fp',
      status: 'active',
      quality: 'unreviewed',
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
      issue: child,
    }, parent)
    expect(item.issue).toEqual(child)
  })

  it('leaves the type route only when the viewed type was deactivated', () => {
    expect(typeRouteAfterDeactivate('t1', 't1')).toBe('/')
    expect(typeRouteAfterDeactivate('t1', 't2')).toBeNull()
    expect(typeRouteAfterDeactivate('', 't1')).toBeNull()
  })

  it('leaves the type route when the viewed type is in a removed subtree', () => {
    expect(typeRouteAfterRemove('child', ['root', 'child'])).toBe('/')
    expect(typeRouteAfterRemove('other', ['root', 'child'])).toBeNull()
    expect(typeRouteAfterRemove('', ['root'])).toBeNull()
  })

  it('clears the issue id when a type action navigates home', () => {
    expect(issueIdAfterLeave('/', 't1')).toBe('')
    expect(issueIdAfterLeave(null, 't1')).toBe('t1')
  })

  it('resets the workbench after switching the data folder', () => {
    expect(afterHomeChange()).toEqual({ href: '/', issueId: '' })
  })

  it('reloads the workbench before assistant settings after a data-folder save', () => {
    expect(homeSaveFollowUpOrder()).toEqual(['reload', 'llm'])
  })

  it('keeps the type chip off when selecting a type with Unlabeled on', () => {
    expect(selectGroupHref('abc', true)).toBe('/taxonomy/abc?unlabeled=1&typechip=0')
    expect(selectGroupHref('abc', false)).toBe('/taxonomy/abc')
  })

  it('reloads comments after a taxonomy tree change that can move labels', () => {
    expect(afterTypeTreeChangeParts()).toEqual({ taxonomy: true, issue: true, inbox: true })
  })

  it('loads the merge target instead of the viewed source', () => {
    expect(afterMergeNavigation({ unlabeled: false, detailsId: 'source' }, 'target', '', 'source', 'source')).toEqual({
      href: '/taxonomy/target',
      issueId: 'target',
      replace: true,
    })
    expect(afterMergeNavigation({ unlabeled: false, detailsId: 'other' }, 'target', '', 'other', 'source')).toEqual({
      href: '/taxonomy/target',
      issueId: 'target',
      replace: false,
    })
    expect(afterMergeNavigation({ unlabeled: true, detailsId: '' }, 'target', 'c1')).toEqual({
      href: '/taxonomy/target?unlabeled=1&typechip=0&id=c1',
      issueId: 'target',
      replace: true,
    })
  })
})
