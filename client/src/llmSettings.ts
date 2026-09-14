export const LLM_SETTINGS_PROVIDERS = [
  { id: 'deepseek', label: 'DeepSeek' },
  { id: 'openai', label: 'OpenAI' },
  { id: 'anthropic', label: 'Anthropic' },
] as const

export type LlmProviderId = typeof LLM_SETTINGS_PROVIDERS[number]['id']

const DEFAULTS: Record<LlmProviderId, string> = {
  deepseek: 'deepseek-chat',
  openai: 'gpt-4o-mini',
  anthropic: 'claude-sonnet-4-20250514',
}

export function defaultLlmModel(provider: string): string {
  return DEFAULTS[provider as LlmProviderId] ?? ''
}

export function canSaveLlmSettings(args: {
  provider: string
  apiKey: string
  keySet: boolean
}): boolean {
  if (!args.provider) { return false }
  if (args.keySet) { return true }
  return args.apiKey.trim().length > 0
}

export function keySetForSelectedProvider(
  provider: string,
  savedProvider: string,
  savedKeySet: boolean,
): boolean {
  return Boolean(provider) && provider === savedProvider && savedKeySet
}

export function apiKeyForSelectedProvider(
  provider: string,
  savedProvider: string,
  savedApiKey: string,
): string {
  if (provider && provider === savedProvider) {
    return savedApiKey
  }
  return ''
}

export function privacyNoticeText(warning: string | null | undefined): string {
  return warning ?? ''
}
