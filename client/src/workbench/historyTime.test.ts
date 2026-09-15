import { describe, expect, it } from 'vitest'
import { formatHistoryTime } from './historyTime'

const NOW = new Date('2026-09-14T12:00:00Z')
const UTC = { now: NOW, timeZone: 'UTC' } as const

describe('formatHistoryTime', () => {
  it('shows month, day, and time to the minute without seconds or offset', () => {
    expect(formatHistoryTime('2026-09-14T03:16:08.034110+00:00', UTC)).toBe('Sep 14, 03:16')
  })

  it('includes the year when it differs from now', () => {
    expect(formatHistoryTime('2025-01-02T15:04:05.123Z', UTC)).toBe('Jan 2, 2025, 15:04')
  })

  it('returns an empty string for missing or invalid timestamps', () => {
    expect(formatHistoryTime('')).toBe('')
    expect(formatHistoryTime('not-a-date')).toBe('')
  })
})
