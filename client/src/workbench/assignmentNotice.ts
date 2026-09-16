export function assignmentNoticeText(count: number | undefined): string {
  // Empty on 0 / missing so callers can always set from assigned/labeled.
  // The store ignores empty and keeps the last assignment notice.
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

/** Closing the visible snackbar. An error overlay leaves the assignment underneath. */
export function snackbarAfterClose(
  errorNotice: string,
  assignmentNotice: string,
): { errorNotice: string, assignmentNotice: string } {
  if (errorNotice) {
    return { errorNotice: '', assignmentNotice }
  }
  return { errorNotice: '', assignmentNotice: '' }
}
