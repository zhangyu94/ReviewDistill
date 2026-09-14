import type { CommentProgress } from '../api/client.ts'

export const EMPTY_PROGRESS: CommentProgress = {
  working_set: 0,
  unlabeled: 0,
  labeled: 0,
  unreviewed: 0,
  verified: 0,
  dropped: 0,
}

export type ProgressPartKey = 'working_set' | 'unlabeled' | 'verified' | 'dropped'

const PART_TITLE: Record<ProgressPartKey, string> = {
  working_set: 'The number of comments to distill. They are not dropped, and they are still in the manuscript or already verified.',
  unlabeled: 'The number of comments to distill that have no issue type. The Unlabeled chip is the inbox queue, not this count.',
  verified: 'The number of comments that are quality-assured. Does not confirm the issue type.',
  dropped: 'The number of comments not to distill (too local, or a bad extract). History is kept.',
}

export function progressHeadlineLabel(): string {
  return 'to distill'
}

export function progressPartTitle(key: ProgressPartKey): string {
  return PART_TITLE[key]
}

export function progressParts(progress: CommentProgress): { key: Exclude<ProgressPartKey, 'working_set'>, n: number }[] {
  return [
    { key: 'unlabeled', n: progress.unlabeled },
    { key: 'verified', n: progress.verified },
    { key: 'dropped', n: progress.dropped },
  ]
}
