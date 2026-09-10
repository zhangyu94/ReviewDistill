<script setup lang="ts">
import type { SelectTriggerProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { SelectIcon, SelectTrigger } from 'reka-ui'
import { computed } from 'vue'

const props = defineProps<SelectTriggerProps & { class?: HTMLAttributes['class'] }>()
const triggerBind = computed(() => {
  const { class: _c, ...rest } = props
  return rest
})
</script>

<template>
  <SelectTrigger
    v-bind="triggerBind"
    class="ch-select min-w-0 justify-between gap-1 text-left"
    :class="[props.class]"
  >
    <slot />
    <SelectIcon as-child>
      <svg
        width="10"
        height="10"
        class="shrink-0 opacity-50"
        viewBox="0 0 448 512"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z" />
      </svg>
    </SelectIcon>
  </SelectTrigger>
</template>
