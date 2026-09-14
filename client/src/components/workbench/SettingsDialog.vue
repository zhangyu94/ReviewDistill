<script setup lang="ts">
import type { DataLocation } from '../../api/client.ts'
import type { SettingsPanelId } from '../../settingsPanels.ts'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import {
  fetchDataLocation,
  fetchLlmSettings,
  saveLlmSettings,
} from '../../api/client.ts'
import {
  apiKeyForSelectedProvider,
  apiKeyInputType,
  canSaveLlmSettings,
  defaultLlmModel,
  keySetForSelectedProvider,
  LLM_SETTINGS_PROVIDERS,
} from '../../llmSettings.ts'
import {
  DEFAULT_SETTINGS_PANEL,
  SETTINGS_PANELS,
  settingsErrorMessage,
  settingsPanelOnOpen,
  showsSettingsSave,
} from '../../settingsPanels.ts'
import { useWorkbenchStore } from '../../workbench/workbenchStore.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const store = useWorkbenchStore()
const { settingsOpen } = storeToRefs(store)
const panel = ref<SettingsPanelId>(DEFAULT_SETTINGS_PANEL)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const showKey = ref(false)
const location = ref<DataLocation | null>(null)
const copied = ref(false)
const provider = ref('')
const model = ref('')
const apiKey = ref('')
const keySet = ref(false)
const savedProvider = ref('')
const savedKeySet = ref(false)
const savedApiKey = ref('')

const canSave = computed(() =>
  canSaveLlmSettings({
    provider: provider.value,
    apiKey: apiKey.value,
    keySet: keySet.value,
  }),
)

function applyLlmSettings(body: Awaited<ReturnType<typeof fetchLlmSettings>>) {
  provider.value = body.provider ?? ''
  model.value = body.model ?? (provider.value ? defaultLlmModel(provider.value) : '')
  savedProvider.value = provider.value
  savedKeySet.value = body.key_set
  savedApiKey.value = body.api_key ?? ''
  keySet.value = savedKeySet.value
  apiKey.value = savedApiKey.value
}

async function loadSettings() {
  panel.value = settingsPanelOnOpen()
  error.value = ''
  notice.value = ''
  copied.value = false
  showKey.value = false
  try {
    applyLlmSettings(await fetchLlmSettings())
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  try {
    location.value = await fetchDataLocation()
  }
  catch (err) {
    location.value = null
    error.value = settingsErrorMessage(error.value, err)
  }
}

function show() {
  store.openSettings()
}

function hide() {
  store.closeSettings()
}

watch(settingsOpen, (open) => {
  if (open) { void loadSettings() }
})

async function copyHomeFolder() {
  if (!location.value) { return }
  try {
    await navigator.clipboard.writeText(location.value.home)
    copied.value = true
  }
  catch {
    copied.value = false
  }
}

function onProviderChange(id: string) {
  provider.value = id
  model.value = defaultLlmModel(id)
  keySet.value = keySetForSelectedProvider(id, savedProvider.value, savedKeySet.value)
  apiKey.value = apiKeyForSelectedProvider(id, savedProvider.value, savedApiKey.value)
}

function onProviderId(value: unknown) {
  if (typeof value === 'string' && value) { onProviderChange(value) }
}

async function save() {
  if (!canSave.value) { return }
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await saveLlmSettings({
      provider: provider.value,
      model: model.value.trim() || defaultLlmModel(provider.value),
      api_key: apiKey.value,
    })
    applyLlmSettings(await fetchLlmSettings())
    notice.value = 'Saved.'
    await store.loadInbox()
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}

defineExpose({ show })
</script>

<template>
  <button
    class="ch-chip ch-chip-idle gap-1"
    type="button"
    title="Assistant and data location"
    @click="show"
  >
    <span class="i-fa6-solid:gear h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    Settings
  </button>
  <div
    v-if="settingsOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="w-full max-w-md rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-4 text-xs shadow-lg">
      <div class="mb-3 flex items-center gap-1.5">
        <h2 class="font-semibold">
          Settings
        </h2>
        <button
          class="ch-btn ch-btn-outline ml-auto px-1.5"
          type="button"
          title="Close"
          aria-label="Close"
          @click="hide"
        >
          <span class="i-fa6-solid:xmark h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <div class="mb-3 flex flex-wrap gap-1.5" role="tablist" aria-label="Settings sections">
        <button
          v-for="row in SETTINGS_PANELS"
          :key="row.id"
          class="ch-chip"
          :class="panel === row.id ? 'ch-chip-active' : 'ch-chip-idle'"
          type="button"
          role="tab"
          :aria-selected="panel === row.id"
          :title="row.id === 'assistant' ? 'LLM provider, model, and API key' : 'Data folder on this computer'"
          @click="panel = row.id"
        >
          {{ row.label }}
        </button>
      </div>
      <p v-if="error" class="ch-error-text mb-2">
        {{ error }}
      </p>
      <p v-if="notice && panel === 'assistant'" class="ch-muted-text mb-2">
        {{ notice }}
      </p>

      <template v-if="panel === 'data'">
        <p class="ch-muted-text mb-1">
          Comments and issue types live in this folder:
        </p>
        <p class="mb-1 break-all font-mono text-[11px]">
          {{ location?.home ?? '…' }}
        </p>
        <button
          class="ch-btn ch-btn-outline"
          type="button"
          title="Copy the folder path"
          :disabled="!location"
          @click="copyHomeFolder"
        >
          {{ copied ? 'Copied' : 'Copy folder path' }}
        </button>
      </template>

      <template v-else>
        <label class="ch-field-label">Provider</label>
        <Select :model-value="provider || undefined" @update:model-value="onProviderId">
          <SelectTrigger class="mb-3 w-full" title="LLM provider for Label with AI">
            <SelectValue placeholder="Choose an LLM provider…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="row in LLM_SETTINGS_PROVIDERS" :key="row.id" :value="row.id">
              {{ row.label }}
            </SelectItem>
          </SelectContent>
        </Select>

        <template v-if="provider">
          <label class="ch-field-label">Model</label>
          <input
            v-model="model"
            class="ch-input mb-3"
            type="text"
            :placeholder="defaultLlmModel(provider)"
          >

          <label class="ch-field-label">API key</label>
          <div class="relative mb-1">
            <input
              v-model="apiKey"
              class="ch-input pr-14"
              :type="apiKeyInputType(showKey)"
              autocomplete="off"
              placeholder="Paste an API key for the selected provider"
            >
            <button
              class="absolute top-1/2 right-1 -translate-y-1/2 ch-btn ch-btn-outline h-5 px-1.5"
              type="button"
              :title="showKey ? 'Hide the API key' : 'Show the API key'"
              :aria-label="showKey ? 'Hide API key' : 'Show API key'"
              :aria-pressed="showKey"
              @click="showKey = !showKey"
            >
              {{ showKey ? 'Hide' : 'Show' }}
            </button>
          </div>
          <p class="ch-muted-text mb-3">
            Stored in this computer’s ReviewDistill folder (<code>.env</code>, gitignored), not in the paper repo.
            Use Show to read the saved key. An empty field on Save keeps the existing value.
          </p>
        </template>
      </template>

      <div v-if="showsSettingsSave(panel)" class="flex justify-end">
        <button
          class="ch-btn ch-btn-default"
          type="button"
          title="Save provider, model, and API key"
          :disabled="busy || !canSave"
          @click="save"
        >
          Save
        </button>
      </div>
    </div>
  </div>
</template>
