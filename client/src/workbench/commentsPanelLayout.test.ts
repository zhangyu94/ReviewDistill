import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const panelSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/EntriesPanel.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)

function commentsErrorPaddingIsShared(panel: string, page: string): boolean {
  const errorMark = '<p v-if="error" class="ch-error-text px-2 pt-2">'
  const errorAt = panel.indexOf(errorMark)
  const listBranch = panel.indexOf('v-if="layout === \'list\'"')
  const slotDuplicate = page.includes('class="ch-error-text mb-3"')
  return errorAt >= 0 && listBranch > errorAt && !slotDuplicate
}

describe('comments panel errors', () => {
  it('uses one px-2 strip for list and one-comment layouts', () => {
    expect(commentsErrorPaddingIsShared(panelSource, pageSource)).toBe(true)
  })
})
