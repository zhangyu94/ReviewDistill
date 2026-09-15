import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const historySource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/HistoryDialog.vue'),
  'utf8',
)

function historyErrorParagraph(source: string): string {
  const start = source.indexOf('<p v-if="error"')
  if (start < 0) {
    return ''
  }
  const end = source.indexOf('</p>', start)
  return source.slice(start, end)
}

describe('history dialog errors', () => {
  it('uses error text for load and undo failures', () => {
    const block = historyErrorParagraph(historySource)
    expect(block).toContain('ch-error-text')
  })
})
