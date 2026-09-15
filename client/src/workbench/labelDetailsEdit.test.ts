import { describe, expect, it } from 'vitest'
import { canSaveLabelEdit, canShowLabelEdit, labelDetailsEmptyCopy, labelDetailsErrorText, labelEditSaves, nextLabelSaveError, shouldReloadAfterLabelSaves, shouldSyncLabelEditFromProps } from './labelDetailsEdit.ts'

describe('labelDetailsEdit', () => {
  it('shows Edit only when a live label is selected', () => {
    const label = { id: 't1' }
    expect(canShowLabelEdit({ selectedId: 't1', missing: false, label })).toBe(true)
    expect(canShowLabelEdit({ selectedId: '', missing: false, label: null })).toBe(false)
    expect(canShowLabelEdit({ selectedId: 't1', missing: true, label: null })).toBe(false)
  })

  it('disables Save when name or definition is blank', () => {
    expect(canSaveLabelEdit('Overclaiming', 'A claim is too strong.')).toBe(true)
    expect(canSaveLabelEdit('  ', 'A claim is too strong.')).toBe(false)
    expect(canSaveLabelEdit('Overclaiming', '  ')).toBe(false)
  })

  it('saves only the fields that changed', () => {
    expect(labelEditSaves({
      currentName: 'Overclaiming',
      currentDefinition: 'old',
      nextName: 'Overclaiming',
      nextDefinition: 'new',
    })).toEqual([{ kind: 'edit', definition: 'new' }])
    expect(labelEditSaves({
      currentName: 'Old',
      currentDefinition: 'same',
      nextName: 'New',
      nextDefinition: 'same',
    })).toEqual([{ kind: 'rename', name: 'New' }])
    expect(labelEditSaves({
      currentName: 'Old',
      currentDefinition: 'old',
      nextName: 'New',
      nextDefinition: 'new',
    })).toEqual([
      { kind: 'rename', name: 'New' },
      { kind: 'edit', definition: 'new' },
    ])
    expect(labelEditSaves({
      currentName: 'Overclaiming',
      currentDefinition: 'old',
      nextName: '  Overclaiming  ',
      nextDefinition: 'old',
    })).toEqual([])
  })

  it('reloads Label Details after any successful save POST', () => {
    expect(shouldReloadAfterLabelSaves(0)).toBe(false)
    expect(shouldReloadAfterLabelSaves(1)).toBe(true)
    expect(shouldReloadAfterLabelSaves(2)).toBe(true)
  })

  it('keeps the edit draft while a partial save is reloading Label Details', () => {
    expect(shouldSyncLabelEditFromProps(true)).toBe(false)
    expect(shouldSyncLabelEditFromProps(false)).toBe(true)
  })

  it('keeps the save error after Label Details reloads', () => {
    expect(labelDetailsErrorText('Could not save definition', '')).toBe('Could not save definition')
    expect(labelDetailsErrorText('Could not save definition', 'Not found')).toBe('Could not save definition')
    expect(labelDetailsErrorText('', 'Not found')).toBe('Not found')
    expect(labelDetailsErrorText('  ', 'Not found')).toBe('Not found')
  })

  it('hides a load error while the selected label is still loading', () => {
    expect(labelDetailsErrorText('', 'store corrupt', true)).toBe('')
    expect(labelDetailsErrorText('Could not save definition', 'store corrupt', true)).toBe(
      'Could not save definition',
    )
  })

  it('clears the save error when leaving the failed edit', () => {
    expect(nextLabelSaveError({ keepDraft: true, current: 'Could not save definition' })).toBe(
      'Could not save definition',
    )
    expect(nextLabelSaveError({ keepDraft: false, current: 'Could not save definition' })).toBe('')
  })

  it('uses Select a label only when nothing is selected', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: '',
      missing: false,
      hasLabel: false,
      loading: false,
      hasError: false,
    })).toBe('Select a label.')
  })

  it('says the open label was not found', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: 't1',
      missing: true,
      hasLabel: false,
      loading: false,
      hasError: false,
    })).toBe('This label was not found.')
  })

  it('stays blank while the selected label is still loading', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: 't1',
      missing: false,
      hasLabel: false,
      loading: true,
      hasError: false,
    })).toBe('')
    expect(labelDetailsEmptyCopy({
      selectedId: 't2',
      missing: true,
      hasLabel: false,
      loading: true,
      hasError: false,
    })).toBe('')
  })

  it('stays blank when the label payload is present', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: 't1',
      missing: false,
      hasLabel: true,
      loading: false,
      hasError: false,
    })).toBe('')
  })

  it('does not repeat a panel error as Could not load', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: 't1',
      missing: false,
      hasLabel: false,
      loading: false,
      hasError: true,
    })).toBe('')
  })

  it('says it could not load the selected label after the request finishes empty', () => {
    expect(labelDetailsEmptyCopy({
      selectedId: 't1',
      missing: false,
      hasLabel: false,
      loading: false,
      hasError: false,
    })).toBe('Couldn\'t load this label.')
  })
})
