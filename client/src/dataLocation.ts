export function folderFileUrl(home: string): string {
  const trimmed = home.trim()
  if (!trimmed) {
    return ''
  }
  const unix = trimmed.replace(/\\/g, '/')
  const withSlash = unix.startsWith('/') ? unix : `/${unix}`
  return `file://${encodeURI(withSlash)}`
}

export function canSaveDataPath(args: { draft: string, saved: string }): boolean {
  const draft = args.draft.trim()
  if (!draft) {
    return false
  }
  return draft !== args.saved.trim()
}
