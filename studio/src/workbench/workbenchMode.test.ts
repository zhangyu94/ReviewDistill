import { describe, expect, it } from 'vitest'
import { activeSelector, allowChangeDrop, disappearedHref, dismissTypeHref, entryMode, groupIdFromRoute, inboxItemFromObservation, inspectorKind, taxonClickHref, thisTypeHref, typeSelectorLabel, uncodedHref } from './workbenchMode.ts'

describe('entryMode', () => {
  it('uses the uncoded queue on the inbox route', () => {
    expect(entryMode('inbox')).toBe('uncoded')
  })

  it('uses disappeared comments on the disappeared route', () => {
    expect(entryMode('disappeared')).toBe('disappeared')
  })

  it('uses type observations on taxonomy routes', () => {
    expect(entryMode('taxonomy')).toBe('observations')
    expect(entryMode('issue')).toBe('observations')
  })
})

describe('inspectorKind', () => {
  it('shows the comment inspector on inbox routes', () => {
    expect(inspectorKind('inbox')).toBe('comment')
    expect(inspectorKind('disappeared')).toBe('comment')
  })

  it('shows the issue inspector on taxonomy routes', () => {
    expect(inspectorKind('taxonomy')).toBe('issue')
    expect(inspectorKind('issue')).toBe('issue')
  })
})

describe('allowChangeDrop', () => {
  it('allows comment-to-type drops only while uncoded', () => {
    expect(allowChangeDrop('uncoded', 'change')).toBe(true)
    expect(allowChangeDrop('disappeared', 'change')).toBe(false)
    expect(allowChangeDrop('observations', 'change')).toBe(false)
  })

  it('allows merge and move in every entry mode', () => {
    expect(allowChangeDrop('disappeared', 'merge')).toBe(true)
    expect(allowChangeDrop('observations', 'move')).toBe(true)
  })
})

describe('activeSelector', () => {
  it('selects Uncoded on the inbox route', () => {
    expect(activeSelector('inbox', '')).toBe('uncoded')
  })

  it('selects Disappeared on the disappeared route', () => {
    expect(activeSelector('disappeared', 't1')).toBe('disappeared')
  })

  it('selects This type on an issue route with an id', () => {
    expect(activeSelector('issue', 't1')).toBe('type')
  })

  it('falls back to Uncoded when taxonomy has no selected type', () => {
    expect(activeSelector('taxonomy', '')).toBe('uncoded')
  })
})

describe('groupIdFromRoute', () => {
  it('prefers the taxonomy path id', () => {
    expect(groupIdFromRoute('t1', 't2')).toBe('t1')
  })

  it('reads type from the query when the path has no id', () => {
    expect(groupIdFromRoute('', 't2')).toBe('t2')
  })
})

describe('selector hrefs', () => {
  it('keeps the selected group when switching Uncoded and Disappeared', () => {
    expect(uncodedHref('t1')).toBe('/?type=t1')
    expect(disappearedHref('t1')).toBe('/inbox/disappeared?type=t1')
  })

  it('omits type when no group is selected', () => {
    expect(uncodedHref('')).toBe('/')
    expect(disappearedHref('')).toBe('/inbox/disappeared')
  })

  it('opens This type on the taxonomy path', () => {
    expect(thisTypeHref('t1')).toBe('/taxonomy/t1')
    expect(thisTypeHref('')).toBe('')
  })
})

describe('taxonClickHref', () => {
  it('selects the type instead of only adding a selector chip', () => {
    expect(taxonClickHref('t1')).toBe('/taxonomy/t1')
  })
})

describe('dismissTypeHref', () => {
  it('returns Uncoded when dismissing from Uncoded or a type chip', () => {
    expect(dismissTypeHref('uncoded')).toBe('/')
    expect(dismissTypeHref('type')).toBe('/')
  })

  it('stays on Disappeared when dismissing from Disappeared', () => {
    expect(dismissTypeHref('disappeared')).toBe('/inbox/disappeared')
  })
})

describe('typeSelectorLabel', () => {
  it('uses the issue code and accepted count', () => {
    expect(typeSelectorLabel('MISSINGINTRODUCT', 3)).toBe('MISSINGINTRODUCT (3)')
  })
})

describe('inboxItemFromObservation', () => {
  it('maps a taxonomy comment onto the inbox item shape for the detail view', () => {
    const item = inboxItemFromObservation({
      id: 'c1',
      project_id: 'p',
      source_type: 'latex_command',
      source_command: 'myremark',
      file_path: 'main.tex',
      line_number: 4,
      raw_text: 'add an overview',
      context_text: 'Section 2\nlabel=sec:2',
      section: 'Background',
      git_commit: 'abc1234deadbeef',
      git_url: 'https://example.com/repo.git',
      fingerprint: 'fp',
      status: 'active',
      supersedes_id: null,
      created_at: '2026-01-01T00:00:00',
      project_name: 'paper',
      permalink: 'https://example.com/blob/main.tex#L4',
    })
    expect(item.comment.raw_text).toBe('add an overview')
    expect(item.comment.context_text).toContain('Section 2')
    expect(item.comment.file_path).toBe('main.tex')
    expect(item.project_name).toBe('paper')
    expect(item.permalink).toContain('main.tex')
    expect(item.coding).toBeNull()
  })
})
