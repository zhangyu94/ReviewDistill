export function commentInspectorKickerHeadings(source: string): string[] {
  const headings: string[] = []
  const openTag = /<h2\b[^>]*>/g
  let match = openTag.exec(source)
  while (match) {
    const start = match.index + match[0].length
    const end = source.indexOf('</h2>', start)
    if (end < 0) {
      break
    }
    headings.push(source.slice(start, end).trim())
    match = openTag.exec(source)
  }
  return headings
}

function indexesOf(headings: string[], names: string[]): number[] {
  return headings.flatMap((heading, index) => (
    names.includes(heading) ? [index] : []
  ))
}

export function typeSectionBetweenContextAndLocation(headings: string[]): boolean {
  const context = headings.indexOf('Manuscript context')
  const location = headings.indexOf('Location')
  if (context < 0 || location <= context) {
    return false
  }
  const typeIndexes = indexesOf(headings, ['Type', 'Assign type'])
  return typeIndexes.length > 0 && typeIndexes.every((index) => index > context && index < location)
}

export function qualitySectionBetweenTypeAndLocation(headings: string[]): boolean {
  const typeIndexes = indexesOf(headings, ['Type', 'Assign type'])
  const quality = headings.indexOf('Quality')
  const location = headings.indexOf('Location')
  if (typeIndexes.length === 0 || quality < 0 || location < 0) {
    return false
  }
  return typeIndexes.every((index) => index < quality) && quality < location
}
