import type { CodingJson } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import { assignSuggestion, shouldAssignOnSelect } from './assignLabel.ts'

const labels = [{ id: 't1', name: 'Overclaiming' }]

function coding(partial: Partial<CodingJson>): CodingJson {
  return {
    id: 'c',
    status: 'proposed',
    label_id: null,
    proposed_label_name: null,
    confidence: null,
    rationale: null,
    kind: 'new',
    ...partial,
  }
}

describe('assignSuggestion', () => {
  it('is null when there is no coding', () => {
    expect(assignSuggestion(null, labels)).toBeNull()
    expect(assignSuggestion(undefined, labels)).toBeNull()
  })

  it('uses the active type name for an existing proposal', () => {
    expect(assignSuggestion(coding({
      kind: 'existing',
      label_id: 't1',
      rationale: 'too strong',
    }), labels)).toEqual({
      title: 'Overclaiming',
      rationale: 'too strong',
    })
  })

  it('treats an unresolved existing id as no suggestion', () => {
    expect(assignSuggestion(coding({
      kind: 'existing',
      label_id: 'gone',
    }), labels)).toBeNull()
  })

  it('prefixes a new-type name', () => {
    expect(assignSuggestion(coding({
      kind: 'new',
      proposed_label_name: 'Insufficient justification',
    }), labels)?.title).toBe('New: Insufficient justification')
  })

  it('treats a new type without a name as no suggestion', () => {
    expect(assignSuggestion(coding({ kind: 'new' }), labels)).toBeNull()
  })
})

describe('assign menu', () => {
  it('assigns only when the user picks a different type', () => {
    expect(shouldAssignOnSelect(null, 't1')).toBe(true)
    expect(shouldAssignOnSelect('t1', 't1')).toBe(false)
    expect(shouldAssignOnSelect('t1', 't2')).toBe(true)
    expect(shouldAssignOnSelect(null, '')).toBe(false)
  })
})
