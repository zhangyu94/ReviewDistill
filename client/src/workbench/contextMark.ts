/** Same window as Python ``offset_is_valid``: integer in 0..text.length, else no mark. */
export type ContextMarkSplit =
  | { marked: true, before: string, after: string }
  | { marked: false, text: string }

export function splitContextMark(
  text: string,
  offset: number | null | undefined,
): ContextMarkSplit {
  if (
    typeof offset !== 'number'
    || !Number.isInteger(offset)
    || offset < 0
    || offset > text.length
  ) {
    return { marked: false, text }
  }
  return { marked: true, before: text.slice(0, offset), after: text.slice(offset) }
}
