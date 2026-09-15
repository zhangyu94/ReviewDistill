import type { InboxItemJson, TaxonomyNode } from '../api/client.ts'
import { findNode, isLeaf } from './taxonomyTree.ts'

export function commentListLeafLabels(
  item: Pick<InboxItemJson, 'labeled' | 'label'>,
  forest: TaxonomyNode[],
): { id: string, name: string }[] {
  if (!item.labeled || !item.label) {
    return []
  }
  const node = findNode(forest, item.label.id)
  if (node && !isLeaf(node)) {
    return []
  }
  return [{ id: item.label.id, name: item.label.name }]
}

export function commentListLeafLabelNames(
  item: Pick<InboxItemJson, 'labeled' | 'label'>,
  forest: TaxonomyNode[],
): string {
  return commentListLeafLabels(item, forest).map((label) => label.name).join(' · ')
}
