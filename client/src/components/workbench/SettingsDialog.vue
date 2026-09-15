<script setup lang="ts">
import type { DataLocation } from '../../api/client.ts'
import type { SettingsPanelId } from '../../settingsPanels.ts'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  chooseDataFolder,
  fetchDataLocation,
  fetchLlmSettings,
  openDataFolder,
  saveDataLocation,
  saveLlmSettings,
} from '../../api/client.ts'
import { canSaveDataPath, folderFileUrl } from '../../dataLocation.ts'
import {
  apiKeyForSelectedProvider,
  canSaveLlmSettings,
  defaultLlmModel,
  keySetForSelectedProvider,
  LLM_SETTINGS_PROVIDERS,
} from '../../llmSettings.ts'
import {
  DEFAULT_SETTINGS_PANEL,
  SETTINGS_PANELS,
  settingsErrorMessage,
} from '../../settingsPanels.ts'
import { afterHomeChange, homeSaveFollowUpOrder } from '../../workbench/workbenchMode.ts'
import { useWorkbenchStore } from '../../workbench/workbenchStore.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const store = useWorkbenchStore()
const router = useRouter()
const { settingsOpen } = storeToRefs(store)
const panel = ref<SettingsPanelId>(DEFAULT_SETTINGS_PANEL)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const showKey = ref(false)
const location = ref<DataLocation | null>(null)
const homeDraft = ref('')
const provider = ref('')
const model = ref('')
const apiKey = ref('')
const keySet = ref(false)
const savedProvider = ref('')
const savedKeySet = ref(false)
const savedApiKey = ref('')

const canSave = computed(() => {
  if (panel.value === 'data') {
    return canSaveDataPath({
      draft: homeDraft.value,
      saved: location.value?.home ?? '',
    })
  }
  return canSaveLlmSettings({
    provider: provider.value,
    apiKey: apiKey.value,
    keySet: keySet.value,
  })
})

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
  panel.value = DEFAULT_SETTINGS_PANEL
  error.value = ''
  notice.value = ''
  showKey.value = false
  try {
    applyLlmSettings(await fetchLlmSettings())
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  try {
    location.value = await fetchDataLocation()
    homeDraft.value = location.value.home
  }
  catch (err) {
    location.value = null
    homeDraft.value = ''
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

async function openHomeFolder(event: Event) {
  event.preventDefault()
  if (!location.value) {
    return
  }
  try {
    await openDataFolder()
  }
  catch {
    window.open(location.value.file_url || folderFileUrl(location.value.home), '_blank')
  }
}

async function chooseHomeFolder() {
  busy.value = true
  error.value = ''
  try {
    const body = await chooseDataFolder()
    if (body.home) {
      homeDraft.value = body.home
    }
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
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
  if (!canSave.value) {
    return
  }
  if (panel.value === 'data') {
    await saveDataPath()
    return
  }
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

async function saveDataPath() {
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    location.value = await saveDataLocation(homeDraft.value.trim())
    homeDraft.value = location.value.home
    const next = afterHomeChange()
    for (const step of homeSaveFollowUpOrder()) {
      if (step === 'reload') {
        await router.push(next.href)
        await store.loadAll(next.labelId)
        notice.value = 'Saved.'
      }
      else {
        try {
          applyLlmSettings(await fetchLlmSettings())
        }
        catch (err) {
          error.value = err instanceof Error ? err.message : String(err)
        }
      }
    }
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
      <p v-if="notice" class="ch-muted-text mb-2">
        {{ notice }}
      </p>

      <template v-if="panel === 'data'">
        <p class="ch-muted-text mb-1">
          Comments and labels live in this folder:
        </p>
        <div class="mb-2 flex items-center gap-1.5">
          <input
            v-model="homeDraft"
            class="ch-input min-w-0 flex-1 font-mono text-[11px]"
            type="text"
            spellcheck="false"
            autocomplete="off"
            aria-label="Data folder path"
            title="Folder for comments and labels"
          >
          <button
            class="ch-btn ch-btn-outline shrink-0"
            type="button"
            title="Pick a folder on this computer"
            :disabled="busy"
            @click="chooseHomeFolder"
          >
            Choose…
          </button>
        </div>
        <p class="ch-muted-text mb-3">
          Save points ReviewDistill at this folder. It does not copy existing files.
        </p>
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
              :type="showKey ? 'text' : 'password'"
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

      <div class="flex items-center gap-1.5">
        <a
          v-if="panel === 'data'"
          class="ch-btn ch-btn-outline no-underline hover:no-underline"
          :class="location ? '' : 'pointer-events-none opacity-50'"
          :href="location?.file_url || folderFileUrl(homeDraft)"
          target="_blank"
          rel="noopener noreferrer"
          title="Open the folder on this computer"
          :aria-disabled="!location"
          @click="openHomeFolder"
        >
          Open folder
        </a>
        <button
          class="ch-btn ch-btn-default ml-auto"
          type="button"
          :title="panel === 'data' ? 'Use this folder for comments and labels' : 'Save provider, model, and API key'"
          :disabled="busy || !canSave"
          @click="save"
        >
          Save
        </button>
      </div>
    </div>
  </div>
</template>
