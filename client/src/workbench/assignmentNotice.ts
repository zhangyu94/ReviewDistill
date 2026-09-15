export function assignmentNoticeText(count: number | undefined): string {
  if (!Number.isFinite(count) || (count as number) < 1) { return '' }
  if (count === 1) {
    return '1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.'
  }
  return `${count} comments were labeled. They appear in Label Taxonomy. Change any that are wrong.`
}

export type WorkbenchSnackbarKind = 'info' | 'error'

export function workbenchSnackbar(
  errorNotice: string,
  assignmentNotice: string,
): { text: string, kind: WorkbenchSnackbarKind } {
  if (errorNotice) {
    return { text: errorNotice, kind: 'error' }
  }
  return { text: assignmentNotice, kind: 'info' }
}
