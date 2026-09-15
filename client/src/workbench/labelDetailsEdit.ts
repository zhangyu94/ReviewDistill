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

export function labelDetailsErrorText(saveError: string, loadError: string): string {
  return saveError.trim() ? saveError : loadError
}

export function nextLabelSaveError(opts: { keepDraft: boolean, current: string }): string {
  return opts.keepDraft ? opts.current : ''
}
