<script setup lang="ts">
import type { HistoryEvent } from '../api/client.ts'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchHistory, redoHistory, undoHistory } from '../api/client.ts'
import { useWorkbenchStore } from '../workbench/workbenchStore.ts'

const route = useRoute()
const router = useRouter()
const store = useWorkbenchStore()
const events = ref<HistoryEvent[]>([])
const canUndo = ref(false)
const canRedo = ref(false)
const busy = ref(false)
const error = ref('')
const selectedId = computed(() => {
  const q = route.query.id
  const id = typeof q === 'string' ? q : undefined
  if (id && events.value.some((event) => event.id === id)) { return id }
  return events.value[0]?.id
})
const selected = computed(() => events.value.find((event) => event.id === selectedId.value))

async function load() {
  const body = await fetchHistory()
  events.value = body.events
  canUndo.value = body.can_undo
  canRedo.value = body.can_redo
}

async function wrap(fn: () => Promise<unknown>) {
  if (busy.value) { return }
  busy.value = true
  error.value = ''
  try {
    await fn()
    await load()
    await store.invalidate({ inbox: true, taxonomy: true })
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
  finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-[var(--ch-color-background)]">
    <div class="flex shrink-0 items-center gap-1.5 border-b border-[var(--ch-color-border)] px-2 py-1.5">
      <span class="inline-flex" :title="canUndo ? 'Reverse the latest history event' : 'Nothing to undo'">
        <button
          class="ch-btn ch-btn-outline"
          type="button"
          :disabled="busy || !canUndo"
          @click="wrap(undoHistory)"
        >
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
          Redo
        </button>
      </span>
      <p v-if="error" class="ch-muted-text truncate">
        {{ error }}
      </p>
    </div>
    <div class="flex min-h-0 flex-1">
      <div class="w-80 shrink-0 overflow-auto border-r border-[var(--ch-color-border)] text-xs">
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
          @click="router.replace({ query: { id: event.id } })"
        >
          <div class="uppercase tracking-[0.06em]">
            {{ event.event_type }}
          </div>
          <strong :class="event.undone ? 'font-normal' : ''">{{ event.summary }}</strong>
          <div class="ch-muted-text">
            {{ event.created_at }}
          </div>
        </button>
        <p v-if="events.length === 0" class="ch-muted-text p-2">
          No events.
        </p>
      </div>
      <div class="min-h-0 min-w-0 flex-1 overflow-auto p-3 text-xs">
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
</template>
