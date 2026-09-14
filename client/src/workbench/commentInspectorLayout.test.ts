import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  commentInspectorKickerHeadings,
  inspectorFileRevealUsesButton,
  qualitySectionBetweenTypeAndLocation,
  typeSectionBetweenContextAndLocation,
} from './commentInspectorLayout.ts'

const inspectorSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/CommentInspector.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)

describe('comment inspector body order', () => {
  it('places type then quality between manuscript context and location', () => {
    const headings = commentInspectorKickerHeadings(inspectorSource)
    expect(typeSectionBetweenContextAndLocation(headings)).toBe(true)
    expect(qualitySectionBetweenTypeAndLocation(headings)).toBe(true)
  })

  it('reveals File with a button, not a file URL', () => {
    expect(inspectorFileRevealUsesButton(inspectorSource)).toBe(true)
  })

  it('posts reveal from the workbench page', () => {
    expect(pageSource.includes('revealInboxFile')).toBe(true)
    expect(pageSource.includes('@reveal="revealFile"')).toBe(true)
  })
})
