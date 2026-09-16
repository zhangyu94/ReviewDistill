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

function emptyInbox() {
  return {
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
  }
}

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

  it('clears assignmentNotice on refreshAfterHistory', async () => {
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
    const store = useWorkbenchStore()
    store.setAssignmentNotice('11 comments were labeled. They appear in Label Taxonomy. Change any that are wrong.')
    await store.refreshAfterHistory('')
    expect(store.assignmentNotice).toBe('')
  })

  it('setAssignmentNotice ignores empty so a 0-count retry keeps the last notice', () => {
    const store = useWorkbenchStore()
    store.setAssignmentNotice('1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.')
    store.setAssignmentNotice('')
    expect(store.assignmentNotice).toBe(
      '1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.',
    )
  })

  it('setErrorNotice leaves the assignment notice so dismissing the error restores it', () => {
    const store = useWorkbenchStore()
    store.setAssignmentNotice('1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.')
    store.setErrorNotice('LLM request failed (deepseek): Connection timed out after 60.0 seconds.')
    expect(store.errorNotice).toBe(
      'LLM request failed (deepseek): Connection timed out after 60.0 seconds.',
    )
    expect(store.assignmentNotice).toBe(
      '1 comment was labeled. It appears in Label Taxonomy. Change it if it is wrong.',
    )
  })

  it('setErrorNotice clears a matching Label Details error', () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    const store = useWorkbenchStore()
    store.error = unreachable
    store.setErrorNotice(unreachable)
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
  })

  it('does not paint Label Details when invalidate fails after loadLabel', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    let rejectInbox: (err: Error) => void = () => {}
    let rejectLabel: (err: Error) => void = () => {}
    vi.mocked(fetchInbox).mockImplementationOnce(() => new Promise((_, reject) => {
      rejectInbox = reject
    }))
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    vi.mocked(fetchLabel).mockImplementationOnce(() => new Promise((_, reject) => {
      rejectLabel = reject
    }))
    const store = useWorkbenchStore()
    const pending = store.invalidate({ inbox: true, labels: true, label: true }, 't1').catch((err) => {
      store.setErrorNotice(err instanceof Error ? err.message : String(err))
    })
    rejectLabel(new Error(unreachable))
    await vi.waitFor(() => {
      expect(store.errorNotice).toBe(unreachable)
    })
    expect(store.error).toBe('')
    rejectInbox(new Error(unreachable))
    await pending
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
  })

  it('clears errorNotice on refreshAfterHistory', async () => {
    vi.mocked(fetchInbox).mockResolvedValue(emptyInbox())
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    const store = useWorkbenchStore()
    store.setErrorNotice('LLM request failed (deepseek): Connection timed out after 60.0 seconds.')
    await store.refreshAfterHistory('')
    expect(store.errorNotice).toBe('')
  })

  it('refreshAfterHistory failures go to the error snackbar, not Label Details', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    vi.mocked(fetchInbox).mockRejectedValue(new Error(unreachable))
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    vi.mocked(fetchLabel).mockRejectedValue(new Error(unreachable))
    const store = useWorkbenchStore()
    await expect(store.refreshAfterHistory('t1')).rejects.toThrow(unreachable)
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
  })

  it('starts Label Details in a loading state so a deep link does not flash Could not load', () => {
    const store = useWorkbenchStore()
    expect(store.labelLoading).toBe(true)
  })

  it('clears a previous 404 while the next label is in flight', async () => {
    vi.mocked(fetchLabel)
      .mockRejectedValueOnce(new ApiError('Unknown label', 404))
      .mockImplementationOnce(() => new Promise(() => {}))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.missing).toBe(true)
    void store.loadLabel('t2')
    expect(store.labelLoading).toBe(true)
    expect(store.missing).toBe(false)
    expect(store.error).toBe('')
  })

  it('clears a previous 500 while the next label is in flight', async () => {
    vi.mocked(fetchLabel)
      .mockRejectedValueOnce(new ApiError('store corrupt', 500))
      .mockImplementationOnce(() => new Promise(() => {}))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.error).toBe('store corrupt')
    void store.loadLabel('t2')
    expect(store.labelLoading).toBe(true)
    expect(store.error).toBe('')
    expect(store.missing).toBe(false)
  })

  it('keeps a label-only 500 in Label Details when the rest of loadAll succeeds', async () => {
    vi.mocked(fetchInbox).mockResolvedValue(emptyInbox())
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError('store corrupt', 500))
    const store = useWorkbenchStore()
    await store.loadAll('t1')
    expect(store.error).toBe('store corrupt')
    expect(store.errorNotice).toBe('')
    expect(store.labelLoading).toBe(false)
  })

  it('does not paint Label Details when loadLabel finishes after loadAll already set the snackbar', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    let rejectLabel: (err: Error) => void = () => {}
    vi.mocked(fetchInbox).mockRejectedValue(new Error(unreachable))
    vi.mocked(fetchLabels).mockResolvedValue({ forest: [] })
    vi.mocked(fetchLabel).mockImplementationOnce(() => new Promise((_, reject) => {
      rejectLabel = reject
    }))
    const store = useWorkbenchStore()
    const pending = store.loadAll('t1')
    await vi.waitFor(() => {
      expect(store.errorNotice).toBe(unreachable)
    })
    expect(store.error).toBe('')
    expect(store.labelLoading).toBe(true)
    rejectLabel(new Error(unreachable))
    await pending
    expect(store.error).toBe('')
    expect(store.labelLoading).toBe(false)
  })

  it('loadAll failures go to the error snackbar, not Label Details', async () => {
    vi.mocked(fetchInbox).mockRejectedValue(new Error('inbox down'))
    const store = useWorkbenchStore()
    await store.loadAll()
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe('inbox down')
  })

  it('does not repeat a page-load failure in Label Details when a label is selected', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    vi.mocked(fetchInbox).mockRejectedValue(new Error(unreachable))
    vi.mocked(fetchLabels).mockRejectedValue(new Error(unreachable))
    vi.mocked(fetchLabel).mockRejectedValue(new Error(unreachable))
    const store = useWorkbenchStore()
    await store.loadAll('t1')
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
  })

  it('does not paint Label Details when the snackbar already has the same error', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    vi.mocked(fetchLabel).mockRejectedValue(new Error(unreachable))
    const store = useWorkbenchStore()
    store.setErrorNotice(unreachable)
    await store.loadLabel('t1')
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
  })

  it('treats a 500 label load as an error, not missing', async () => {
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError('store corrupt', 500))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.missing).toBe(false)
    expect(store.error).toBe('store corrupt')
    expect(store.errorNotice).toBe('')
    expect(store.labelLoading).toBe(false)
  })

  it('sends an unreachable label load to the snackbar, not Label Details', async () => {
    const unreachable
      = 'Cannot reach the ReviewDistill server. Make sure it is running, then reload this page.'
    vi.mocked(fetchLabel).mockRejectedValue(new ApiError(unreachable, 502))
    const store = useWorkbenchStore()
    await store.loadLabel('t1')
    expect(store.error).toBe('')
    expect(store.errorNotice).toBe(unreachable)
    expect(store.labelLoading).toBe(false)
  })

  it('keeps labelLoading true until fetchLabel settles', async () => {
    const labelDetail = {
      id: 't1',
      name: 't1',
      parent_id: null,
      path: [{ id: 't1', name: 't1' }],
      definition: '',
      status: 'active',
      examples: [],
      comments: [],
    }
    let finish: (value: typeof labelDetail) => void = () => {}
    vi.mocked(fetchLabel).mockImplementationOnce(() => new Promise((resolve) => {
      finish = resolve
    }))
    const store = useWorkbenchStore()
    const pending = store.loadLabel('t1')
    expect(store.labelLoading).toBe(true)
    finish(labelDetail)
    await pending
    expect(store.labelLoading).toBe(false)
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
