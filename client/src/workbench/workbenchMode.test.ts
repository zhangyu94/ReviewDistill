import { describe, expect, it } from 'vitest'
import { afterHomeChange, afterLabelTreeChangeParts, afterMergeNavigation, allowChangeDrop, clearLabelBeforeLoad, entryMode, homeSaveFollowUpOrder, inboxItemFromObservation, inspectorKind, labeledLabelIdForComment, labelIdAfterLeave, labelLoadErrorView, labelRouteAfterRemove, selectGroupHref, shouldApplyLabelLoad, showAssignLabel } from './workbenchMode.ts'

describe('workbenchMode', () => {
  it('uses the unlabeled queue on the inbox route', () => {
    expect(entryMode('inbox')).toBe('unlabeled')
  })

  it('uses observations on the label route', () => {
    expect(entryMode('label')).toBe('observations')
  })

  it('picks the inspector from the route', () => {
    expect(inspectorKind('inbox')).toBe('comment')
    expect(inspectorKind('label')).toBe('label')
  })

  it('allows comment-to-type drops only for unlabeled comments', () => {
    expect(allowChangeDrop(false, 'change')).toBe(true)
    expect(allowChangeDrop(true, 'change')).toBe(false)
    expect(allowChangeDrop(false, 'merge')).toBe(true)
    expect(allowChangeDrop(true, 'merge')).toBe(true)
  })

  it('offers Accept only for unlabeled comments', () => {
    expect(showAssignLabel(false)).toBe(true)
    expect(showAssignLabel(true)).toBe(false)
  })

  it('marks synthetic label-chip items as labeled with the current label', () => {
    const label = {
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
      context_offset: null,
      section: null,
      git_commit: null,
      git_url: null,
      status: 'active',
      verified: false,
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
    }, label)
    expect(item.labeled).toBe(true)
    expect(item.label).toEqual(label)
    expect(item.comment.verified).toBe(false)
  })

  it('keeps the label-chip inspector while reloading the same label', () => {
    expect(clearLabelBeforeLoad('t1', 't1')).toBe(false)
    expect(clearLabelBeforeLoad('t1', 't2')).toBe(true)
    expect(clearLabelBeforeLoad('t1', '')).toBe(true)
    expect(clearLabelBeforeLoad('', 't1')).toBe(true)
  })

  it('ignores stale label loads', () => {
    expect(shouldApplyLabelLoad(1, 2)).toBe(false)
    expect(shouldApplyLabelLoad(2, 2)).toBe(true)
  })

  it('shows not-found only for 404; other failures are errors', () => {
    expect(labelLoadErrorView(404)).toBe('missing')
    expect(labelLoadErrorView(500)).toBe('error')
    expect(labelLoadErrorView(null)).toBe('error')
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
      context_offset: null,
      section: null,
      git_commit: null,
      git_url: null,
      status: 'active',
      verified: false,
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
    }, { id: 't1', name: 'Overclaiming', parent_id: null })
    expect(labeledLabelIdForComment([item], 'c1')).toBe('t1')
    expect(labeledLabelIdForComment([item], 'missing')).toBeNull()
    expect(labeledLabelIdForComment([{ ...item, label: null }], 'c1')).toBeNull()
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
      context_offset: null,
      section: null,
      git_commit: null,
      git_url: null,
      status: 'active',
      verified: false,
      supersedes_id: null,
      created_at: '2024-01-01T00:00:00Z',
      project_name: 'paper',
      permalink: null,
      label: child,
    }, parent)
    expect(item.label).toEqual(child)
  })

  it('leaves the type route when the viewed type is in a removed subtree', () => {
    expect(labelRouteAfterRemove('child', ['root', 'child'])).toBe('/')
    expect(labelRouteAfterRemove('other', ['root', 'child'])).toBeNull()
    expect(labelRouteAfterRemove('', ['root'])).toBeNull()
  })

  it('clears the label id when a label action navigates home', () => {
    expect(labelIdAfterLeave('/', 't1')).toBe('')
    expect(labelIdAfterLeave(null, 't1')).toBe('t1')
  })

  it('resets the workbench after switching the data folder', () => {
    expect(afterHomeChange()).toEqual({ href: '/', labelId: '' })
  })

  it('reloads the workbench before assistant settings after a data-folder save', () => {
    expect(homeSaveFollowUpOrder()).toEqual(['reload', 'llm'])
  })

  it('keeps the type chip off when selecting a type with Unlabeled on', () => {
    expect(selectGroupHref('abc', true)).toBe('/labels/abc?unlabeled=1&labelchip=0')
    expect(selectGroupHref('abc', false)).toBe('/labels/abc')
  })

  it('reloads comments after a taxonomy tree change that can move labels', () => {
    expect(afterLabelTreeChangeParts()).toEqual({ labels: true, label: true, inbox: true })
  })

  it('loads the merge target instead of the viewed source', () => {
    expect(afterMergeNavigation({ unlabeled: false, detailsId: 'source' }, 'target', '', 'source', 'source')).toEqual({
      href: '/labels/target',
      labelId: 'target',
      replace: true,
    })
    expect(afterMergeNavigation({ unlabeled: false, detailsId: 'other' }, 'target', '', 'other', 'source')).toEqual({
      href: '/labels/target',
      labelId: 'target',
      replace: false,
    })
    expect(afterMergeNavigation({ unlabeled: true, detailsId: '' }, 'target', 'c1')).toEqual({
      href: '/labels/target?unlabeled=1&labelchip=0&id=c1',
      labelId: 'target',
      replace: true,
    })
  })
})
