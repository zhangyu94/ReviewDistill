import { describe, expect, it } from 'vitest'
import {
  DEFAULT_SETTINGS_PANEL,
  SETTINGS_PANELS,
  settingsErrorMessage,
  settingsPanelOnOpen,
  showsSettingsSave,
} from './settingsPanels.ts'

describe('settingsPanels', () => {
  it('lists Assistant then Data', () => {
    expect(SETTINGS_PANELS.map(row => row.id)).toEqual(['assistant', 'data'])
    expect(SETTINGS_PANELS.map(row => row.label)).toEqual(['Assistant', 'Data'])
  })

  it('opens on Assistant', () => {
    expect(DEFAULT_SETTINGS_PANEL).toBe('assistant')
    expect(settingsPanelOnOpen()).toBe('assistant')
  })

  it('shows Save only on Assistant', () => {
    expect(showsSettingsSave('assistant')).toBe(true)
    expect(showsSettingsSave('data')).toBe(false)
  })

  it('keeps an existing settings error', () => {
    expect(settingsErrorMessage('first', new Error('second'))).toBe('first')
  })

  it('uses the new error when none is set', () => {
    expect(settingsErrorMessage('', new Error('paths failed'))).toBe('paths failed')
    expect(settingsErrorMessage('', 'plain')).toBe('plain')
  })
})
