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
      <span class="i-fa6-solid:chevron-down h-2.5 w-2.5 shrink-0 opacity-50" aria-hidden="true" />
    </SelectIcon>
  </SelectTrigger>
</template>
