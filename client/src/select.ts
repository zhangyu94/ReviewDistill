/** Next id after an action, using the list from *before* the item is removed. */
export function nextSelectedId(ids: string[], actedId: string): string | undefined {
  if (ids.length === 0) { return undefined }
  const i = ids.indexOf(actedId)
  if (i === -1) { return ids[0] }
  if (i + 1 < ids.length) { return ids[i + 1] }
  if (i > 0) { return ids[i - 1] }
  return undefined
}
