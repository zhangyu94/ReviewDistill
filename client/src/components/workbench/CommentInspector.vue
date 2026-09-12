<script setup lang="ts">
import type { InboxItemJson, InboxResponse } from '../../api/client.ts'
import type { LocationRow } from '../../inboxLocation.ts'
import { computed, ref, watch } from 'vue'
import {
  acceptTooltip,
  changeTooltip,
  dropTooltip,
  verifyTooltip,
} from '../../inboxTooltips.ts'
import { changeIssueOptions, showAssignType } from '../../workbench/workbenchMode.ts'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const props = defineProps<{
  view: 'unlabeled' | 'observation'
  selected: InboxItemJson | undefined
  data: InboxResponse | null
  error: string
  notice: string
  locationRows: LocationRow[]
  contextParts: { prose: string, extras: string }
  suggestionTitle: string | null
  changeId: string
}>()

const emit = defineEmits<{
  'update:changeId': [value: string]
  'accept': []
  'change': []
  'verify': []
  'drop': []
  'configureLlm': []
}>()

function onChangeId(value: unknown) {
  if (typeof value === 'string') { emit('update:changeId', value) }
}

const changeIssues = computed(() =>
  changeIssueOptions(props.data?.issues ?? [], props.selected?.issue?.id ?? null),
)
const changeEmpty = computed(() => changeIssues.value.length === 0)
const whyOpen = ref(false)
watch(() => props.selected?.comment.id, () => {
  whyOpen.value = false
})
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
              Quality
            </dt><dd>{{ selected.comment.quality }}</dd>
            <dt class="ch-muted-text">
              In the manuscript
            </dt><dd>{{ selected.in_manuscript ? 'Yes' : 'No' }}</dd>
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

        <section class="ch-panel">
          <h2 class="ch-kicker">
            Quality
          </h2>
          <p v-if="!selected.in_manuscript" class="mb-3">
            Not in the manuscript.
            <span v-if="selected.guess">{{ selected.guess }}</span>
          </p>
          <div class="flex flex-wrap items-center gap-1.5">
            <button
              class="ch-btn ch-btn-default"
              type="button"
              :disabled="selected.comment.quality === 'verified'"
              :title="verifyTooltip()"
              @click="emit('verify')"
            >
              Verify
            </button>
            <button
              class="ch-btn ch-btn-outline"
              type="button"
              :disabled="selected.comment.quality === 'dropped'"
              :title="dropTooltip()"
              @click="emit('drop')"
            >
              Drop
            </button>
          </div>
        </section>

        <template v-if="showAssignType(view, selected.labeled)">
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Assign type
            </h2>
            <template v-if="selected.coding">
              <p class="mb-1">
                <span class="rounded-[var(--ch-radius)] bg-[var(--ch-color-secondary)] px-1.5 py-0.5 text-xs font-medium uppercase tracking-[0.06em]">
                  {{ selected.coding.kind === 'existing' ? 'Existing issue' : 'New issue type' }}
                </span>
              </p>
              <p class="font-semibold">
                {{ suggestionTitle }}
              </p>
              <template v-if="selected.coding.rationale">
                <button
                  class="mt-1 text-[var(--ch-color-muted-foreground)] underline"
                  type="button"
                  :aria-expanded="whyOpen"
                  @click="whyOpen = !whyOpen"
                >
                  Why?
                </button>
                <p v-if="whyOpen" class="ch-prose mt-1 text-[var(--ch-color-body)]">
                  {{ selected.coding.rationale }}
                </p>
              </template>
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
              No AI suggestion. Use <strong>Label with AI</strong> to propose types for unlabeled comments.
            </p>
            <div class="mt-3 border-t border-[var(--ch-color-border)] pt-3">
              <p class="ch-muted-text mb-1.5">
                Apply this suggestion, or leave the comment unlabeled
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
              </div>
              <p class="ch-muted-text mb-1.5 mt-3">
                Or assign an existing issue type
              </p>
              <div class="flex flex-wrap items-center gap-1.5">
                <Select :model-value="changeId" @update:model-value="onChangeId">
                  <SelectTrigger class="w-auto min-w-40" title="Issue type to assign">
                    <SelectValue placeholder="Issue type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="issue in changeIssues" :key="issue.id" :value="issue.id">
                      {{ issue.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <span class="inline-flex" :title="changeTooltip(!changeEmpty)">
                  <button
                    class="ch-btn ch-btn-outline"
                    type="button"
                    :disabled="changeEmpty"
                    @click="emit('change')"
                  >Change</button>
                </span>
              </div>
            </div>
          </section>
        </template>
        <template v-else>
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Type
            </h2>
            <p v-if="selected.issue" class="mb-1.5 font-semibold">
              {{ selected.issue.code }} · {{ selected.issue.name }}
            </p>
            <p class="ch-muted-text mb-1.5">
              Assign a different issue type
            </p>
            <div class="flex flex-wrap items-center gap-1.5">
              <Select :model-value="changeId" @update:model-value="onChangeId">
                <SelectTrigger class="w-auto min-w-40" title="Issue type to assign">
                  <SelectValue placeholder="Issue type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="issue in changeIssues" :key="issue.id" :value="issue.id">
                    {{ issue.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <span class="inline-flex" :title="changeTooltip(!changeEmpty)">
                <button
                  class="ch-btn ch-btn-outline"
                  type="button"
                  :disabled="changeEmpty"
                  @click="emit('change')"
                >Change</button>
              </span>
            </div>
          </section>
        </template>
      </div>
    </template>
  </div>
</template>
