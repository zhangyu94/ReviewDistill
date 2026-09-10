<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  fetchLlmSettings,
  saveLlmSettings,
  type LlmSettingsResponse,
} from '../../api/client.ts'
import {
  LLM_SETTINGS_PROVIDERS,
  apiKeyInputType,
  canSaveLlmSettings,
  defaultLlmModel,
  keySetForSelectedProvider,
} from '../../llmSettings.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const open = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const showKey = ref(false)
const data = ref<LlmSettingsResponse | null>(null)
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

async function show() {
  open.value = true
  error.value = ''
  notice.value = ''
  apiKey.value = ''
  showKey.value = false
  try {
    data.value = await fetchLlmSettings()
    const id = data.value.default_project_id || data.value.projects[0]?.id || ''
    if (id)
      await applyProject(id)
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
}

function hide() {
  open.value = false
}

function onProjectId(value: unknown) {
  if (typeof value === 'string' && value)
    void applyProject(value)
}

function onProviderChange(id: string) {
  provider.value = id
  model.value = defaultLlmModel(id)
  keySet.value = keySetForSelectedProvider(id, savedProvider.value, savedKeySet.value)
}

function onProviderId(value: unknown) {
  if (typeof value === 'string' && value)
    onProviderChange(value)
}

function onOpenEvent() {
  void show()
}

async function save() {
  if (!canSave.value)
    return
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
    window.dispatchEvent(new CustomEvent('reviewdistill:llm-changed'))
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}

onMounted(() => {
  window.addEventListener('reviewdistill:open-settings', onOpenEvent)
})
onUnmounted(() => {
  window.removeEventListener('reviewdistill:open-settings', onOpenEvent)
})

defineExpose({ show })
</script>

<template>
  <button
    class="ch-chip ch-chip-idle ml-auto gap-1"
    type="button"
    title="Configure the LLM provider and API key"
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
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="w-full max-w-md rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] p-4 text-xs shadow-lg">
      <h2 class="mb-1 font-semibold">Settings</h2>
      <p class="ch-kicker">Assistant configuration</p>
      <p v-if="error" class="ch-error-text mb-2">{{ error }}</p>
      <p v-if="notice" class="ch-muted-text mb-2">{{ notice }}</p>

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
        <SelectTrigger class="mb-3 w-full" title="LLM provider for Get AI suggestions">
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
          >{{ showKey ? 'Hide' : 'Show' }}</button>
        </div>
        <p class="ch-muted-text mb-3">
          Stored in this paper’s <code>.reviewdistill/.env</code> (gitignored).
          <template v-if="keySet"> A key is set. Paste a new one to replace it.</template>
        </p>
      </template>

      <div class="flex justify-end gap-1.5">
        <button class="ch-btn ch-btn-outline" type="button" title="Close without saving" @click="hide">Close</button>
        <button
          class="ch-btn ch-btn-default"
          type="button"
          title="Save provider, model, and API key to this paper"
          :disabled="busy || !canSave"
          @click="save"
        >Save</button>
      </div>
    </div>
  </div>
</template>
