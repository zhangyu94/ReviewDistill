import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchInbox, fetchIssue, fetchTaxonomy } from '../api/client.ts'
import { useWorkbenchStore } from './workbenchStore.ts'

vi.mock('../api/client.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client.ts')>()
  return {
    ...actual,
    fetchInbox: vi.fn(),
    fetchTaxonomy: vi.fn(),
    fetchIssue: vi.fn(),
  }
})

describe('workbenchStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(fetchInbox).mockReset()
    vi.mocked(fetchTaxonomy).mockReset()
    vi.mocked(fetchIssue).mockReset()
  })

  it('opens and closes settings without window events', () => {
    const store = useWorkbenchStore()
    expect(store.settingsOpen).toBe(false)
    store.openSettings()
    expect(store.settingsOpen).toBe(true)
    store.closeSettings()
    expect(store.settingsOpen).toBe(false)
  })

  it('invalidates inbox and taxonomy through the store', async () => {
    vi.mocked(fetchInbox).mockResolvedValue({
      unlabeled_count: 1,
      pending_code_count: 0,
      llm_provider: null,
      issues: [],
      items: [],
      working_items: [],
      progress: {
        working_set: 0,
        unlabeled: 0,
        labeled: 0,
        unreviewed: 0,
        verified: 0,
        dropped: 0,
      },
    })
    vi.mocked(fetchTaxonomy).mockResolvedValue({ forest: [] })
    const store = useWorkbenchStore()
    await store.invalidate({ inbox: true, taxonomy: true })
    expect(store.inbox?.unlabeled_count).toBe(1)
    expect(store.taxonomy).toEqual({ forest: [] })
  })

  it('refreshAfterHistory reloads issue details for the open type', async () => {
    vi.mocked(fetchInbox).mockResolvedValue({
      unlabeled_count: 0,
      pending_code_count: 0,
      llm_provider: null,
      issues: [],
      items: [],
      working_items: [],
      progress: {
        working_set: 0,
        unlabeled: 0,
        labeled: 0,
        unreviewed: 0,
        verified: 0,
        dropped: 0,
      },
    })
    vi.mocked(fetchTaxonomy).mockResolvedValue({ forest: [] })
    vi.mocked(fetchIssue).mockResolvedValue({
      id: 't1',
      name: 'Overclaiming',
      parent_id: null,
      path: [{ id: 't1', name: 'Overclaiming' }],
      definition: 'after undo',
      notes: null,
      status: 'active',
      examples: [],
      counterexamples: [],
      comments: [],
    })
    const store = useWorkbenchStore()
    await store.refreshAfterHistory('t1')
    expect(fetchIssue).toHaveBeenCalledWith('t1')
    expect(store.issue?.definition).toBe('after undo')
  })

  it('treats a 500 issue load as an error, not missing', async () => {
    vi.mocked(fetchIssue).mockRejectedValue(new ApiError('store corrupt', 500))
    const store = useWorkbenchStore()
    await store.loadIssue('t1')
    expect(store.missing).toBe(false)
    expect(store.error).toBe('store corrupt')
  })

  it('treats a 404 issue load as missing', async () => {
    vi.mocked(fetchIssue).mockRejectedValue(new ApiError('Unknown issue type', 404))
    const store = useWorkbenchStore()
    await store.loadIssue('t1')
    expect(store.missing).toBe(true)
    expect(store.issue).toBeNull()
    expect(store.error).toBe('')
  })

  it('clears a previous missing flag when loading with no issue id', async () => {
    vi.mocked(fetchIssue).mockRejectedValue(new ApiError('Unknown issue type', 404))
    const store = useWorkbenchStore()
    await store.loadIssue('t1')
    expect(store.missing).toBe(true)
    await store.loadIssue('')
    expect(store.missing).toBe(false)
    expect(store.issue).toBeNull()
    expect(store.error).toBe('')
    expect(fetchIssue).toHaveBeenCalledTimes(1)
  })

  it('ignores a stale issue response when a newer load is in flight', async () => {
    const issue = (id: string) => ({
      id,
      name: id,
      parent_id: null,
      path: [{ id, name: id }],
      definition: '',
      notes: null,
      status: 'active',
      examples: [],
      counterexamples: [],
      comments: [],
    })
    let finishFirst: (value: ReturnType<typeof issue>) => void = () => {}
    vi.mocked(fetchIssue)
      .mockImplementationOnce(() => new Promise((resolve) => {
        finishFirst = resolve
      }))
      .mockResolvedValueOnce(issue('t2'))
    const store = useWorkbenchStore()
    const first = store.loadIssue('t1')
    const second = store.loadIssue('t2')
    finishFirst(issue('t1'))
    await Promise.all([first, second])
    expect(store.issue?.id).toBe('t2')
  })

  it('ignores a stale 404 when a newer issue load succeeded', async () => {
    const issue = (id: string) => ({
      id,
      name: id,
      parent_id: null,
      path: [{ id, name: id }],
      definition: '',
      notes: null,
      status: 'active',
      examples: [],
      counterexamples: [],
      comments: [],
    })
    let failFirst: (err: ApiError) => void = () => {}
    vi.mocked(fetchIssue)
      .mockImplementationOnce(() => new Promise((_, reject) => {
        failFirst = reject
      }))
      .mockResolvedValueOnce(issue('t2'))
    const store = useWorkbenchStore()
    const first = store.loadIssue('t1')
    const second = store.loadIssue('t2')
    failFirst(new ApiError('Unknown issue type', 404))
    await Promise.all([first, second])
    expect(store.issue?.id).toBe('t2')
    expect(store.missing).toBe(false)
  })
})
