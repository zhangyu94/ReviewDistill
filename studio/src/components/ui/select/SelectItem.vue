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
        <svg
          width="10"
          height="10"
          viewBox="0 0 448 512"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M438.6 105.4c12.5 12.5 12.5 32.8 0 45.3l-256 256c-12.5 12.5-32.8 12.5-45.3 0l-128-128c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0L160 338.7 393.4 105.4c12.5-12.5 32.8-12.5 45.3 0z" />
        </svg>
      </SelectItemIndicator>
    </span>
    <SelectItemText>
      <slot />
    </SelectItemText>
  </SelectItem>
</template>
