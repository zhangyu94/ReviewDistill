export function commentsTotalLabel(
  matched: number,
  chips: { unlabeled?: boolean, typeOn?: boolean } = {},
  toDistill = matched,
): string {
  if (chips.unlabeled || chips.typeOn) {
    return `${matched} matching · ${toDistill} to distill`
  }
  return `${toDistill} to distill`
}
