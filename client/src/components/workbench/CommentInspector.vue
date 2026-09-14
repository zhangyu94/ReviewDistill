<script setup lang="ts">
import type { InboxItemJson, InboxResponse, TaxonomyNode } from '../../api/client.ts'
import { fileRevealAccessibleName, fileRevealLabel, type LocationRow } from '../../inboxLocation.ts'
import { computed, ref, watch } from 'vue'
import { assignSuggestion, shouldAssignOnSelect } from '../../workbench/assignType.ts'
import { assignableIssueRows } from '../../workbench/taxonomyTree.ts'
import { showAssignType } from '../../workbench/workbenchMode.ts'
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
  locationRows: LocationRow[]
  contextParts: { prose: string, extras: string }
  forest?: TaxonomyNode[]
}>()

const emit = defineEmits<{
  accept: []
  assign: [id: string]
  verify: []
  drop: []
  configureLlm: []
  reveal: []
}>()

function onAssignId(value: unknown) {
  if (typeof value !== 'string') { return }
  if (!shouldAssignOnSelect(props.selected?.issue?.id, value)) { return }
  emit('assign', value)
}

const changeIssues = computed(() => {
  const forest = props.forest
  if (forest && forest.length) {
    return assignableIssueRows(forest, props.selected?.issue?.id)
  }
  return (props.data?.issues ?? []).map((issue) => ({
    ...issue,
    depth: 0,
  }))
})
const changeEmpty = computed(() => changeIssues.value.length === 0)
const menuValue = computed(() => props.selected?.issue?.id ?? '')
const changeMenuTitle = computed(() => (
  changeEmpty.value
    ? 'No issue types yet. Accept a new-issue suggestion first.'
    : 'The menu shows the current type. Pick another type to assign it.'
))
const suggestion = computed(() =>
  assignSuggestion(props.selected?.coding, changeIssues.value),
)
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
    <template v-if="selected">
      <div class="flex w-full min-w-0 flex-col gap-3">
        <section class="ch-panel">
          <div class="mb-1.5 flex flex-wrap items-center gap-1.5">
            <h2 class="ch-kicker mb-0">
              Comment
            </h2>
            <span
              v-if="!selected.in_manuscript"
              class="ch-chip ch-chip-idle"
              title="This remark is no longer in the .tex file."
            >Left the manuscript</span>
          </div>
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

        <template v-if="showAssignType(selected.labeled)">
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Assign type
            </h2>
            <div class="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
              <template v-if="suggestion">
                <p class="mb-0 font-semibold">
                  {{ suggestion.title }}
                </p>
                <button
                  v-if="suggestion.rationale"
                  class="text-[var(--ch-color-muted-foreground)] underline"
                  type="button"
                  :aria-expanded="whyOpen"
                  @click="whyOpen = !whyOpen"
                >
                  Why?
                </button>
                <span class="ml-auto inline-flex" title="Apply the AI suggestion. If it proposed a new issue type, that type is added to the taxonomy and this comment becomes an example.">
                  <button
                    class="ch-btn ch-btn-default"
                    type="button"
                    @click="emit('accept')"
                  >Accept</button>
                </span>
              </template>
              <template v-else>
                <p class="ch-muted-text mb-0">
                  No AI suggestion.
                </p>
                <button
                  v-if="!data?.llm_provider"
                  class="ch-btn ch-btn-outline"
                  type="button"
                  title="Open Settings to choose a provider and API key"
                  @click="emit('configureLlm')"
                >
                  Configure LLM
                </button>
              </template>
            </div>
            <p v-if="whyOpen && suggestion?.rationale" class="ch-prose mb-3 text-[var(--ch-color-body)]">
              {{ suggestion.rationale }}
            </p>
            <Select
              :model-value="menuValue || undefined"
              :disabled="changeEmpty"
              @update:model-value="onAssignId"
            >
              <SelectTrigger class="w-auto min-w-40" :title="changeMenuTitle">
                <SelectValue placeholder="Choose a type…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="issue in changeIssues" :key="issue.id" :value="issue.id">
                  <span :style="{ paddingLeft: `${issue.depth * 12}px` }">{{ issue.name }}</span>
                </SelectItem>
              </SelectContent>
            </Select>
          </section>
        </template>
        <template v-else>
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Type
            </h2>
            <Select
              :model-value="menuValue || undefined"
              :disabled="changeEmpty"
              @update:model-value="onAssignId"
            >
              <SelectTrigger class="w-auto min-w-40" :title="changeMenuTitle">
                <SelectValue placeholder="Choose a type…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="issue in changeIssues" :key="issue.id" :value="issue.id">
                  <span :style="{ paddingLeft: `${issue.depth * 12}px` }">{{ issue.name }}</span>
                </SelectItem>
              </SelectContent>
            </Select>
          </section>
        </template>

        <section class="ch-panel">
          <h2 class="ch-kicker">
            Quality
          </h2>
          <p v-if="selected.guess" class="mb-3">
            {{ selected.guess }}
          </p>
          <div class="flex flex-wrap items-center gap-1.5">
            <button
              class="ch-btn ch-btn-outline"
              type="button"
              :disabled="selected.comment.quality === 'verified'"
              title="This observation is quality-assured (wording, context, worth keeping as evidence). Does not confirm the issue type."
              @click="emit('verify')"
            >
              Verify
            </button>
            <button
              class="ch-btn ch-btn-outline"
              type="button"
              :disabled="selected.comment.quality === 'dropped'"
              title="Do not distill this observation (too local, or a bad extract). History is kept."
              @click="emit('drop')"
            >
              Drop
            </button>
          </div>
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
                <button
                  v-else-if="row.reveal"
                  class="ch-link cursor-pointer border-0 bg-transparent p-0 text-left"
                  type="button"
                  :title="fileRevealLabel()"
                  :aria-label="fileRevealAccessibleName(row.value)"
                  @click="emit('reveal')"
                >
                  <code>{{ row.value }}</code>
                </button>
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
      </div>
    </template>
  </div>
</template>
