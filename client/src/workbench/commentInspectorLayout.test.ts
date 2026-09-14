import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  commentInspectorKickerHeadings,
  qualitySectionBetweenTypeAndLocation,
  typeSectionBetweenContextAndLocation,
} from './commentInspectorLayout.ts'

const inspectorSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/CommentInspector.vue'),
  'utf8',
)

describe('comment inspector body order', () => {
  it('places type then quality between manuscript context and location', () => {
    const headings = commentInspectorKickerHeadings(inspectorSource)
    expect(typeSectionBetweenContextAndLocation(headings)).toBe(true)
    expect(qualitySectionBetweenTypeAndLocation(headings)).toBe(true)
  })
})
