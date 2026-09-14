export interface LocationRow {
  label: string
  value: string
  href: string | null
  reveal: boolean
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

export function fileRevealLabel(): string {
  return 'Show this file on this computer'
}

export function fileRevealAccessibleName(filePath: string): string {
  return `${fileRevealLabel()}: ${filePath}`
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
  localFile: boolean
}): LocationRow[] {
  const rows: LocationRow[] = [
    { label: 'Project', value: args.projectName, href: null, reveal: false },
    { label: 'Command', value: `\\${args.command}`, href: null, reveal: false },
    // File uses reveal, not href: browsers block file:// from http://127.0.0.1.
    { label: 'File', value: args.filePath, href: null, reveal: args.localFile },
    { label: 'Line', value: String(args.lineNumber), href: null, reveal: false },
  ]
  if (args.heading) { rows.push({ label: 'Heading', value: args.heading, href: null, reveal: false }) }
  if (args.gitUrl) { rows.push({ label: 'Remote', value: args.gitUrl, href: args.gitHref, reveal: false }) }
  if (args.gitCommit) { rows.push({ label: 'Commit', value: shortCommit(args.gitCommit), href: null, reveal: false }) }
  return rows
}
