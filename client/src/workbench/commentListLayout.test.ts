import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const rowSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/CommentListRow.vue'),
  'utf8',
)
const panelSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../components/workbench/EntriesPanel.vue'),
  'utf8',
)
const pageSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../pages/WorkbenchPage.vue'),
  'utf8',
)

function listBlock(source: string): string {
  const start = source.indexOf('v-if="layout === \'list\'"')
  const oneAt = source.indexOf('v-else')
  if (start < 0 || oneAt < 0 || oneAt <= start) {
    return ''
  }
  return source.slice(start, oneAt)
}

describe('comments list row', () => {
  it('does not wrap the row in a single button', () => {
    expect(rowSource).not.toMatch(/<button[\s\S]*v-for="item in items"/)
    expect(listBlock(panelSource)).not.toMatch(/<button[\s\S]*v-for="item in items"/)
    expect(listBlock(panelSource)).toContain('<CommentListRow')
  })

  it('selects and drags from the comment text, not the card', () => {
    expect(rowSource).toContain('emit(\'select\', item.comment.id)')
    expect(rowSource).toMatch(
      /<button[\s\S]*:draggable="!item.labeled"[\s\S]*line-clamp-2/,
    )
    const cardOpen = rowSource.slice(rowSource.indexOf('<div'), rowSource.indexOf('<button'))
    expect(cardOpen).not.toContain('draggable')
  })

  it('reveals the file path, not the line', () => {
    expect(rowSource).toContain('item.local_file')
    expect(rowSource).toContain('item.project_name')
    expect(rowSource).toContain('item.comment.file_path')
    expect(rowSource).toContain('commentListLocationLabel')
    expect(rowSource).toContain('fileRevealAccessibleName(item.comment.file_path)')
    expect(rowSource).toContain('fileRevealLabel()')
    expect(rowSource).toContain('emit(\'reveal\', item.comment.id)')
    expect(rowSource).not.toContain('file://')
    const locationLine = rowSource.slice(rowSource.indexOf('ch-muted-text mt-0.5'))
    const reveal = locationLine.slice(
      locationLine.indexOf('v-if="item.local_file"'),
      locationLine.indexOf('</button>'),
    )
    expect(reveal).toContain('item.comment.file_path')
    expect(reveal).not.toContain('locationLabel')
    expect(locationLine).toMatch(/<\/button>[\s\S]*locationLabel/)
  })

  it('assigns from a leaf Select on every row', () => {
    expect(rowSource).toContain('assignableLabelRows')
    expect(rowSource).toContain('shouldAssignOnSelect')
    expect(rowSource).toContain('emit(\'assign\', props.item.comment.id, value)')
    expect(rowSource).toContain('Choose a label…')
    expect(rowSource).toContain('No labels yet. Accept a new-label suggestion first.')
  })

  it('keeps the list label menu as compact chrome', () => {
    expect(rowSource).toContain('SelectTrigger class="h-6 w-auto max-w-full"')
    expect(rowSource).toMatch(/<\/div>\s*<div class="mt-0.5 flex min-w-0 items-center gap-1.5">[\s\S]*<span class="ch-muted-text shrink-0">Label<\/span>[\s\S]*<Select/)
  })

  it('forwards assign and reveal from the list panel', () => {
    expect(panelSource).toContain('emit(\'assign\'')
    expect(panelSource).toContain('emit(\'reveal\'')
  })

  it('forwards assign and reveal from the list to the workbench', () => {
    expect(pageSource).toContain('@assign="change"')
    expect(pageSource).toContain('@reveal="revealFile"')
    expect(pageSource).toContain('selectedIdAfterListAssign')
    expect(pageSource).toMatch(/async function change\(\s*commentId: string,\s*nextLabelId: string/)
    expect(pageSource).toMatch(/async function revealFile\(\s*commentId: string/)
  })

  it('uses the list-assign selection rule for drag onto a leaf', () => {
    const start = pageSource.indexOf('if (action.type === \'change\')')
    const end = pageSource.indexOf('if (action.type === \'merge\')', start)
    const dropChange = start >= 0 && end > start ? pageSource.slice(start, end) : ''
    expect(dropChange).toContain('selectedIdAfterListAssign')
    expect(dropChange).not.toContain('selectedIdAfterAction')
  })
})
