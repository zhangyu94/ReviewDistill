import type { CodingJson, IssueOption } from '../api/client.ts'

export interface AssignSuggestion {
  title: string
  rationale: string | null
}

/** Stored proposal if usable. An unresolved existing type id is not a suggestion. */
export function assignSuggestion(
  coding: CodingJson | null | undefined,
  issues: Pick<IssueOption, 'id' | 'name'>[],
): AssignSuggestion | null {
  if (!coding) { return null }
  if (coding.kind === 'new') {
    const name = coding.proposed_issue_name?.trim()
    if (!name) { return null }
    return {
      title: `New: ${name}`,
      rationale: coding.rationale,
    }
  }
  const match = issues.find((row) => row.id === coding.issue_type_id)
  if (!match) { return null }
  return { title: match.name, rationale: coding.rationale }
}

export function shouldAssignOnSelect(
  currentTypeId: string | null | undefined,
  selectedId: string,
): boolean {
  return Boolean(selectedId) && selectedId !== (currentTypeId ?? '')
}
