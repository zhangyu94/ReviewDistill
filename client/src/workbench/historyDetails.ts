import type { HistoryDetails, HistoryEvent } from '../api/client.ts'

const GENERIC_SUMMARY = /^(?:Merge labels|Split label|Change label assignment|Accept suggested label assignment|Verify comment|Unverify comment|Drop comment|Delete comment|Edit definition|Label with AI)\b/

export function historyDetailsOf(
  event: Pick<HistoryEvent, 'summary'> & { details?: HistoryDetails | null },
): HistoryDetails {
  const details = event.details
  if (details && typeof details.explanation === 'string') {
    return {
      explanation: details.explanation,
      comments: details.comments ?? [],
      quotes: details.quotes ?? [],
    }
  }
  return { explanation: '', comments: [], quotes: [] }
}

export function historyHasComments(details: HistoryDetails): boolean {
  return details.comments.length > 0
}

export function historyHasQuotes(details: HistoryDetails): boolean {
  return details.quotes.length > 0
}

export function historyShowExplanation(explanation: string, summary: string): boolean {
  // Chevron extra: skip an explanation that only restates the list-line summary.
  const extra = explanation.trim()
  const title = summary.trim()
  if (!extra) {
    return false
  }
  if (normalizeHistoryCopy(extra) === normalizeHistoryCopy(title)) {
    return false
  }
  if (GENERIC_SUMMARY.test(title)) {
    return true
  }
  if (/\. .+/.test(extra)) {
    return true
  }
  return /\b(?:under|subtree|descendant|ungrouped|Unlabeled|top of the taxonomy)\b/i.test(extra)
}

export function historyHasExtra(details: HistoryDetails, summary: string): boolean {
  return historyShowExplanation(details.explanation, summary)
    || historyHasComments(details)
    || historyHasQuotes(details)
}

export function historyEventHasExtra(
  event: Pick<HistoryEvent, 'summary'> & { details?: HistoryDetails | null },
): boolean {
  return historyHasExtra(historyDetailsOf(event), event.summary)
}

function normalizeHistoryCopy(value: string): string {
  return value
    .toLowerCase()
    .replace(/→/g, ' to ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\b(?:renamed|rename|added|add|moved|move|flattened|flatten|removed|remove|deactivated|deactivate|the label)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
