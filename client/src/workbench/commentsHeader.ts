export function commentsTotalLabel(
  matched: number,
  chips: { unlabeled?: boolean, labelOn?: boolean } = {},
  toDistill = matched,
): string {
  if (chips.unlabeled || chips.labelOn) {
    return `${matched} matching · ${toDistill} to distill`
  }
  return `${toDistill} to distill`
}
