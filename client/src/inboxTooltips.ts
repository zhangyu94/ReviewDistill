export function acceptTooltip(hasProposal: boolean): string {
  if (hasProposal) {
    return 'Apply the AI suggestion. If it proposed a new issue type, that type is added to the taxonomy and this comment becomes an example.'
  }
  return 'No AI suggestion yet. Use Label with AI first.'
}

export function changeTooltip(hasIssues: boolean): string {
  if (hasIssues) {
    return 'Assign this comment to the issue type chosen in the dropdown.'
  }
  return 'No issue types yet. Accept a new-issue suggestion first.'
}

export function verifyTooltip(): string {
  return 'This observation is quality-assured (wording, context, worth keeping as evidence). Does not confirm the issue type.'
}

export function dropTooltip(): string {
  return 'Do not distill this observation (too local, or a bad extract). History is kept.'
}
