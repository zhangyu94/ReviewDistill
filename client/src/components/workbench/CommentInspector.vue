<script setup lang="ts">
import type { InboxItemJson, InboxResponse } from '../../api/client.ts'
import type { LocationRow } from '../../inboxLocation.ts'
import {
  acceptTooltip,
  changeTooltip,
  keepTooltip,
  rejectTooltip,
  retractTooltip,
} from '../../inboxTooltips.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

defineProps<{
  view: 'uncoded' | 'disappeared' | 'observation'
  selected: InboxItemJson | undefined
  data: InboxResponse | null
  error: string
  notice: string
  locationRows: LocationRow[]
  contextParts: { prose: string, extras: string }
  suggestionTitle: string | null
  changeId: string
  issuesEmpty: boolean
}>()

const emit = defineEmits<{
  'update:changeId': [value: string]
  'accept': []
  'reject': []
  'change': []
  'keep': []
  'retract': []
  'configureLlm': []
}>()

function onChangeId(value: unknown) {
  if (typeof value === 'string') { emit('update:changeId', value) }
}
</script>

<template>
  <div>
    <p v-if="error" class="ch-error-text mb-3">
      {{ error }}
    </p>
    <p v-if="notice" class="ch-muted-text mb-3">
      {{ notice }}
    </p>
    <template v-if="selected">
      <div class="flex max-w-3xl flex-col gap-3">
        <section class="ch-panel">
          <h2 class="ch-kicker">
            Comment
          </h2>
          <p class="ch-prose whitespace-pre-wrap">
            {{ selected.comment.raw_text }}
          </p>
        </section>

        <section class="ch-panel-muted">
          <h2 class="ch-kicker">
            Manuscript context
          </h2>
          <p class="font-[var(--ch-font-mono)] leading-5 whitespace-pre-wrap text-[var(--ch-color-body)]">
            {{ contextParts.prose || '—' }}
          </p>
          <p v-if="contextParts.extras" class="ch-muted-text mt-2 leading-4">
            {{ contextParts.extras }}
          </p>
        </section>

        <section class="ch-panel">
          <h2 class="ch-kicker">
            Location
          </h2>
          <dl class="grid grid-cols-[7.5rem_1fr] gap-x-2 gap-y-1">
            <template v-for="row in locationRows" :key="row.label">
              <dt class="ch-muted-text">
                {{ row.label }}
              </dt>
              <dd class="min-w-0 break-all">
                <a
                  v-if="row.href"
                  class="ch-link"
                  :href="row.href"
                  target="_blank"
                  rel="noreferrer"
                >{{ row.value }}</a>
                <code v-else-if="row.label === 'Command' || row.label === 'File'">{{ row.value }}</code>
                <template v-else>
                  {{ row.value }}
                </template>
              </dd>
            </template>
          </dl>
        </section>

        <details class="ch-panel">
          <summary class="cursor-pointer font-medium">
            Record details
          </summary>
          <dl class="mt-2 grid grid-cols-[7.5rem_1fr] gap-x-2 gap-y-1 leading-4">
            <dt class="ch-muted-text">
              ID
            </dt><dd class="break-all">
              {{ selected.comment.id }}
            </dd>
            <dt class="ch-muted-text">
              Source type
            </dt><dd>{{ selected.comment.source_type }}</dd>
            <dt class="ch-muted-text">
              Status
            </dt><dd>{{ selected.comment.status }}</dd>
            <dt class="ch-muted-text">
              Git commit
            </dt><dd class="break-all">
              {{ selected.comment.git_commit || '—' }}
            </dd>
            <dt class="ch-muted-text">
              Fingerprint
            </dt><dd class="break-all">
              {{ selected.comment.fingerprint }}
            </dd>
            <dt class="ch-muted-text">
              Created
            </dt><dd>{{ selected.comment.created_at }}</dd>
            <template v-if="selected.comment.supersedes_id">
              <dt class="ch-muted-text">
                Supersedes
              </dt><dd class="break-all">
                {{ selected.comment.supersedes_id }}
              </dd>
            </template>
          </dl>
        </details>

        <template v-if="view === 'uncoded'">
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Assign type
            </h2>
            <template v-if="selected.coding">
              <p class="mb-1">
                <span class="rounded-[var(--ch-radius)] bg-[var(--ch-color-secondary)] px-1.5 py-0.5 text-xs font-medium uppercase tracking-[0.06em]">
                  {{ selected.coding.kind === 'existing' ? 'Existing issue' : 'New issue type' }}
                </span>
                <span v-if="selected.coding.confidence != null" class="ch-muted-text ml-2">{{ Math.round(selected.coding.confidence * 100) }}% confidence</span>
              </p>
              <p class="font-semibold">
                {{ suggestionTitle }}
              </p>
              <p class="ch-prose mt-1 text-[var(--ch-color-body)]">
                {{ selected.coding.rationale }}
              </p>
            </template>
            <p v-else-if="!data?.llm_provider" class="ch-muted-text">
              No AI suggestion.
              <button
                class="ch-btn ch-btn-outline ml-1"
                type="button"
                title="Open Settings to choose a provider and API key"
                @click="emit('configureLlm')"
              >
                Configure LLM
              </button>
            </p>
            <p v-else class="ch-muted-text">
              No AI suggestion. Use <strong>Get AI suggestions</strong> to code all uncoded comments.
            </p>
            <div class="mt-3 border-t border-[var(--ch-color-border)] pt-3">
              <p class="ch-muted-text mb-1.5">
                Apply this suggestion, or skip coding this comment
              </p>
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="inline-flex" :title="acceptTooltip(!!selected.coding)">
                  <button
                    class="ch-btn ch-btn-default"
                    type="button"
                    :disabled="!selected.coding"
                    @click="emit('accept')"
                  >Accept</button>
                </span>
                <button
                  class="ch-btn ch-btn-outline"
                  type="button"
                  :title="rejectTooltip()"
                  @click="emit('reject')"
                >
                  Reject
                </button>
              </div>
              <p class="ch-muted-text mb-1.5 mt-3">
                Or assign an existing issue type instead
              </p>
              <div class="flex flex-wrap items-center gap-1.5">
                <Select :model-value="changeId" @update:model-value="onChangeId">
                  <SelectTrigger class="w-auto min-w-40" title="Issue type to assign with Change">
                    <SelectValue placeholder="Issue type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="issue in data?.issues ?? []" :key="issue.id" :value="issue.id">
                      {{ issue.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <span class="inline-flex" :title="changeTooltip(!issuesEmpty)">
                  <button
                    class="ch-btn ch-btn-outline"
                    type="button"
                    :disabled="issuesEmpty"
                    @click="emit('change')"
                  >Change</button>
                </span>
              </div>
            </div>
          </section>
        </template>
        <template v-else-if="view === 'disappeared'">
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Disappeared
            </h2>
            <p class="mb-3">
              {{ selected.guess }}
            </p>
            <div class="flex flex-wrap items-center gap-1.5">
              <button
                class="ch-btn ch-btn-default"
                type="button"
                :title="keepTooltip()"
                @click="emit('keep')"
              >
                Keep
              </button>
              <button
                class="ch-btn ch-btn-outline"
                type="button"
                :title="retractTooltip()"
                @click="emit('retract')"
              >
                Retract
              </button>
            </div>
          </section>
        </template>
      </div>
    </template>
  </div>
</template>
