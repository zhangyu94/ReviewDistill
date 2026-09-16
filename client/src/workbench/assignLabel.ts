import type { AssignmentJson, LabelOption } from '../api/client.ts'

export interface AssignSuggestion {
  title: string
  rationale: string | null
}

/** Stored proposal if usable. An unresolved existing type id is not a suggestion. */
export function assignSuggestion(
  assignment: AssignmentJson | null | undefined,
  labels: Pick<LabelOption, 'id' | 'name'>[],
): AssignSuggestion | null {
  if (!assignment) { return null }
  if (assignment.kind === 'new') {
    const name = assignment.proposed_label_name?.trim()
    if (!name) { return null }
    return {
      title: `New: ${name}`,
      rationale: assignment.rationale,
    }
  }
  const match = labels.find((row) => row.id === assignment.label_id)
  if (!match) { return null }
  return { title: match.name, rationale: assignment.rationale }
}

export function shouldAssignOnSelect(
  currentLabelId: string | null | undefined,
  selectedId: string,
): boolean {
  return Boolean(selectedId) && selectedId !== (currentLabelId ?? '')
}
