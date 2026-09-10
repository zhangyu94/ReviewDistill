<script setup lang="ts">
import type { SelectContentEmits, SelectContentProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { SelectContent, SelectPortal, SelectViewport, useForwardPropsEmits } from 'reka-ui'
import { computed } from 'vue'
import { SELECT_CONTENT_POSITION, SELECT_CONTENT_SIDE_OFFSET } from './selectPosition.ts'

const props = withDefaults(defineProps<SelectContentProps & { class?: HTMLAttributes['class'] }>(), {
  position: SELECT_CONTENT_POSITION,
  sideOffset: SELECT_CONTENT_SIDE_OFFSET,
})
const emits = defineEmits<SelectContentEmits>()
const forwarded = useForwardPropsEmits(
  computed(() => {
    const { class: _c, position: _p, ...rest } = props
    return rest
  }),
  emits,
)
</script>

<template>
  <!-- Always popper: item-aligned overlays the trigger (same ChartHarness fix). -->
  <SelectPortal>
    <SelectContent
      v-bind="forwarded"
      :position="SELECT_CONTENT_POSITION"
      :side-offset="props.sideOffset ?? SELECT_CONTENT_SIDE_OFFSET"
      class="z-[100] max-h-60 min-w-[8rem] w-[var(--reka-select-trigger-width)] overflow-hidden rounded-[var(--ch-radius)] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] text-xs text-[var(--ch-color-body)] shadow-md"
      :class="[props.class]"
    >
      <SelectViewport class="p-0.5">
        <slot />
      </SelectViewport>
    </SelectContent>
  </SelectPortal>
</template>
