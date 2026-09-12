<script setup lang="ts">
import type { DataLocation, LlmSettingsResponse } from '../../api/client.ts'
import type { SettingsPanelId } from '../../settingsPanels.ts'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import {
  fetchDataLocation,
  fetchLlmSettings,
  saveLlmSettings,
} from '../../api/client.ts'
import {
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
const data = ref<LlmSettingsResponse | null>(null)
const location = ref<DataLocation | null>(null)
const copied = ref(false)
const projectId = ref('')
const provider = ref('')
const model = ref('')
const apiKey = ref('')
const keySet = ref(false)
const savedProvider = ref('')
const savedKeySet = ref(false)

const canSave = computed(() =>
  canSaveLlmSettings({
    projectId: projectId.value,
    provider: provider.value,
    apiKey: apiKey.value,
    keySet: keySet.value,
  }),
)

async function applyProject(id: string) {
  try {
    const body = await fetchLlmSettings(id)
    data.value = body
    const selected = body.selected
    projectId.value = id
    provider.value = selected?.provider ?? ''
    model.value = selected?.model ?? (provider.value ? defaultLlmModel(provider.value) : '')
    savedProvider.value = provider.value
    savedKeySet.value = selected?.key_set ?? false
    keySet.value = savedKeySet.value
    apiKey.value = ''
    showKey.value = false
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function loadSettings() {
  panel.value = settingsPanelOnOpen()
  error.value = ''
  notice.value = ''
  copied.value = false
  apiKey.value = ''
  showKey.value = false
  try {
    data.value = await fetchLlmSettings()
    const id = data.value.default_project_id || data.value.projects[0]?.id || ''
    if (id) {
      await applyProject(id)
    }
    else {
      projectId.value = ''
      provider.value = ''
      model.value = ''
      keySet.value = false
      savedProvider.value = ''
      savedKeySet.value = false
    }
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

function onProjectId(value: unknown) {
  if (typeof value === 'string' && value) { void applyProject(value) }
}

function onProviderChange(id: string) {
  provider.value = id
  model.value = defaultLlmModel(id)
  keySet.value = keySetForSelectedProvider(id, savedProvider.value, savedKeySet.value)
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
      project_id: projectId.value,
      provider: provider.value,
      model: model.value.trim() || defaultLlmModel(provider.value),
      api_key: apiKey.value,
    })
    notice.value = 'Saved.'
    apiKey.value = ''
    savedProvider.value = provider.value
    savedKeySet.value = true
    keySet.value = true
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
    class="ch-chip ch-chip-idle ml-auto gap-1"
    type="button"
    title="Assistant and data location"
    @click="show"
  >
    <svg class="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2" />
      <path
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"
      />
    </svg>
    Settings
  </button>
  <div
    v-if="settingsOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="w-full max-w-md rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-4 text-xs shadow-lg">
      <h2 class="mb-3 font-semibold">
        Settings
      </h2>
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
          class="ch-btn ch-btn-outline mb-1"
          type="button"
          title="Copy the folder path"
          :disabled="!location"
          @click="copyHomeFolder"
        >
          {{ copied ? 'Copied' : 'Copy folder path' }}
        </button>
        <p class="ch-muted-text mb-3">
          Copy the whole folder to back up — JSONL files for comments, types, and coding — especially if ReviewDistill is running.
          To store it somewhere else, quit the workbench and run
          <code>reviewdistill paths move ~/Documents/reviewdistill</code>
          (or <code>reviewdistill paths use DIR</code> for a folder you already copied). Restart <code>reviewdistill serve</code> afterwards.
        </p>
      </template>

      <template v-else>
        <label class="ch-field-label">Paper</label>
        <Select :model-value="projectId || undefined" @update:model-value="onProjectId">
          <SelectTrigger class="mb-3 w-full" title="Paper whose LLM settings to edit">
            <SelectValue placeholder="Choose a paper…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="row in data?.projects ?? []" :key="row.id" :value="row.id">
              {{ row.name }} · {{ row.root_path }}
            </SelectItem>
          </SelectContent>
        </Select>

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
            Stored in this paper’s <code>.reviewdistill/.env</code> (gitignored).
            <template v-if="keySet">
              A key is set. Paste a new one to replace it.
            </template>
          </p>
        </template>
      </template>

      <div class="flex justify-end gap-1.5">
        <button class="ch-btn ch-btn-outline" type="button" title="Close without saving" @click="hide">
          Close
        </button>
        <button
          v-if="showsSettingsSave(panel)"
          class="ch-btn ch-btn-default"
          type="button"
          title="Save provider, model, and API key to this paper"
          :disabled="busy || !canSave"
          @click="save"
        >
          Save
        </button>
      </div>
    </div>
  </div>
</template>
