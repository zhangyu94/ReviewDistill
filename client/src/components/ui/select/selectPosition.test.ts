import { describe, expect, it } from 'vitest'
import { SELECT_CONTENT_POSITION, SELECT_CONTENT_SIDE_OFFSET } from './selectPosition.ts'

describe('select menu position', () => {
  it('places the list below the trigger instead of overlaying it', () => {
    expect(SELECT_CONTENT_POSITION).toBe('popper')
    expect(SELECT_CONTENT_SIDE_OFFSET).toBe(4)
  })
})
