import type { TaxonomyNode } from './taxonomyTree.ts'
import { describe, expect, it } from 'vitest'
import { allTypeIds, exportQuery, toggleCheckedId } from './exportSelection.ts'

const forest: TaxonomyNode[] = [
  {
    id: 'root',
    name: 'Parent',
    count: 5,
    children: [
      { id: 'a', name: 'A', count: 1, children: [] },
      { id: 'b', name: 'B', count: 4, children: [] },
    ],
  },
]

describe('exportSelection', () => {
  it('lists every type id without cascading', () => {
    expect(allTypeIds(forest)).toEqual(['root', 'a', 'b'])
  })

  it('toggles one id without its children', () => {
    expect(toggleCheckedId(forest, ['root', 'a', 'b'], 'root')).toEqual(['a', 'b'])
    expect(toggleCheckedId(forest, ['a', 'b'], 'root')).toEqual(['root', 'a', 'b'])
  })

  it('builds the export query with repeated id', () => {
    expect(exportQuery('md', ['a', 'b'])).toBe('format=md&id=a&id=b')
  })
})
