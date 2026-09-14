import type { InboxItemJson, TaxonomyNode } from '../api/client.ts'
import { findNode, isLeaf } from './taxonomyTree.ts'

export function commentListLeafTypes(
  item: Pick<InboxItemJson, 'labeled' | 'issue'>,
  forest: TaxonomyNode[],
): { id: string, name: string }[] {
  if (!item.labeled || !item.issue) {
    return []
  }
  const node = findNode(forest, item.issue.id)
  if (node && !isLeaf(node)) {
    return []
  }
  return [{ id: item.issue.id, name: item.issue.name }]
}

export function commentListLeafTypeLabel(
  item: Pick<InboxItemJson, 'labeled' | 'issue'>,
  forest: TaxonomyNode[],
): string {
  return commentListLeafTypes(item, forest).map((type) => type.name).join(' · ')
}
