<script setup lang="ts">
import type { HistoryEvent } from '../../api/client.ts'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchHistory, redoHistory, undoHistory } from '../../api/client.ts'
import { useWorkbenchStore } from '../../workbench/workbenchStore.ts'

const store = useWorkbenchStore()
const route = useRoute()
const open = ref(false)
const events = ref<HistoryEvent[]>([])
const canUndo = ref(false)
const canRedo = ref(false)
const busy = ref(false)
const error = ref('')
const selectedId = ref('')
const selected = computed(() => events.value.find((event) => event.id === selectedId.value))

async function load() {
  const body = await fetchHistory()
  events.value = body.events
  canUndo.value = body.can_undo
  canRedo.value = body.can_redo
  if (!events.value.some((event) => event.id === selectedId.value)) {
    selectedId.value = events.value[0]?.id ?? ''
  }
}

async function show() {
  open.value = true
}

function hide() {
  open.value = false
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
    const issueId = typeof route.params.id === 'string' ? route.params.id : ''
    await store.refreshAfterHistory(issueId)
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
    class="ch-chip ch-chip-idle ml-auto gap-1"
    type="button"
    title="Chronological log of taxonomy and coding changes"
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
    <div class="flex h-[min(36rem,80vh)] w-full max-w-4xl flex-col overflow-hidden rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] text-xs shadow-lg">
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
        <p v-if="error" class="ch-muted-text min-w-0 flex-1 truncate">
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
      <div class="flex min-h-0 flex-1">
        <div class="w-72 shrink-0 overflow-auto border-r border-[var(--ch-color-border)]">
          <button
            v-for="event in events"
            :key="event.id"
            type="button"
            class="block w-full border-b border-[var(--ch-color-border)] px-2 py-1.5 text-left"
            :class="[
              event.id === selectedId ? 'bg-[var(--ch-color-background-muted)]' : '',
              event.undone ? 'ch-muted-text' : '',
            ]"
            :title="event.undone ? `${event.summary} (undone)` : event.summary"
            @click="selectedId = event.id"
          >
            <div class="uppercase tracking-[0.06em]">
              {{ event.event_type }}
            </div>
            <strong :class="event.undone ? 'font-normal' : ''">{{ event.summary }}</strong>
            <div class="ch-muted-text">
              {{ event.created_at }}
            </div>
          </button>
          <p v-if="events.length === 0 && !error" class="ch-muted-text p-2">
            No events.
          </p>
        </div>
        <div class="min-h-0 min-w-0 flex-1 overflow-auto p-3">
          <template v-if="selected">
            <p class="mb-0.5">
              <strong>{{ selected.summary }}</strong>
            </p>
            <p class="ch-muted-text mb-2">
              {{ selected.event_type }} · {{ selected.created_at }}
            </p>
            <p v-if="selected.undone" class="ch-muted-text mb-2">
              Undone
            </p>
            <pre class="ch-code-block">{{ JSON.stringify(selected.payload, null, 2) }}</pre>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
