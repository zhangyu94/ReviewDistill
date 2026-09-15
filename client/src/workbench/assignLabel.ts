import type { CodingJson, LabelOption } from '../api/client.ts'

export interface AssignSuggestion {
  title: string
  rationale: string | null
}

/** Stored proposal if usable. An unresolved existing type id is not a suggestion. */
export function assignSuggestion(
  coding: CodingJson | null | undefined,
  labels: Pick<LabelOption, 'id' | 'name'>[],
): AssignSuggestion | null {
  if (!coding) { return null }
  if (coding.kind === 'new') {
    const name = coding.proposed_label_name?.trim()
    if (!name) { return null }
    return {
      title: `New: ${name}`,
      rationale: coding.rationale,
    }
  }
  const match = labels.find((row) => row.id === coding.label_id)
  if (!match) { return null }
  return { title: match.name, rationale: coding.rationale }
}

export function shouldAssignOnSelect(
  currentLabelId: string | null | undefined,
  selectedId: string,
): boolean {
  return Boolean(selectedId) && selectedId !== (currentLabelId ?? '')
}
