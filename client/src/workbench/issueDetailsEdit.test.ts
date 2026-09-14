import { describe, expect, it } from 'vitest'
import { canSaveIssueEdit, canShowIssueEdit, issueDetailsErrorText, issueEditSaves, nextIssueSaveError, shouldReloadAfterIssueSaves, shouldSyncIssueEditFromProps } from './issueDetailsEdit.ts'

describe('issueDetailsEdit', () => {
  it('shows Edit only when a live type is selected', () => {
    const issue = { id: 't1' }
    expect(canShowIssueEdit({ selectedId: 't1', missing: false, issue })).toBe(true)
    expect(canShowIssueEdit({ selectedId: '', missing: false, issue: null })).toBe(false)
    expect(canShowIssueEdit({ selectedId: 't1', missing: true, issue: null })).toBe(false)
  })

  it('disables Save when name or definition is blank', () => {
    expect(canSaveIssueEdit('Overclaiming', 'A claim is too strong.')).toBe(true)
    expect(canSaveIssueEdit('  ', 'A claim is too strong.')).toBe(false)
    expect(canSaveIssueEdit('Overclaiming', '  ')).toBe(false)
  })

  it('saves only the fields that changed', () => {
    expect(issueEditSaves({
      currentName: 'Overclaiming',
      currentDefinition: 'old',
      nextName: 'Overclaiming',
      nextDefinition: 'new',
    })).toEqual([{ kind: 'edit', definition: 'new' }])
    expect(issueEditSaves({
      currentName: 'Old',
      currentDefinition: 'same',
      nextName: 'New',
      nextDefinition: 'same',
    })).toEqual([{ kind: 'rename', name: 'New' }])
    expect(issueEditSaves({
      currentName: 'Old',
      currentDefinition: 'old',
      nextName: 'New',
      nextDefinition: 'new',
    })).toEqual([
      { kind: 'rename', name: 'New' },
      { kind: 'edit', definition: 'new' },
    ])
    expect(issueEditSaves({
      currentName: 'Overclaiming',
      currentDefinition: 'old',
      nextName: '  Overclaiming  ',
      nextDefinition: 'old',
    })).toEqual([])
  })

  it('reloads Issue Details after any successful save POST', () => {
    expect(shouldReloadAfterIssueSaves(0)).toBe(false)
    expect(shouldReloadAfterIssueSaves(1)).toBe(true)
    expect(shouldReloadAfterIssueSaves(2)).toBe(true)
  })

  it('keeps the edit draft while a partial save is reloading Issue Details', () => {
    expect(shouldSyncIssueEditFromProps(true)).toBe(false)
    expect(shouldSyncIssueEditFromProps(false)).toBe(true)
  })

  it('keeps the save error after Issue Details reloads', () => {
    expect(issueDetailsErrorText('Could not save definition', '')).toBe('Could not save definition')
    expect(issueDetailsErrorText('Could not save definition', 'Not found')).toBe('Could not save definition')
    expect(issueDetailsErrorText('', 'Not found')).toBe('Not found')
    expect(issueDetailsErrorText('  ', 'Not found')).toBe('Not found')
  })

  it('clears the save error when leaving the failed edit', () => {
    expect(nextIssueSaveError({ keepDraft: true, current: 'Could not save definition' })).toBe(
      'Could not save definition',
    )
    expect(nextIssueSaveError({ keepDraft: false, current: 'Could not save definition' })).toBe('')
  })
})
