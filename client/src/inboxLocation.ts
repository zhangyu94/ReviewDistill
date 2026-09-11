export interface LocationRow {
  label: string
  value: string
  href: string | null
}

export function safeHttpHref(url: string | null | undefined): string | null {
  if (!url) { return null }
  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') { return url }
  }
  catch {
    return null
  }
  return null
}

export function shortCommit(hash: string | null): string {
  if (!hash) { return '—' }
  return hash.slice(0, 7)
}

export function inboxLocationRows(args: {
  projectName: string
  command: string
  filePath: string
  lineNumber: number
  heading: string | null
  gitUrl: string | null
  gitCommit: string | null
  gitHref: string | null
}): LocationRow[] {
  const rows: LocationRow[] = [
    { label: 'Project', value: args.projectName, href: null },
    { label: 'Command', value: `\\${args.command}`, href: null },
    { label: 'File', value: args.filePath, href: null },
    { label: 'Line', value: String(args.lineNumber), href: null },
  ]
  if (args.heading) { rows.push({ label: 'Heading', value: args.heading, href: null }) }
  if (args.gitUrl) { rows.push({ label: 'Remote', value: args.gitUrl, href: args.gitHref }) }
  if (args.gitCommit) { rows.push({ label: 'Commit', value: shortCommit(args.gitCommit), href: null }) }
  return rows
}
