<script setup lang="ts">
import type { InboxItemJson, InboxResponse, TaxonomyNode } from '../../api/client.ts'
import type { LocationRow } from '../../inboxLocation.ts'
import { computed, ref, watch } from 'vue'
import { fileRevealAccessibleName, fileRevealLabel } from '../../inboxLocation.ts'
import { assignSuggestion, shouldAssignOnSelect } from '../../workbench/assignLabel.ts'
import { splitContextMark } from '../../workbench/contextMark.ts'
import { assignableLabelRows } from '../../workbench/taxonomyTree.ts'
import { showAssignLabel } from '../../workbench/workbenchMode.ts'
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
  forest?: TaxonomyNode[]
}>()

const emit = defineEmits<{
  accept: []
  assign: [id: string]
  verify: []
  delete: []
  configureLlm: []
  reveal: []
}>()

function onAssignId(value: unknown) {
  if (typeof value !== 'string') { return }
  if (!shouldAssignOnSelect(props.selected?.label?.id, value)) { return }
  emit('assign', value)
}

const changeLabels = computed(() => {
  const forest = props.forest
  if (forest && forest.length) {
    return assignableLabelRows(forest, props.selected?.label?.id)
  }
  return (props.data?.labels ?? []).map((label) => ({
    ...label,
    depth: 0,
  }))
})
const changeEmpty = computed(() => changeLabels.value.length === 0)
const menuValue = computed(() => props.selected?.label?.id ?? '')
const changeMenuTitle = computed(() => (
  changeEmpty.value
    ? 'No labels yet. Accept a new-label suggestion first.'
    : 'The menu shows the current label. Pick another label to assign it.'
))
const suggestion = computed(() =>
  assignSuggestion(props.selected?.assignment, changeLabels.value),
)
const contextMark = computed(() => {
  const text = props.selected?.comment.context_text ?? ''
  return splitContextMark(text, props.selected?.comment.context_offset)
})
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
          <div class="mb-1.5 flex flex-wrap items-center gap-1.5">
            <h2 class="ch-kicker mb-0">
              Manuscript context
            </h2>
            <span
              v-if="contextMark.marked"
              class="ch-muted-text inline-flex items-center gap-1"
            >(<span class="ch-context-mark" aria-hidden="true" /> Comment sat here)</span>
          </div>
          <p
            v-if="contextMark.marked"
            class="font-[var(--ch-font-mono)] leading-5 whitespace-pre-wrap text-[var(--ch-color-body)]"
          ><span>{{ contextMark.before }}</span><span
            class="ch-context-mark mx-px"
            title="Comment sat here"
            role="img"
            aria-label="Comment sat here"
          /><span>{{ contextMark.after }}</span></p>
          <p
            v-else
            class="font-[var(--ch-font-mono)] leading-5 whitespace-pre-wrap text-[var(--ch-color-body)]"
          >
            {{ contextMark.text || '—' }}
          </p>
        </section>

        <template v-if="showAssignLabel(selected.labeled)">
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Assign label
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
                <span class="ml-auto inline-flex" title="Accept the suggested label assignment. If it proposed a new label, that label is added to the taxonomy and this comment becomes an example.">
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
                <SelectValue placeholder="Choose a label…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="row in changeLabels" :key="row.id" :value="row.id">
                  <span :style="{ paddingLeft: `${row.depth * 12}px` }">{{ row.name }}</span>
                </SelectItem>
              </SelectContent>
            </Select>
          </section>
        </template>
        <template v-else>
          <section class="ch-panel">
            <h2 class="ch-kicker">
              Label
            </h2>
            <Select
              :model-value="menuValue || undefined"
              :disabled="changeEmpty"
              @update:model-value="onAssignId"
            >
              <SelectTrigger class="w-auto min-w-40" :title="changeMenuTitle">
                <SelectValue placeholder="Choose a label…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="row in changeLabels" :key="row.id" :value="row.id">
                  <span :style="{ paddingLeft: `${row.depth * 12}px` }">{{ row.name }}</span>
                </SelectItem>
              </SelectContent>
            </Select>
          </section>
        </template>

        <section class="ch-panel">
          <h2 class="ch-kicker">
            Triage
          </h2>
          <!-- Protect or remove the observation — not a quality rating. -->
          <p v-if="selected.guess" class="mb-3">
            {{ selected.guess }}
          </p>
          <div class="flex flex-wrap items-center gap-1.5">
            <button
              class="ch-btn ch-btn-outline"
              :class="selected.comment.verified
                ? 'border-[var(--ch-color-primary)] bg-[var(--ch-color-primary)] text-[var(--ch-color-primary-foreground)] hover:border-black hover:bg-black'
                : ''"
              type="button"
              :aria-pressed="selected.comment.verified"
              :title="selected.comment.verified
                ? 'Click to unprotect so Delete is available again.'
                : 'Stamp this observation as verified (wording, context, worth keeping as evidence). Does not confirm the label assignment.'"
              @click="emit('verify')"
            >
              <span
                class="h-3.5 w-3.5 shrink-0"
                :class="selected.comment.verified ? 'i-fa6-solid:lock' : 'i-fa6-solid:lock-open'"
                aria-hidden="true"
              />
              Verify
            </button>
            <button
              class="ch-btn ch-btn-outline"
              type="button"
              :disabled="selected.comment.verified"
              :title="selected.comment.verified
                ? 'Unverify before deleting.'
                : 'Remove this observation from the store. Undo from History. A later extract can recreate it if the wording is still in the file.'"
              @click="emit('delete')"
            >
              <span class="i-fa6-solid:trash-can h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              Delete
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
              In the manuscript
            </dt><dd>{{ selected.in_manuscript ? 'Yes' : 'No' }}</dd>
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
