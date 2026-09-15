import { describe, expect, it } from 'vitest'
import { splitContextMark } from './contextMark.ts'

describe('splitContextMark', () => {
  it('splits at a valid offset', () => {
    expect(splitContextMark('Hello world', 5)).toEqual({
      marked: true,
      before: 'Hello',
      after: ' world',
    })
  })

  it('returns unmarked text when the offset is missing or out of range', () => {
    expect(splitContextMark('Hello', null)).toEqual({ marked: false, text: 'Hello' })
    expect(splitContextMark('Hello', 6)).toEqual({ marked: false, text: 'Hello' })
    expect(splitContextMark('Hello', -1)).toEqual({ marked: false, text: 'Hello' })
  })
})
