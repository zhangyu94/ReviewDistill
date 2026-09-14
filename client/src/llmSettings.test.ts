import { describe, expect, it } from 'vitest'
import { apiKeyForSelectedProvider, apiKeyInputType, canSaveLlmSettings, defaultLlmModel, keySetForSelectedProvider, LLM_SETTINGS_PROVIDERS } from './llmSettings.ts'

describe('llmSettings', () => {
  it('lists DeepSeek, OpenAI, and Anthropic', () => {
    expect(LLM_SETTINGS_PROVIDERS.map((row) => row.id)).toEqual(['deepseek', 'openai', 'anthropic'])
  })

  it('fills the default model for a provider', () => {
    expect(defaultLlmModel('deepseek')).toBe('deepseek-chat')
    expect(defaultLlmModel('openai')).toBe('gpt-4o-mini')
    expect(defaultLlmModel('anthropic')).toBe('claude-sonnet-4-20250514')
  })

  it('requires a provider and a key unless one is already set', () => {
    expect(canSaveLlmSettings({ provider: '', apiKey: 'sk', keySet: false })).toBe(false)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: '', keySet: false })).toBe(false)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: '', keySet: true })).toBe(true)
    expect(canSaveLlmSettings({ provider: 'deepseek', apiKey: 'sk', keySet: false })).toBe(true)
  })

  it('uses password input until the key is shown', () => {
    expect(apiKeyInputType(false)).toBe('password')
    expect(apiKeyInputType(true)).toBe('text')
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
})
