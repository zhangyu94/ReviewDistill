import type { InboxItemJson, TaxonomyNode } from '../api/client.ts'
import { describe, expect, it } from 'vitest'
import { commentListLeafLabelNames, commentListLeafLabels, commentListLocationLabel } from './commentList.ts'

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

function item(partial: Partial<InboxItemJson> = {}): Pick<InboxItemJson, 'labeled' | 'label'> {
  return {
    labeled: false,
    label: null,
    ...partial,
  }
}

describe('commentListLeafLabels', () => {
  it('is empty when the comment is unlabeled', () => {
    expect(commentListLeafLabels(item(), forest)).toEqual([])
  })

  it('names the assigned leaf label', () => {
    expect(commentListLeafLabels(item({
      labeled: true,
      label: { id: 'a', name: 'Overclaiming', parent_id: 'root' },
    }), forest)).toEqual([{ id: 'a', name: 'Overclaiming' }])
  })

  it('omits a leftover parent label', () => {
    expect(commentListLeafLabels(item({
      labeled: true,
      label: { id: 'root', name: 'Parent', parent_id: null },
    }), forest)).toEqual([])
  })

  it('still names an assigned label missing from the forest', () => {
    expect(commentListLeafLabels(item({
      labeled: true,
      label: { id: 'gone', name: 'Retired leaf', parent_id: null },
    }), forest)).toEqual([{ id: 'gone', name: 'Retired leaf' }])
  })

  it('joins leaf label names as plain text', () => {
    expect(commentListLeafLabelNames(item(), forest)).toBe('')
    expect(commentListLeafLabelNames(item({
      labeled: true,
      label: { id: 'a', name: 'Overclaiming', parent_id: 'root' },
    }), forest)).toBe('Overclaiming')
  })
})

describe('commentListLocationLabel', () => {
  it('names the line in list and tree', () => {
    expect(commentListLocationLabel(10)).toBe('line 10')
    expect(commentListLocationLabel(4)).toBe('line 4')
  })
})
