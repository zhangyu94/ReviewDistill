<script setup lang="ts">
import {
  commentPageTitle,
  nextCommentTitle,
  pagerItems,
  previousCommentTitle,
} from '../../workbench/pagination.ts'

const props = defineProps<{
  pageCount: number
}>()

const currentPage = defineModel<number>({ required: true })

function go(page: number) {
  if (page < 1 || page > props.pageCount || page === currentPage.value) { return }
  currentPage.value = page
}
</script>

<template>
  <nav
    v-if="pageCount > 0"
    class="flex shrink-0 items-center justify-center gap-0.5 border-t border-[var(--ch-color-border)] px-2 py-1.5"
    aria-label="Comments"
  >
    <span class="inline-flex" :title="previousCommentTitle(currentPage)">
      <button
        class="ch-btn ch-btn-outline min-w-6 px-1.5"
        type="button"
        aria-label="Previous comment"
        :disabled="currentPage <= 1"
        @click="go(currentPage - 1)"
      >
        ‹
      </button>
    </span>
    <template v-for="(item, index) in pagerItems(currentPage, pageCount)" :key="`${item}-${index}`">
      <span v-if="item === 'ellipsis'" class="ch-muted-text px-1">…</span>
      <button
        v-else
        class="ch-btn min-w-6 px-1.5"
        :class="item === currentPage ? 'ch-btn-default' : 'ch-btn-outline'"
        type="button"
        :title="commentPageTitle(item, pageCount, currentPage)"
        :aria-current="item === currentPage ? 'page' : undefined"
        :aria-label="commentPageTitle(item, pageCount, currentPage)"
        @click="go(item)"
      >
        {{ item }}
      </button>
    </template>
    <span class="inline-flex" :title="nextCommentTitle(currentPage, pageCount)">
      <button
        class="ch-btn ch-btn-outline min-w-6 px-1.5"
        type="button"
        aria-label="Next comment"
        :disabled="currentPage >= pageCount"
        @click="go(currentPage + 1)"
      >
        ›
      </button>
    </span>
  </nav>
</template>
