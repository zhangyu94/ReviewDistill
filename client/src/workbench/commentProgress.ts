import type { CommentProgress } from '../api/client.ts'

export const EMPTY_PROGRESS: CommentProgress = {
  working_set: 0,
  unlabeled: 0,
  labeled: 0,
  unreviewed: 0,
  verified: 0,
  dropped: 0,
}

export function progressParts(progress: CommentProgress): { key: 'unlabeled' | 'verified' | 'dropped', n: number }[] {
  return [
    { key: 'unlabeled', n: progress.unlabeled },
    { key: 'verified', n: progress.verified },
    { key: 'dropped', n: progress.dropped },
  ]
}
