<script setup lang="ts">
import type { HistoryEvent } from '../../api/client.ts'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchHistory, redoHistory, undoHistory } from '../../api/client.ts'
import {
  historyDetailsOf,
  historyEventHasExtra,
  historyHasComments,
  historyHasQuotes,
  historyShowExplanation,
} from '../../workbench/historyDetails.ts'
import { formatHistoryTime } from '../../workbench/historyTime.ts'
import { useWorkbenchStore } from '../../workbench/workbenchStore.ts'

const store = useWorkbenchStore()
const route = useRoute()
const open = ref(false)
const events = ref<HistoryEvent[]>([])
const canUndo = ref(false)
const canRedo = ref(false)
const busy = ref(false)
const error = ref('')
const expandedId = ref('')
const expandedEvent = computed(() => events.value.find((event) => event.id === expandedId.value))
const expandedDetails = computed(() => expandedEvent.value ? historyDetailsOf(expandedEvent.value) : null)

async function load() {
  const body = await fetchHistory()
  events.value = body.events
  canUndo.value = body.can_undo
  canRedo.value = body.can_redo
  if (!events.value.some((event) => event.id === expandedId.value)) {
    expandedId.value = ''
  }
}

async function show() {
  open.value = true
}

function hide() {
  open.value = false
  expandedId.value = ''
}

function toggle(id: string) {
  expandedId.value = expandedId.value === id ? '' : id
}

watch(open, (value) => {
  if (!value) { return }
  error.value = ''
  void load().catch((err) => {
    error.value = err instanceof Error ? err.message : String(err)
  })
})

async function wrap(fn: () => Promise<unknown>) {
  if (busy.value) { return }
  busy.value = true
  error.value = ''
  try {
    await fn()
    await load()
    const labelId = typeof route.params.id === 'string' ? route.params.id : ''
    await store.refreshAfterHistory(labelId)
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}
</script>

<template>
  <button
    class="ch-chip ch-chip-idle gap-1"
    type="button"
    title="Chronological log of taxonomy and assignment changes"
    @click="show"
  >
    <span class="i-fa6-solid:clock-rotate-left h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    History
  </button>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="hide"
  >
    <div class="flex h-[min(36rem,80vh)] w-full max-w-2xl flex-col overflow-hidden rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] text-xs shadow-lg">
      <div class="flex shrink-0 items-center gap-1.5 border-b border-[var(--ch-color-border)] px-3 py-2">
        <h2 class="mr-2 font-semibold">
          History
        </h2>
        <span class="inline-flex" :title="canUndo ? 'Reverse the latest history event' : 'Nothing to undo'">
          <button
            class="ch-btn ch-btn-outline"
            type="button"
            :disabled="busy || !canUndo"
            @click="wrap(undoHistory)"
          >
            <span class="i-fa6-solid:arrow-rotate-left h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            Undo
          </button>
        </span>
        <span class="inline-flex" :title="canRedo ? 'Reapply the last undone event' : 'Nothing to redo'">
          <button
            class="ch-btn ch-btn-outline"
            type="button"
            :disabled="busy || !canRedo"
            @click="wrap(redoHistory)"
          >
            <span class="i-fa6-solid:arrow-rotate-right h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            Redo
          </button>
        </span>
        <p v-if="error" class="ch-error-text min-w-0 flex-1 truncate">
          {{ error }}
        </p>
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
      <div class="min-h-0 flex-1 overflow-auto">
        <div
          v-for="event in events"
          :key="event.id"
          class="border-b border-[var(--ch-color-border)]"
          :class="event.undone ? 'ch-muted-text' : ''"
        >
          <div class="flex items-start">
            <div class="min-w-0 flex-1 px-3 py-1.5">
              <div class="uppercase tracking-[0.06em]">
                {{ event.event_type }}
              </div>
              <strong :class="event.undone ? 'font-normal' : ''">{{ event.summary }}</strong>
              <div class="ch-muted-text" :title="event.created_at">
                {{ formatHistoryTime(event.created_at) }}
              </div>
            </div>
            <button
              v-if="historyEventHasExtra(event)"
              class="ch-btn ch-btn-outline m-1.5 shrink-0 px-1.5"
              type="button"
              :title="expandedId === event.id ? 'Hide details' : 'Show details'"
              :aria-label="expandedId === event.id ? 'Hide details' : 'Show details'"
              :aria-expanded="expandedId === event.id"
              @click="toggle(event.id)"
            >
              <span
                class="h-3.5 w-3.5"
                :class="expandedId === event.id ? 'i-fa6-solid:chevron-down' : 'i-fa6-solid:chevron-right'"
                aria-hidden="true"
              />
            </button>
          </div>
          <div
            v-if="expandedId === event.id && expandedEvent && expandedDetails"
            class="flex flex-col gap-2 px-3 pb-2"
          >
            <!-- Server-built details only; do not stringify event.payload. -->
            <p
              v-if="historyShowExplanation(expandedDetails.explanation, expandedEvent.summary)"
            >
              {{ expandedDetails.explanation }}
            </p>
            <section
              v-if="historyHasQuotes(expandedDetails)"
              class="flex flex-col gap-2"
            >
              <section
                v-for="(quote, index) in expandedDetails.quotes"
                :key="`quote-${event.id}-${index}`"
                class="ch-panel"
              >
                <h3 class="ch-kicker">
                  {{ quote.heading }}
                </h3>
                <p class="ch-prose whitespace-pre-wrap">
                  {{ quote.body }}
                </p>
              </section>
            </section>
            <section
              v-if="historyHasComments(expandedDetails)"
              class="flex flex-col gap-2"
            >
              <section
                v-for="(comment, index) in expandedDetails.comments"
                :key="`comment-${event.id}-${index}`"
                class="ch-panel"
              >
                <h3 class="ch-kicker mb-0">
                  Comment
                </h3>
                <p v-if="comment.label_name" class="ch-muted-text mb-1.5">
                  {{ comment.label_name }}
                </p>
                <p class="ch-prose whitespace-pre-wrap" :class="comment.label_name ? '' : 'mt-1.5'">
                  {{ comment.text }}
                </p>
              </section>
            </section>
          </div>
        </div>
        <p v-if="events.length === 0 && !error" class="ch-muted-text p-3">
          No events.
        </p>
      </div>
    </div>
  </div>
</template>
