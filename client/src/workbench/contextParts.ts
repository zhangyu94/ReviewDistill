export function splitContextText(raw: string): { prose: string, extras: string } {
  if (!raw) { return { prose: '', extras: '' } }
  const lines = raw.split('\n')
  const last = lines[lines.length - 1] ?? ''
  if (last.startsWith('Citations:') || last.startsWith('Refs:')) { return { prose: lines.slice(0, -1).join('\n'), extras: last } }
  return { prose: raw, extras: '' }
}
