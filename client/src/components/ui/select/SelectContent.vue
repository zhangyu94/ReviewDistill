<script setup lang="ts">
import type { SelectContentEmits, SelectContentProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { SelectContent, SelectPortal, SelectViewport, useForwardPropsEmits } from 'reka-ui'
import { computed } from 'vue'

const props = withDefaults(defineProps<SelectContentProps & { class?: HTMLAttributes['class'] }>(), {
  position: 'popper',
  sideOffset: 4,
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
      position="popper"
      :side-offset="props.sideOffset ?? 4"
      class="z-[100] max-h-60 min-w-[8rem] w-[var(--reka-select-trigger-width)] overflow-hidden rounded-[var(--ch-radius)] border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] text-xs text-[var(--ch-color-body)] shadow-md"
      :class="[props.class]"
    >
      <SelectViewport class="p-0.5">
        <slot />
      </SelectViewport>
    </SelectContent>
  </SelectPortal>
</template>
