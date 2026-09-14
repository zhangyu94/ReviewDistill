import { describe, expect, it } from 'vitest'
import { apiKeyForSelectedProvider, canSaveLlmSettings, keySetForSelectedProvider, privacyNoticeText } from './llmSettings.ts'

describe('llmSettings', () => {
  it('requires a provider and a key unless one is already set', () => {
    expect(canSaveLlmSettings({ provider: '', apiKey: 'sk', keySet: false })).toBe(false)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: '', keySet: false })).toBe(false)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: '', keySet: true })).toBe(true)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: 'sk', keySet: false })).toBe(true)
  })

  it('treats a key as set only for the provider that was saved', () => {
    expect(keySetForSelectedProvider('openai', 'deepseek', true)).toBe(false)
    expect(keySetForSelectedProvider('deepseek', 'deepseek', true)).toBe(true)
    expect(keySetForSelectedProvider('deepseek', 'deepseek', false)).toBe(false)
  })

  it('fills the saved key only for the provider that was saved', () => {
    expect(apiKeyForSelectedProvider('openai', 'deepseek', 'sk-ds')).toBe('')
    expect(apiKeyForSelectedProvider('deepseek', 'deepseek', 'sk-ds')).toBe('sk-ds')
    expect(apiKeyForSelectedProvider('', 'deepseek', 'sk-ds')).toBe('')
  })

  it('uses the API privacy warning as workbench notice text', () => {
    expect(privacyNoticeText('Sending 2 review comment(s)')).toBe('Sending 2 review comment(s)')
    expect(privacyNoticeText(null)).toBe('')
    expect(privacyNoticeText(undefined)).toBe('')
  })
})
