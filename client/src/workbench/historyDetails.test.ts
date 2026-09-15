import { describe, expect, it } from 'vitest'
import {
  historyDetailsOf,
  historyEventHasExtra,
  historyHasComments,
  historyHasExtra,
  historyHasQuotes,
  historyShowExplanation,
} from './historyDetails'

describe('historyDetailsOf', () => {
  it('returns server details when present', () => {
    expect(historyDetailsOf({
      summary: 'Change label assignment',
      details: {
        explanation: 'Assigned this comment to Overclaiming.',
        comments: [{ text: 'Too strong.', label_name: 'Overclaiming' }],
        quotes: [],
      },
    })).toEqual({
      explanation: 'Assigned this comment to Overclaiming.',
      comments: [{ text: 'Too strong.', label_name: 'Overclaiming' }],
      quotes: [],
    })
  })

  it('does not copy the summary into the explanation when details are missing', () => {
    expect(historyDetailsOf({ summary: 'Change label' })).toEqual({
      explanation: '',
      comments: [],
      quotes: [],
    })
  })
})

describe('historyShowExplanation', () => {
  it('hides a rename restatement of the list title', () => {
    expect(historyShowExplanation(
      'Renamed Missing intro to Missing intro.',
      'Rename Missing intro → Missing intro',
    )).toBe(false)
  })

  it('hides an add restatement of the list title', () => {
    expect(historyShowExplanation(
      'Added the label New label.',
      'Add New label',
    )).toBe(false)
  })

  it('shows merge names when the list title is generic', () => {
    expect(historyShowExplanation(
      'Merged Type A, Type B into Overclaiming.',
      'Merge labels',
    )).toBe(true)
  })

  it('shows a second sentence such as moving labels onto ungrouped', () => {
    expect(historyShowExplanation(
      'Added the label New label. Existing label assignments on the parent were moved onto ungrouped.',
      'Add New label',
    )).toBe(true)
  })

  it('shows where a label was moved', () => {
    expect(historyShowExplanation(
      'Moved Overclaiming under Claims.',
      'Move Overclaiming',
    )).toBe(true)
  })

  it('shows a delete explanation under a generic list title', () => {
    expect(historyShowExplanation(
      'Deleted this comment.',
      'Delete comment',
    )).toBe(true)
  })

  it('shows an unverify explanation under a generic list title', () => {
    expect(historyShowExplanation(
      'Unverified this comment.',
      'Unverify comment',
    )).toBe(true)
  })
})

describe('historyHasExtra', () => {
  it('is false when a rename only restates the title', () => {
    const details = historyDetailsOf({
      summary: 'Rename A → B',
      details: { explanation: 'Renamed A to B.', comments: [], quotes: [] },
    })
    expect(historyHasComments(details)).toBe(false)
    expect(historyHasQuotes(details)).toBe(false)
    expect(historyHasExtra(details, 'Rename A → B')).toBe(false)
  })

  it('is true when there are comments or quotes', () => {
    const details = historyDetailsOf({
      summary: 'Edit definition',
      details: {
        explanation: 'Edited the definition of Overclaiming.',
        comments: [],
        quotes: [{ heading: 'Definition', body: 'A claim is stronger than the evidence.' }],
      },
    })
    expect(historyHasQuotes(details)).toBe(true)
    expect(historyHasExtra(details, 'Edit definition')).toBe(true)
  })
})

describe('historyEventHasExtra', () => {
  it('hides the chevron when the event has no extra details', () => {
    expect(historyEventHasExtra({
      summary: 'Rename A → B',
      details: { explanation: 'Renamed A to B.', comments: [], quotes: [] },
    })).toBe(false)
  })

  it('shows the chevron when the event has a comment', () => {
    expect(historyEventHasExtra({
      summary: 'Change label assignment',
      details: {
        explanation: 'Assigned this comment to Overclaiming.',
        comments: [{ text: 'Too strong.', label_name: 'Overclaiming' }],
        quotes: [],
      },
    })).toBe(true)
  })
})
