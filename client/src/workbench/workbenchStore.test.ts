import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fetchInbox, fetchLabel, fetchLabels } from '../api/client.ts'
import { useWorkbenchStore } from './workbenchStore.ts'

vi.mock('../api/client.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client.ts')>()
  return {
    ...actual,
    fetchInbox: vi.fn(),
    fetchLabels: vi.fn(),
    fetchLabel: vi.fn(),
  }
})

describe('workbenchStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(fetchInbox).mockReset()
    vi.mocked(fetchLabels).mockReset()
    vi.mocked(fetchLabel).mockReset()
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
      labels: [],
      items: [],
      working_items: [],
      progress: {
        working_set: 0,
        unlabeled: 0,
        labeled: 0,
        unreviewed: 0,
        verified: 0,
      },
    })
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    const store = useWorkbenchStore()
    await store.invalidate({ inbox: true, labels: true })
    expect(store.inbox?.unlabeled_count).toBe(1)
    expect(store.labels).toEqual({ forest: [] })
  })

  it('refreshAfterHistory reloads label details for the open label', async () => {
    vi.mocked(fetchInbox).mockResolvedValue({
      unlabeled_count: 0,
      pending_code_count: 0,
      llm_provider: null,
      labels: [],
      items: [],
      working_items: [],
      progress: {
        working_set: 0,
        unlabeled: 0,
        labeled: 0,
        unreviewed: 0,
        verified: 0,
      },
    })
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    vi.mocked(fetchLabel).mockResolvedValue({
      id: 't1',
      name: 'Overclaiming',
      parent_id: null,
      path: [{ id: 't1', name: 'Overclaiming' }],
      definition: 'after undo',
      status: 'active',
      examples: [],
      comments: [],
    })
    const store = useWorkbenchStore()
    await store.refreshAfterHistory('t1')
    expect(fetchLabel).toHaveBeenCalledWith('t1')
    expect(store.label?.definition).toBe('after undo')
  })

  it('treats a 500 label load as an error, not missing', async () => {
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError('store corrupt', 500))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.missing).toBe(false)
    expect(store.error).toBe('store corrupt')
  })

  it('treats a 404 label load as missing', async () => {
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError('Unknown label', 404))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.missing).toBe(true)
    expect(store.label).toBeNull()
    expect(store.error).toBe('')
  })

  it('clears a previous missing flag when loading with no label id', async () => {
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError('Unknown label', 404))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.missing).toBe(true)
    await store.loadLabel('')
    expect(store.missing).toBe(false)
    expect(store.label).toBeNull()
    expect(store.error).toBe('')
    expect(fetchLabel).toHaveBeenCalledTimes(1)
  })

  it('ignores a stale label response when a newer load is in flight', async () => {
    const labelDetail = (id: string) => ({
      id,
      name: id,
      parent_id: null,
      path: [{ id, name: id }],
      definition: '',
      status: 'active',
      examples: [],
      comments: [],
    })
    let finishFirst: (value: ReturnType<typeof labelDetail>) => void = () => {}
    vi.mocked(fetchLabel)
      .mockImplementationOnce(() => new Promise((resolve) => {
        finishFirst = resolve
      }))
      .mockResolvedValueOnce(labelDetail('t2'))
    const store = useWorkbenchStore()
    const first = store.loadLabel('t1')
    const second = store.loadLabel('t2')
    finishFirst(labelDetail('t1'))
    await Promise.all([first, second])
    expect(store.label?.id).toBe('t2')
  })

  it('ignores a stale 404 when a newer label load succeeded', async () => {
    const labelDetail = (id: string) => ({
      id,
      name: id,
      parent_id: null,
      path: [{ id, name: id }],
      definition: '',
      status: 'active',
      examples: [],
      comments: [],
    })
    let failFirst: (err: ApiError) => void = () => {}
    vi.mocked(fetchLabel)
      .mockImplementationOnce(() => new Promise((_, reject) => {
        failFirst = reject
      }))
      .mockResolvedValueOnce(labelDetail('t2'))
    const store = useWorkbenchStore()
    const first = store.loadLabel('t1')
    const second = store.loadLabel('t2')
    failFirst(new ApiError('Unknown label', 404))
    await Promise.all([first, second])
    expect(store.label?.id).toBe('t2')
    expect(store.missing).toBe(false)
  })
})
