import type { InboxItemJson, TaxonomyNode } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import { commentListLeafTypeLabel, commentListLeafTypes } from './commentList.ts'

const forest: TaxonomyNode[] = [
  {
    id: 'root',
    name: 'Parent',
    count: 5,
    children: [
      { id: 'a', name: 'Overclaiming', count: 1, children: [] },
      { id: 'b', name: 'Causal language', count: 4, children: [] },
    ],
  },
]

function item(partial: Partial<InboxItemJson> = {}): Pick<InboxItemJson, 'labeled' | 'issue'> {
  return {
    labeled: false,
    issue: null,
    ...partial,
  }
}

describe('commentListLeafTypes', () => {
  it('is empty when the comment is unlabeled', () => {
    expect(commentListLeafTypes(item(), forest)).toEqual([])
  })

  it('names the assigned leaf type', () => {
    expect(commentListLeafTypes(item({
      labeled: true,
      issue: { id: 'a', name: 'Overclaiming', parent_id: 'root' },
    }), forest)).toEqual([{ id: 'a', name: 'Overclaiming' }])
  })

  it('omits a leftover parent label', () => {
    expect(commentListLeafTypes(item({
      labeled: true,
      issue: { id: 'root', name: 'Parent', parent_id: null },
    }), forest)).toEqual([])
  })

  it('still names an assigned type missing from the forest', () => {
    expect(commentListLeafTypes(item({
      labeled: true,
      issue: { id: 'gone', name: 'Retired leaf', parent_id: null },
    }), forest)).toEqual([{ id: 'gone', name: 'Retired leaf' }])
  })

  it('joins leaf type names as plain text', () => {
    expect(commentListLeafTypeLabel(item(), forest)).toBe('')
    expect(commentListLeafTypeLabel(item({
      labeled: true,
      issue: { id: 'a', name: 'Overclaiming', parent_id: 'root' },
    }), forest)).toBe('Overclaiming')
  })
})
