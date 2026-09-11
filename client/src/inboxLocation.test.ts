import { describe, expect, it } from 'vitest'
import { inboxLocationRows, safeHttpHref } from './inboxLocation.ts'

const base = {
  projectName: 'paper-01',
  command: 'myremark',
  filePath: 'sections/methods.tex',
  lineNumber: 20,
  heading: 'paper-01 / Methods',
  gitUrl: 'https://git@git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaa',
  gitCommit: 'abc1234def456',
  gitHref: 'https://git@git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaa',
}

describe('inboxLocationRows', () => {
  it('labels each location field instead of concatenating them', () => {
    const rows = inboxLocationRows(base)
    expect(rows.map((row) => row.label)).toEqual([
      'Project',
      'Command',
      'File',
      'Line',
      'Heading',
      'Remote',
      'Commit',
    ])
    expect(rows.map((row) => row.value)).toEqual([
      'paper-01',
      '\\myremark',
      'sections/methods.tex',
      '20',
      'paper-01 / Methods',
      'https://git@git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaa',
      'abc1234',
    ])
    expect(rows.find((row) => row.label === 'Remote')?.href).toBe(base.gitHref)
  })

  it('omits heading, remote, and commit when they are missing', () => {
    const rows = inboxLocationRows({
      ...base,
      heading: null,
      gitUrl: null,
      gitCommit: null,
      gitHref: null,
    })
    expect(rows.map((row) => row.label)).toEqual(['Project', 'Command', 'File', 'Line'])
  })
})

describe('safeHttpHref', () => {
  it('allows http and https only', () => {
    expect(safeHttpHref('https://github.com/ex/paper')).toBe('https://github.com/ex/paper')
    expect(safeHttpHref('http://localhost:8765')).toBe('http://localhost:8765')
    expect(safeHttpHref('javascript:alert(1)')).toBeNull()
    expect(safeHttpHref('data:text/html,hi')).toBeNull()
    expect(safeHttpHref(null)).toBeNull()
  })
})
