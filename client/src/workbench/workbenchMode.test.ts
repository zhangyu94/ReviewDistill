import { describe, expect, it } from 'vitest'
import { activeSelector, allowChangeDrop, changeIssueOptions, clearIssueBeforeLoad, dismissTypeHref, entryMode, groupIdFromRoute, inboxItemFromObservation, inspectorKind, issueLoadErrorView, labeledTypeIdForComment, nextChangeId, shouldApplyIssueLoad, showAssignType, taxonClickHref, thisTypeHref, typeRouteAfterDeactivate, typeSelectorLabel, unlabeledHref } from './workbenchMode.ts'

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

  it('allows comment-to-type drops only while unlabeled', () => {
    expect(allowChangeDrop('unlabeled', 'change')).toBe(true)
    expect(allowChangeDrop('observations', 'change')).toBe(false)
    expect(allowChangeDrop('unlabeled', 'merge')).toBe(true)
    expect(allowChangeDrop('observations', 'merge')).toBe(true)
  })

  it('selects Unlabeled on the inbox route', () => {
    expect(activeSelector('inbox', '')).toBe('unlabeled')
  })

  it('selects the type chip on an issue route', () => {
    expect(activeSelector('issue', 't1')).toBe('type')
  })

  it('prefers the path id over ?type=', () => {
    expect(groupIdFromRoute('from-path', 'from-query')).toBe('from-path')
    expect(groupIdFromRoute('', 'from-query')).toBe('from-query')
  })

  it('keeps the selected group on the unlabeled href', () => {
    expect(unlabeledHref('t1')).toBe('/?type=t1')
    expect(unlabeledHref('')).toBe('/')
  })

  it('opens a type from the groups panel on /taxonomy/:id', () => {
    expect(taxonClickHref('t1')).toBe('/taxonomy/t1')
    expect(thisTypeHref('t1')).toBe('/taxonomy/t1')
    expect(thisTypeHref('')).toBe('')
  })

  it('returns Unlabeled when dismissing a type chip', () => {
    expect(dismissTypeHref('unlabeled')).toBe('/')
    expect(dismissTypeHref('type')).toBe('/')
  })

  it('labels the type chip with code and count', () => {
    expect(typeSelectorLabel('OVERCLAIM', 3)).toBe('OVERCLAIM (3)')
  })

  it('offers Accept only for unlabeled comments', () => {
    expect(showAssignType('unlabeled', false)).toBe(true)
    expect(showAssignType('unlabeled', true)).toBe(false)
    expect(showAssignType('observation', false)).toBe(false)
    expect(showAssignType('observation', true)).toBe(false)
  })

  it('marks synthetic type-chip items as labeled with the current type', () => {
    const issue = {
      id: 't1',
      code: 'OVERCLAIM',
      name: 'Overclaiming',
      category: 'Argumentation',
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
    }, { id: 't1', code: 'OVERCLAIM', name: 'Overclaiming', category: 'Argumentation' })
    expect(labeledTypeIdForComment([item], 'c1')).toBe('t1')
    expect(labeledTypeIdForComment([item], 'missing')).toBeNull()
    expect(labeledTypeIdForComment([{ ...item, issue: null }], 'c1')).toBeNull()
  })

  it('omits the current type from Change options', () => {
    const issues = [
      { id: 'a', code: 'A', name: 'A', category: 'X' },
      { id: 'b', code: 'B', name: 'B', category: 'X' },
    ]
    expect(changeIssueOptions(issues, 'a').map((row) => row.id)).toEqual(['b'])
    expect(changeIssueOptions(issues, null).map((row) => row.id)).toEqual(['a', 'b'])
  })

  it('defaults Change to another type when the current one is selected', () => {
    const issues = [
      { id: 'a', code: 'A', name: 'A', category: 'X' },
      { id: 'b', code: 'B', name: 'B', category: 'X' },
    ]
    expect(nextChangeId(issues, 'a', 'a')).toBe('b')
    expect(nextChangeId(issues, 'a', 'b')).toBe('b')
    expect(nextChangeId(issues, null, 'a')).toBe('a')
    expect(nextChangeId(issues, 'a', '')).toBe('b')
    expect(nextChangeId(issues, 'a', 'missing')).toBe('b')
    expect(nextChangeId([issues[0]], 'a', 'a')).toBe('')
  })

  it('leaves the type route only when the viewed type was deactivated', () => {
    expect(typeRouteAfterDeactivate('t1', 't1')).toBe('/')
    expect(typeRouteAfterDeactivate('t1', 't2')).toBeNull()
    expect(typeRouteAfterDeactivate('', 't1')).toBeNull()
  })
})
