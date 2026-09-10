export function acceptTooltip(hasProposal: boolean): string {
  if (hasProposal) {
    return "Apply the AI suggestion. If it proposed a new issue type, that type is added to the taxonomy and this comment becomes an example."
  }
  return "No AI suggestion yet. Use Get AI suggestions first."
}

export function rejectTooltip(): string {
  return "Do not assign this comment to any issue type. It leaves Uncoded; the observation stays in history."
}

export function changeTooltip(hasIssues: boolean): string {
  if (hasIssues) {
    return "Assign this comment to the issue type chosen in the dropdown, instead of the AI suggestion."
  }
  return "No issue types yet. Accept a new-issue suggestion first."
}

export function keepTooltip(): string {
  return "Keep this observation in the working dataset even though the comment is gone from the source."
}

export function retractTooltip(): string {
  return "Drop this observation from the working dataset. History is kept; it is not used for coding, clustering, or export."
}
