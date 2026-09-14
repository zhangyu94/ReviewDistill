export function canShowIssueEdit(opts: {
  selectedId: string
  missing: boolean
  issue: { id: string } | null
}): boolean {
  return Boolean(opts.selectedId) && !opts.missing && opts.issue != null
}

export function canSaveIssueEdit(name: string, definition: string): boolean {
  return Boolean(name.trim() && definition.trim())
}

export type IssueEditCall
  = | { kind: 'rename', name: string }
    | { kind: 'edit', definition: string }

export function issueEditSaves(opts: {
  currentName: string
  currentDefinition: string
  nextName: string
  nextDefinition: string
}): IssueEditCall[] {
  // Keep rename and edit as separate POSTs; one Save may run both.
  const name = opts.nextName.trim()
  const definition = opts.nextDefinition.trim()
  const calls: IssueEditCall[] = []
  if (name !== opts.currentName) {
    calls.push({ kind: 'rename', name })
  }
  if (definition !== opts.currentDefinition) {
    calls.push({ kind: 'edit', definition })
  }
  return calls
}

export function shouldReloadAfterIssueSaves(completedCount: number): boolean {
  return completedCount > 0
}

export function shouldSyncIssueEditFromProps(saving: boolean): boolean {
  return !saving
}

export function issueDetailsErrorText(saveError: string, loadError: string): string {
  return saveError.trim() ? saveError : loadError
}

export function nextIssueSaveError(opts: { keepDraft: boolean, current: string }): string {
  return opts.keepDraft ? opts.current : ''
}
