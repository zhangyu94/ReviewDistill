export const SETTINGS_PANELS = [
  { id: 'assistant', label: 'Assistant' },
  { id: 'data', label: 'Data' },
] as const

export type SettingsPanelId = typeof SETTINGS_PANELS[number]['id']

export const DEFAULT_SETTINGS_PANEL: SettingsPanelId = 'assistant'

export function settingsPanelOnOpen(): SettingsPanelId {
  return DEFAULT_SETTINGS_PANEL
}

export function showsSettingsSave(panel: SettingsPanelId): boolean {
  return panel === 'assistant'
}

export function settingsErrorMessage(existing: string, err: unknown): string {
  if (existing)
    return existing
  return err instanceof Error ? err.message : String(err)
}
