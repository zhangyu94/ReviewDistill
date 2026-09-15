import type { ExportFormat } from '../api/client.ts'
import type { TaxonomyNode } from './taxonomyTree.ts'
import { flattenForest } from './taxonomyTree.ts'

export function allLabelIds(forest: TaxonomyNode[]): string[] {
  return flattenForest(forest).map(({ node }) => node.id)
}

export function toggleCheckedId(forest: TaxonomyNode[], ids: string[], id: string): string[] {
  const selected = new Set(ids)
  if (selected.has(id)) {
    selected.delete(id)
  }
  else {
    selected.add(id)
  }
  return allLabelIds(forest).filter((row) => selected.has(row))
}

export function exportQuery(fmt: ExportFormat, ids: string[]): string {
  const params = new URLSearchParams({ format: fmt })
  for (const id of ids) {
    params.append('id', id)
  }
  return params.toString()
}
