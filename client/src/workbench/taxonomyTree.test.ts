import type { TaxonomyNode } from './taxonomyTree.ts'
import { describe, expect, it } from 'vitest'
import { assignableLabelRows, findNode, flattenForest, isLeaf, moveBody } from './taxonomyTree.ts'

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

describe('taxonomyTree', () => {
  it('flattens with depth', () => {
    expect(flattenForest(forest).map((row) => [row.node.id, row.depth])).toEqual([
      ['root', 0],
      ['a', 1],
      ['b', 1],
    ])
  })

  it('detects leaves', () => {
    expect(isLeaf(forest[0])).toBe(false)
    expect(isLeaf(forest[0].children[0])).toBe(true)
  })

  it('nests as last child on inner', () => {
    expect(moveBody(forest, 'a', 'root', 'inner')).toEqual({ parent_id: 'root', position: 1 })
  })

  it('inserts before a sibling', () => {
    expect(moveBody(forest, 'b', 'a', 'before')).toEqual({ parent_id: 'root', position: 0 })
  })

  it('inserts after a root', () => {
    const twoRoots: TaxonomyNode[] = [
      { id: 'x', name: 'X', count: 0, children: [] },
      { id: 'y', name: 'Y', count: 0, children: [] },
    ]
    expect(moveBody(twoRoots, 'y', 'x', 'after')).toEqual({ parent_id: null, position: 1 })
  })

  it('finds a nested node', () => {
    expect(findNode(forest, 'b')?.name).toBe('B')
  })

  it('offers leaves for assign, plus the current type if it is a parent', () => {
    expect(assignableLabelRows(forest).map((row) => row.id)).toEqual(['a', 'b'])
    expect(assignableLabelRows(forest, 'root').map((row) => [row.id, row.depth])).toEqual([
      ['root', 0],
      ['a', 1],
      ['b', 1],
    ])
  })
})
