import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const modeSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), './workbenchMode.ts'),
  'utf8',
)
const panelSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/EntriesPanel.vue'),
  'utf8',
)
const rowSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/CommentListRow.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)

function sliceBetween(source: string, startNeedle: string, endNeedle: string): string {
  const start = source.indexOf(startNeedle)
  const end = source.indexOf(endNeedle, start + startNeedle.length)
  if (start < 0 || end < 0) { return '' }
  return source.slice(start, end)
}

function layoutGroup(source: string): string {
  return sliceBetween(source, 'aria-label="Comment layout"', 'ml-auto')
}

function treeBlock(source: string): string {
  return sliceBetween(source, 'v-else-if="layout === \'tree\'"', 'v-else class="flex min-h-0 flex-1 flex-col"')
}

function oneBlock(source: string): string {
  const start = source.indexOf('v-else class="flex min-h-0 flex-1 flex-col"')
  if (start < 0) { return '' }
  return source.slice(start)
}

describe('comments tree layout', () => {
  it('adds tree between list and one in the layout type', () => {
    expect(modeSource).toContain('export type CommentsLayout = \'list\' | \'tree\' | \'one\'')
  })

  it('places the tree button between list and one', () => {
    const group = layoutGroup(panelSource)
    const list = group.indexOf('i-fa6-solid:list')
    const tree = group.indexOf('i-fa6-solid:folder-tree')
    const one = group.indexOf('i-fa6-regular:square')
    expect(list).toBeGreaterThanOrEqual(0)
    expect(tree).toBeGreaterThan(list)
    expect(one).toBeGreaterThan(tree)
    expect(group).toContain('emit(\'update:layout\', \'tree\')')
    expect(group).toContain('Show comments in a project file tree')
    expect(group).toContain(':aria-pressed="layout === \'tree\'"')
  })

  it('scans the tree without pagination', () => {
    const tree = treeBlock(panelSource)
    expect(panelSource).toContain('flattenCommentTree')
    expect(panelSource).toContain('commentTree(')
    expect(tree).toContain('treeRows')
    expect(tree).toContain('CommentListRow')
    expect(tree).not.toContain('CommentPagination')
    expect(oneBlock(panelSource)).toContain('CommentPagination')
  })

  it('toggles group rows without selecting them as comments', () => {
    const tree = treeBlock(panelSource)
    expect(tree).toContain('toggleCollapsed')
    expect(tree).toContain('row.kind === \'group\'')
    expect(tree).not.toMatch(/@click="emit\('select', row\.id\)"/)
    expect(tree).not.toContain('draggable')
  })

  it('reuses comment cards in the tree with line location and indent', () => {
    const tree = treeBlock(panelSource)
    expect(tree).toContain('location="line"')
    expect(tree).toContain('row.depth')
    expect(rowSource).toContain('location?: \'full\' | \'line\'')
    expect(rowSource).toContain('commentListLocationLabel')
  })

  it('reveals the tree file path, not the line', () => {
    const tree = treeBlock(panelSource)
    expect(tree).toContain('row.revealId')
    expect(tree).toContain('fileRevealAccessibleName(row.name)')
    expect(tree).toContain('emit(\'reveal\', row.revealId)')
    expect(rowSource).toContain('v-if="location !== \'line\'"')
  })

  it('walks visible tree order with j and k', () => {
    expect(pageSource).toContain('adjacentVisibleCommentId')
    expect(pageSource).toContain('commentsLayout.value === \'tree\'')
    expect(pageSource).toContain('expandAncestors')
    expect(pageSource).toContain('shouldIgnoreCommentHotkey')
    expect(panelSource).toContain('update:collapsed')
  })

  it('keeps a collapsed group collapsed even when it holds the open comment', () => {
    const start = pageSource.indexOf('function onCommentTreeCollapsed')
    const end = pageSource.indexOf('function onKey', start)
    const fn = start >= 0 && end > start ? pageSource.slice(start, end) : ''
    expect(fn).toContain('selectedIdAfterTreeCollapse')
    expect(fn).not.toContain('expandAncestors')
  })
})
