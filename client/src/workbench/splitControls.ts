import { workbenchHref } from './commentSelectors.ts'

export function canHeaderSplit(opts: {
  forestEmpty: boolean
  unlabeledCount: number
  llmConfigured: boolean
}): boolean {
  return opts.forestEmpty && opts.unlabeledCount >= 2 && opts.llmConfigured
}

export function canHeaderSplitFromState(opts: {
  forest: unknown[] | undefined
  unlabeledWorkingCount: number
  llmConfigured: boolean
}): boolean {
  return canHeaderSplit({
    forestEmpty: (opts.forest?.length ?? -1) === 0,
    unlabeledCount: opts.unlabeledWorkingCount,
    llmConfigured: opts.llmConfigured,
  })
}

export function canLeafSplit(opts: { isLeaf: boolean, count: number, llmConfigured: boolean }): boolean {
  return opts.isLeaf && opts.count >= 2 && opts.llmConfigured
}

export function afterSplitHref(sourceId: string | null): string {
  // Unlabeled on, type chip off: placements are proposals until Accept.
  return workbenchHref(sourceId ?? '', { unlabeled: true, labelChipOff: true })
}

export function canHeaderRecycle(opts: {
  forestEmpty: boolean
  unlabeledCount: number
  llmConfigured?: boolean
}): boolean {
  // No LLM: recycle only parks leftovers so leaf-fork can run later.
  return !opts.forestEmpty && opts.unlabeledCount >= 2
}

export function canHeaderRecycleFromState(opts: {
  forest: unknown[] | undefined
  unlabeledWorkingCount: number
}): boolean {
  if (opts.forest === undefined) {
    return false
  }
  return canHeaderRecycle({
    forestEmpty: opts.forest.length === 0,
    unlabeledCount: opts.unlabeledWorkingCount,
  })
}

export function afterRecycleHref(id: string): string {
  return workbenchHref(id, { unlabeled: false, labelChipOff: false })
}
