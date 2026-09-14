import type { TaxonomyNode } from '../api/client.ts'

export type { TaxonomyNode }

export function flattenForest(forest: TaxonomyNode[], depth = 0): { node: TaxonomyNode, depth: number }[] {
  return forest.flatMap((node) => [{ node, depth }, ...flattenForest(node.children, depth + 1)])
}

export function isLeaf(node: TaxonomyNode): boolean {
  return node.children.length === 0
}

/** Leaves, plus ``currentId`` so a leftover parent label still shows in the menu. */
export function assignableIssueRows(
  forest: TaxonomyNode[],
  currentId?: string | null,
): { id: string, name: string, depth: number }[] {
  return flattenForest(forest)
    .filter(({ node }) => isLeaf(node) || node.id === currentId)
    .map(({ node, depth }) => ({ id: node.id, name: node.name, depth }))
}

export function descendantIds(node: TaxonomyNode): string[] {
  return node.children.flatMap((child) => [child.id, ...descendantIds(child)])
}

export function findNode(forest: TaxonomyNode[], id: string): TaxonomyNode | null {
  for (const node of forest) {
    if (node.id === id) { return node }
    const found = findNode(node.children, id)
    if (found) { return found }
  }
  return null
}

export function findParent(forest: TaxonomyNode[], id: string): TaxonomyNode | null {
  for (const node of forest) {
    if (node.children.some((child) => child.id === id)) { return node }
    const found = findParent(node.children, id)
    if (found) { return found }
  }
  return null
}

function siblingIndex(siblings: TaxonomyNode[], id: string): number {
  return siblings.findIndex((node) => node.id === id)
}

/** Server move body from a before/inner/after drop. */
export function moveBody(
  forest: TaxonomyNode[],
  sourceId: string,
  targetId: string,
  placement: 'before' | 'inner' | 'after',
): { parent_id: string | null, position: number } | null {
  const target = findNode(forest, targetId)
  if (!target) { return null }
  if (placement === 'inner') {
    const withoutSource = target.children.filter((child) => child.id !== sourceId)
    return { parent_id: targetId, position: withoutSource.length }
  }
  const parent = findParent(forest, targetId)
  const siblings = parent ? parent.children : forest
  const withoutSource = siblings.filter((node) => node.id !== sourceId)
  const targetIndex = siblingIndex(withoutSource, targetId)
  if (targetIndex < 0) { return null }
  const position = placement === 'before' ? targetIndex : targetIndex + 1
  return { parent_id: parent?.id ?? null, position }
}
