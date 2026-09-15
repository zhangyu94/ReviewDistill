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

function commentsKeepsWorkbenchErrorsOutOfPanels(panel: string, page: string): boolean {
  const commentsStrip = panel.includes('<p v-if="error" class="ch-error-text px-2 pt-2">')
  const pagePassesErrorToComments = /<EntriesPanel[\s\S]*?:error="error"/.test(page)
  const snackbarGetsErrors = page.includes('setErrorNotice') && page.includes('workbenchSnackbar')
  const actionsDoNotPaintStoreError = !page.includes('error.value = err instanceof Error')
  return !commentsStrip && !pagePassesErrorToComments && snackbarGetsErrors && actionsDoNotPaintStoreError
}

describe('comments panel errors', () => {
  it('keeps workbench action errors out of Comments', () => {
    expect(commentsKeepsWorkbenchErrorsOutOfPanels(panelSource, pageSource)).toBe(true)
  })

  it('keeps a Label Details load error when an action starts', () => {
    const start = pageSource.indexOf('function beginAction')
    const end = pageSource.indexOf('function showActionError')
    const fn = pageSource.slice(start, end)
    expect(fn).toContain('clearErrorNotice')
    expect(fn).not.toContain('error.value = \'\'')
  })

  it('passes labelLoading into Label Details', () => {
    expect(/<LabelInspector[\s\S]*?:loading="labelLoading"/.test(pageSource)).toBe(true)
  })

  it('routes Label Details save refresh errors to the snackbar', () => {
    const start = pageSource.indexOf('async function onLabelUpdated')
    const end = pageSource.indexOf('function onCommentsLayout')
    const fn = pageSource.slice(start, end)
    expect(fn).toContain('showActionError')
    expect(fn).toContain('invalidate')
  })

  it('routes inbox reloads on navigation to the snackbar', () => {
    expect(pageSource).toContain('loadInbox().catch(showActionError)')
  })

  it('does not claim Comments are empty until inbox has loaded', () => {
    expect(pageSource).toContain('loaded: inbox.value != null')
  })
})
