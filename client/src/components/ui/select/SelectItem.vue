<script setup lang="ts">
import type { SelectItemProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { SelectItem, SelectItemIndicator, SelectItemText } from 'reka-ui'
import { computed } from 'vue'

const props = defineProps<SelectItemProps & { class?: HTMLAttributes['class'] }>()
const itemBind = computed(() => {
  const { class: _c, ...rest } = props
  return rest
})
</script>

<template>
  <SelectItem
    v-bind="itemBind"
    class="relative flex w-full cursor-default items-center rounded-[var(--ch-radius)] py-1 pr-6 pl-2 text-xs outline-none data-[highlighted]:bg-[var(--ch-color-background-muted)] data-[highlighted]:text-[var(--ch-color-foreground)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
    :class="[props.class]"
  >
    <span
      class="absolute right-1.5 flex items-center justify-center"
      style="width: 14px; height: 14px"
    >
      <SelectItemIndicator>
        <span class="i-fa6-solid:check h-2.5 w-2.5" aria-hidden="true" />
      </SelectItemIndicator>
    </span>
    <SelectItemText>
      <slot />
    </SelectItemText>
  </SelectItem>
</template>
