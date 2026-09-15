import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const panelSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/LabelsPanel.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)

function labelsPanelUsesLabelerActionIcons(source: string): boolean {
  return source.includes('i-fa6-solid:code-fork')
    && source.includes('i-fa6-solid:plus')
    && source.includes('i-fa6-solid:code-merge')
    && source.includes('i-fa6-solid:trash')
    && source.includes('i-fa6-solid:recycle')
}

function labelsPanelHeaderOrderIsForkPlusRecycle(source: string): boolean {
  const fork = source.indexOf('i-fa6-solid:code-fork')
  const plus = source.indexOf('i-fa6-solid:plus')
  const recycle = source.indexOf('i-fa6-solid:recycle')
  return fork >= 0 && plus > fork && recycle > plus
}

function workbenchPostsRecycle(source: string): boolean {
  return source.includes('recycleUngrouped')
    && source.includes('afterRecycleHref')
    && source.includes('@recycle="onRecycleUngrouped"')
}

describe('label taxonomy tree actions', () => {
  it('uses the image taxonomy labeler icons', () => {
    expect(labelsPanelUsesLabelerActionIcons(panelSource)).toBe(true)
    expect(labelsPanelHeaderOrderIsForkPlusRecycle(panelSource)).toBe(true)
  })

  it('posts recycle from the workbench page', () => {
    expect(workbenchPostsRecycle(pageSource)).toBe(true)
  })
})
