import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const inspectorSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/CommentInspector.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)
const progressSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/ProgressBar.vue'),
  'utf8',
)
const unoSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../uno.config.ts'),
  'utf8',
)

function commentInspectorKickerHeadings(source: string): string[] {
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

function labelSectionBetweenContextAndLocation(headings: string[]): boolean {
  const context = headings.indexOf('Manuscript context')
  const location = headings.indexOf('Location')
  if (context < 0 || location <= context) {
    return false
  }
  const labelIndexes = indexesOf(headings, ['Label', 'Assign label'])
  return labelIndexes.length > 0 && labelIndexes.every((index) => index > context && index < location)
}

function triageSectionBetweenLabelAndLocation(headings: string[]): boolean {
  const labelIndexes = indexesOf(headings, ['Label', 'Assign label'])
  const triage = headings.indexOf('Triage')
  const location = headings.indexOf('Location')
  if (labelIndexes.length === 0 || triage < 0 || location < 0) {
    return false
  }
  return labelIndexes.every((index) => index < triage) && triage < location
}

function triageButtonsUseLockAndBinIcons(source: string): boolean {
  return source.includes('\'i-fa6-solid:lock\'')
    && source.includes('i-fa6-solid:lock-open')
    && source.includes('i-fa6-solid:trash-can')
}

function verifyButtonIsToggle(source: string): boolean {
  const emitAt = source.indexOf('emit(\'verify\')')
  const start = source.lastIndexOf('<button', emitAt)
  const verifyBlock = source.slice(start, emitAt)
  return verifyBlock.includes('aria-pressed')
    && verifyBlock.includes('ch-btn-outline')
    && !verifyBlock.includes('ch-btn-default')
    && !verifyBlock.includes(':disabled')
}

function deleteButtonDisabledWhenVerified(source: string): boolean {
  const emitAt = source.indexOf('emit(\'delete\')')
  const start = source.lastIndexOf('<button', emitAt)
  const deleteBlock = source.slice(start, emitAt)
  return deleteBlock.includes(':disabled="selected.comment.verified"')
}

function inspectorFileRevealUsesButton(source: string): boolean {
  return source.includes('row.reveal')
    && source.includes('type="button"')
    && source.includes('fileRevealAccessibleName(row.value)')
    && source.includes('emit(\'reveal\')')
}

function manuscriptContextLegendIsParenthetical(source: string): boolean {
  const headingAt = source.indexOf('Manuscript context')
  if (headingAt < 0) {
    return false
  }
  const sectionStart = source.lastIndexOf('<section', headingAt)
  const sectionEnd = source.indexOf('</section>', headingAt)
  if (sectionStart < 0 || sectionEnd < 0) {
    return false
  }
  const section = source.slice(sectionStart, sectionEnd)
  const localHeading = section.indexOf('Manuscript context')
  const rowStart = section.lastIndexOf('<div', localHeading)
  const rowEnd = section.indexOf('</div>', localHeading)
  if (rowStart < 0 || rowEnd < 0) {
    return false
  }
  const row = section.slice(rowStart, rowEnd)
  return row.includes('ch-kicker')
    && row.includes('ch-context-mark')
    && /\([\s\S]*Comment sat here\s*\)/.test(row)
}

describe('comment inspector body order', () => {
  it('places label then triage between manuscript context and location', () => {
    const headings = commentInspectorKickerHeadings(inspectorSource)
    expect(labelSectionBetweenContextAndLocation(headings)).toBe(true)
    expect(triageSectionBetweenLabelAndLocation(headings)).toBe(true)
  })

  it('puts a lock on Verify, an unlocked lock when off, and a bin on Delete', () => {
    expect(triageButtonsUseLockAndBinIcons(inspectorSource)).toBe(true)
  })

  it('treats Verify as a protect toggle and disables Delete when verified', () => {
    expect(verifyButtonIsToggle(inspectorSource)).toBe(true)
    expect(deleteButtonDisabledWhenVerified(inspectorSource)).toBe(true)
  })

  it('reveals File with a button, not a file URL', () => {
    expect(inspectorFileRevealUsesButton(inspectorSource)).toBe(true)
  })

  it('posts reveal from the workbench page', () => {
    expect(pageSource.includes('revealInboxFile')).toBe(true)
    expect(pageSource.includes('@reveal="revealSelected"')).toBe(true)
  })

  it('shows a square insertion mark and a matching legend', () => {
    expect(unoSource).toMatch(/['"]ch-context-mark['"],\s*'[^']*h-2\.5[^']*w-2\.5[^']*'/)
    expect(inspectorSource.match(/ch-context-mark/g)?.length).toBeGreaterThanOrEqual(2)
    expect(inspectorSource).toContain('Comment sat here')
    expect(manuscriptContextLegendIsParenthetical(inspectorSource)).toBe(true)
  })

  it('explains unlabeled and verified without treating Verify as a label assignment', () => {
    expect(progressSource).toContain(
      'The number of comments to distill that have no label. The Unlabeled chip is the inbox queue, not this count.',
    )
    expect(progressSource).toContain(
      'The number of comments that are verified. Does not confirm the label assignment.',
    )
    expect(inspectorSource).toContain('Stamp this observation as verified')
  })
})
