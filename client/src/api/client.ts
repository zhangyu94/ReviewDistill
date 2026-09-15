export interface LabelOption {
  id: string
  name: string
  parent_id: string | null
}

export interface CommentJson {
  id: string
  project_id: string
  source_type: string
  source_command: string
  file_path: string
  line_number: number
  raw_text: string
  context_text: string
  section: string | null
  git_commit: string | null
  git_url: string | null
  status: string
  verified: boolean
  supersedes_id: string | null
  created_at: string
}

export interface CodingJson {
  id: string
  status: string
  label_id: string | null
  proposed_label_name: string | null
  confidence: number | null
  rationale: string | null
  kind: 'existing' | 'new'
}

export interface InboxItemJson {
  comment: CommentJson
  project_name: string
  permalink: string | null
  guess: string | null
  in_manuscript: boolean
  labeled: boolean
  label: LabelOption | null
  coding: CodingJson | null
  in_working_set: boolean
  local_file: boolean
}

export interface CommentProgress {
  working_set: number
  unlabeled: number
  labeled: number
  unreviewed: number
  verified: number
}

export interface InboxResponse {
  unlabeled_count: number
  pending_code_count: number
  llm_provider: string | null
  labels: LabelOption[]
  items: InboxItemJson[]
  working_items: InboxItemJson[]
  progress: CommentProgress
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function throwHttpError(response: Response): Promise<never> {
  let detail = response.statusText
  try {
    const body = await response.json() as { detail?: unknown }
    if (typeof body.detail === 'string') { detail = body.detail }
  }
  catch {
    // keep statusText
  }
  throw new ApiError(detail, response.status)
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    await throwHttpError(response)
  }
  return await response.json() as T
}

export function fetchInbox(): Promise<InboxResponse> {
  return api<InboxResponse>('/api/inbox')
}

export function postInbox(commentId: string, action: 'accept' | 'verify' | 'delete'): Promise<{ ok: true }> {
  return api(`/api/inbox/${commentId}/${action}`, { method: 'POST' })
}

export function revealInboxFile(commentId: string): Promise<{ ok: true }> {
  return api(`/api/inbox/${commentId}/reveal`, { method: 'POST' })
}

export function postInboxCode(): Promise<{ ok: true, coded: number, failed: number, privacy_warning: string | null }> {
  return api('/api/inbox/code', { method: 'POST' })
}

export function changeInbox(commentId: string, labelId: string): Promise<{ ok: true }> {
  return api(`/api/inbox/${commentId}/change`, {
    method: 'POST',
    body: JSON.stringify({ label_id: labelId }),
  })
}

export interface TaxonomyNode {
  id: string
  name: string
  count: number
  children: TaxonomyNode[]
}

export interface TaxonomyListResponse {
  forest: TaxonomyNode[]
}

export interface LabelDetail {
  id: string
  name: string
  parent_id: string | null
  path: { id: string, name: string }[]
  definition: string
  status: string
  examples: { id: string, text: string }[]
  comments: TaxonomyCommentJson[]
}

export type TaxonomyCommentJson = CommentJson & {
  project_name: string
  permalink: string | null
  label?: LabelOption | null
}

export function fetchLabels(): Promise<TaxonomyListResponse> {
  return api('/api/labels')
}

export function fetchLabel(id: string): Promise<LabelDetail> {
  return api(`/api/labels/${id}`)
}

export function renameLabel(id: string, name: string): Promise<{ ok: true }> {
  return api(`/api/labels/${id}/rename`, { method: 'POST', body: JSON.stringify({ name }) })
}

export function editLabel(
  id: string,
  body: { definition: string },
): Promise<{ ok: true }> {
  return api(`/api/labels/${id}/edit`, { method: 'POST', body: JSON.stringify(body) })
}

export function createLabel(parentId: string | null): Promise<{ ok: true, id: string }> {
  return api('/api/labels', { method: 'POST', body: JSON.stringify({ parent_id: parentId }) })
}

export function moveLabel(id: string, parentId: string | null, position: number): Promise<{ ok: true }> {
  return api(`/api/labels/${id}/move`, {
    method: 'POST',
    body: JSON.stringify({ parent_id: parentId, position }),
  })
}

export function flattenLabel(id: string): Promise<{ ok: true }> {
  return api(`/api/labels/${id}/flatten`, { method: 'POST' })
}

export function removeLabel(id: string): Promise<{ ok: true }> {
  return api(`/api/labels/${id}/remove`, { method: 'POST' })
}

export function mergeLabels(sourceIds: string[], targetId: string): Promise<{ ok: true }> {
  return api('/api/labels/merge', {
    method: 'POST',
    body: JSON.stringify({ source_ids: sourceIds, target_id: targetId }),
  })
}

export function splitLabel(id: string): Promise<{ ok: true, privacy_warning: string | null }> {
  return api(`/api/labels/${id}/split`, { method: 'POST' })
}

export function splitForest(): Promise<{ ok: true, privacy_warning: string | null }> {
  return api('/api/labels/split', { method: 'POST' })
}

export function recycleUngrouped(): Promise<{ ok: true, id: string }> {
  return api('/api/labels/recycle', { method: 'POST' })
}

export interface HistoryComment {
  text: string
  label_name: string | null
}

export interface HistoryQuote {
  heading: string
  body: string
}

export interface HistoryDetails {
  explanation: string
  comments: HistoryComment[]
  quotes: HistoryQuote[]
}

export interface HistoryEvent {
  id: string
  event_type: string
  created_at: string
  payload: Record<string, unknown>
  undone: boolean
  summary: string
  details: HistoryDetails
}

export interface HistoryResponse {
  events: HistoryEvent[]
  can_undo: boolean
  can_redo: boolean
}

export function fetchHistory(): Promise<HistoryResponse> {
  return api('/api/history')
}

export function undoHistory(): Promise<{ ok: true }> {
  return api('/api/history/undo', { method: 'POST' })
}

export function redoHistory(): Promise<{ ok: true }> {
  return api('/api/history/redo', { method: 'POST' })
}

export type ExportFormat = 'md' | 'yaml' | 'json'

export async function fetchExport(fmt: ExportFormat, ids: string[]): Promise<string> {
  const params = new URLSearchParams({ format: fmt })
  for (const id of ids) {
    params.append('id', id)
  }
  const response = await fetch(`/api/labels/export?${params.toString()}`)
  if (!response.ok) {
    await throwHttpError(response)
  }
  return await response.text()
}

export interface LlmSettingsResponse {
  provider: string | null
  model: string | null
  key_set: boolean
  api_key: string | null
}

export function fetchLlmSettings(): Promise<LlmSettingsResponse> {
  return api('/api/llm-settings')
}

export function saveLlmSettings(body: {
  provider: string
  model: string
  api_key: string
}): Promise<{ ok: true, key_set: boolean }> {
  return api('/api/llm-settings', { method: 'POST', body: JSON.stringify(body) })
}

export interface DataLocation {
  home: string
  comments: string
  file_url: string
}

export function fetchDataLocation(): Promise<DataLocation> {
  return api('/api/paths')
}

export function saveDataLocation(home: string): Promise<DataLocation> {
  return api('/api/paths', { method: 'POST', body: JSON.stringify({ home }) })
}

export function openDataFolder(): Promise<{ ok: true }> {
  return api('/api/paths/open', { method: 'POST' })
}

export function chooseDataFolder(): Promise<{ home: string | null }> {
  return api('/api/paths/choose', { method: 'POST' })
}
