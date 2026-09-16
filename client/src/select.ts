/** Next id after an action, using the list from *before* the item is removed. */
export function nextSelectedId(ids: string[], actedId: string): string | undefined {
  if (ids.length === 0) { return undefined }
  const i = ids.indexOf(actedId)
  if (i === -1) { return ids[0] }
  if (i + 1 < ids.length) { return ids[i + 1] }
  if (i > 0) { return ids[i - 1] }
  return undefined
}

/** Keep the acted row when it is still in the list after reload. */
export function selectedIdAfterAction(
  idsBefore: string[],
  actedId: string,
  idsAfter: string[],
): string | undefined {
  if (idsAfter.includes(actedId)) { return actedId }
  return nextSelectedId(idsBefore, actedId)
}

/** After a list assign (the acted row may not be the open comment): keep the acted row if it remains; if it left, keep the current row when it remains; else same as selectedIdAfterAction. */
export function selectedIdAfterListAssign(
  idsBefore: string[],
  actedId: string,
  idsAfter: string[],
  currentId: string | undefined,
): string | undefined {
  if (idsAfter.includes(actedId)) {
    return actedId
  }
  if (currentId && idsAfter.includes(currentId)) {
    return currentId
  }
  return selectedIdAfterAction(idsBefore, actedId, idsAfter)
}
