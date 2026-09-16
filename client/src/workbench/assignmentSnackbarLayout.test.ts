import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const page = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)
const snackbar = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/AssignmentSnackbar.vue'),
  'utf8',
)

describe('assignment snackbar', () => {
  it('is a workbench overlay above Progress and does not navigate after split', () => {
    expect(page.includes('afterSplitHref')).toBe(false)
    expect(page.includes('AssignmentSnackbar')).toBe(true)
    expect(page.includes('assignmentNoticeText')).toBe(true)
    expect(page.includes('snackbarAfterClose')).toBe(true)
    expect(page.includes('privacyNoticeText')).toBe(false)
    expect(snackbar.includes('i-fa6-solid:circle-info')).toBe(true)
    expect(snackbar.includes('bottom-12')).toBe(true)
    expect(snackbar.includes('pointer-events-none')).toBe(true)
  })

  it('uses a destructive icon for error notices', () => {
    expect(snackbar.includes('kind === \'error\'')).toBe(true)
    expect(snackbar.includes('i-fa6-solid:circle-exclamation')).toBe(true)
    expect(page.includes('errorNotice')).toBe(true)
  })
})
