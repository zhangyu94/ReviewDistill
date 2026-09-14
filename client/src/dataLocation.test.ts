import { describe, expect, it } from 'vitest'
import { canSaveDataPath, folderFileUrl } from './dataLocation.ts'

describe('dataLocation', () => {
  it('builds a file URL for a Unix folder', () => {
    expect(folderFileUrl('/Users/yuzhang/projects/review-skill')).toBe(
      'file:///Users/yuzhang/projects/review-skill',
    )
  })

  it('encodes spaces in the file URL', () => {
    expect(folderFileUrl('/Users/My Folder/data')).toBe('file:///Users/My%20Folder/data')
  })

  it('builds a file URL for a Windows folder', () => {
    expect(folderFileUrl('C:\\Users\\me\\data')).toBe('file:///C:/Users/me/data')
  })

  it('returns an empty file URL when the path is blank', () => {
    expect(folderFileUrl('')).toBe('')
    expect(folderFileUrl('   ')).toBe('')
  })

  it('allows Save when the draft folder differs from the saved one', () => {
    expect(canSaveDataPath({ draft: '/new/home', saved: '/old/home' })).toBe(true)
  })

  it('blocks Save when the draft is blank or unchanged', () => {
    expect(canSaveDataPath({ draft: '', saved: '/old/home' })).toBe(false)
    expect(canSaveDataPath({ draft: '   ', saved: '/old/home' })).toBe(false)
    expect(canSaveDataPath({ draft: '/old/home', saved: '/old/home' })).toBe(false)
    expect(canSaveDataPath({ draft: ' /old/home ', saved: '/old/home' })).toBe(false)
  })
})
