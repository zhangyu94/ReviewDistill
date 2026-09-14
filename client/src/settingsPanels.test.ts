import { describe, expect, it } from 'vitest'
import { settingsErrorMessage } from './settingsPanels.ts'

describe('settingsPanels', () => {
  it('keeps an existing settings error', () => {
    expect(settingsErrorMessage('first', new Error('second'))).toBe('first')
  })

  it('uses the new error when none is set', () => {
    expect(settingsErrorMessage('', new Error('paths failed'))).toBe('paths failed')
    expect(settingsErrorMessage('', 'plain')).toBe('plain')
  })
})
