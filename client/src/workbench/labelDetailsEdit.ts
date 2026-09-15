export function canShowLabelEdit(opts: {
  selectedId: string
  missing: boolean
  label: { id: string } | null
}): boolean {
  return Boolean(opts.selectedId) && !opts.missing && opts.label != null
}

export function canSaveLabelEdit(name: string, definition: string): boolean {
  return Boolean(name.trim() && definition.trim())
}

export type LabelEditCall
  = | { kind: 'rename', name: string }
    | { kind: 'edit', definition: string }

export function labelEditSaves(opts: {
  currentName: string
  currentDefinition: string
  nextName: string
  nextDefinition: string
}): LabelEditCall[] {
  // Keep rename and edit as separate POSTs; one Save may run both.
  const name = opts.nextName.trim()
  const definition = opts.nextDefinition.trim()
  const calls: LabelEditCall[] = []
  if (name !== opts.currentName) {
    calls.push({ kind: 'rename', name })
  }
  if (definition !== opts.currentDefinition) {
    calls.push({ kind: 'edit', definition })
  }
  return calls
}

export function shouldReloadAfterLabelSaves(completedCount: number): boolean {
  return completedCount > 0
}

export function shouldSyncLabelEditFromProps(saving: boolean): boolean {
  return !saving
}

export function labelDetailsErrorText(saveError: string, loadError: string, loading = false): string {
  if (saveError.trim()) {
    return saveError
  }
  if (loading) {
    return ''
  }
  return loadError
}

export function labelDetailsEmptyCopy(opts: {
  selectedId: string
  missing: boolean
  hasLabel: boolean
  loading: boolean
  hasError: boolean
}): string {
  if (!opts.selectedId) {
    return 'Select a label.'
  }
  if (opts.loading) {
    return ''
  }
  if (opts.missing) {
    return 'This label was not found.'
  }
  if (opts.hasLabel || opts.hasError) {
    return ''
  }
  return 'Couldn\'t load this label.'
}

export function nextLabelSaveError(opts: { keepDraft: boolean, current: string }): string {
  return opts.keepDraft ? opts.current : ''
}
