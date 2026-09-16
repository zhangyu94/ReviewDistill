export function shouldIgnoreCommentHotkey(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) { return false }
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
    return true
  }
  return target.closest('[role="combobox"], [role="listbox"], [role="menu"]') != null
}
