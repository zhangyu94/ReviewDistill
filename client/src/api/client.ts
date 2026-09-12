export interface IssueOption {
  id: string
  code: string
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
  fingerprint: string
  status: string
  quality: string
  supersedes_id: string | null
  created_at: string
}

export interface CodingJson {
  id: string
  status: string
  issue_type_id: string | null
  proposed_issue_name: string | null
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
  issue: IssueOption | null
  coding: CodingJson | null
}

export interface InboxResponse {
  unlabeled_count: number
  pending_code_count: number
  llm_provider: string | null
  issues: IssueOption[]
  items: InboxItemJson[]
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

export function postInbox(commentId: string, action: 'accept' | 'verify' | 'drop'): Promise<{ ok: true }> {
  return api(`/api/inbox/${commentId}/${action}`, { method: 'POST' })
}

export function postInboxCode(): Promise<{ ok: true, coded: number, failed: number, privacy_warning: string | null }> {
  return api('/api/inbox/code', { method: 'POST' })
}

export function changeInbox(commentId: string, issueTypeId: string): Promise<{ ok: true }> {
  return api(`/api/inbox/${commentId}/change`, {
    method: 'POST',
    body: JSON.stringify({ issue_type_id: issueTypeId }),
  })
}

export interface TaxonomyNode {
  id: string
  code: string
  name: string
  count: number
  children: TaxonomyNode[]
}

export interface TaxonomyListResponse {
  forest: TaxonomyNode[]
}

export interface TaxonomyDetail {
  id: string
  code: string
  name: string
  parent_id: string | null
  path: { id: string, name: string }[]
  definition: string
  notes: string | null
  status: string
  examples: { id: string, text: string }[]
  counterexamples: { id: string, text: string }[]
  comments: TaxonomyCommentJson[]
}

export type TaxonomyCommentJson = CommentJson & {
  project_name: string
  permalink: string | null
  issue?: IssueOption | null
}

export function fetchTaxonomy(): Promise<TaxonomyListResponse> {
  return api('/api/taxonomy')
}

export function fetchIssue(id: string): Promise<TaxonomyDetail> {
  return api(`/api/taxonomy/${id}`)
}

export function renameIssue(id: string, name: string, code: string): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/rename`, { method: 'POST', body: JSON.stringify({ name, code }) })
}

export function editIssue(
  id: string,
  body: { definition: string, notes: string },
): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/edit`, { method: 'POST', body: JSON.stringify(body) })
}

export function createIssue(parentId: string | null): Promise<{ ok: true, id: string }> {
  return api('/api/taxonomy', { method: 'POST', body: JSON.stringify({ parent_id: parentId }) })
}

export function moveIssue(id: string, parentId: string | null, position: number): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/move`, {
    method: 'POST',
    body: JSON.stringify({ parent_id: parentId, position }),
  })
}

export function flattenIssue(id: string): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/flatten`, { method: 'POST' })
}

export function removeIssue(id: string): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/remove`, { method: 'POST' })
}

export function deactivateIssue(id: string): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/deactivate`, { method: 'POST' })
}

export function addCounterexample(id: string, text: string): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/counterexample`, { method: 'POST', body: JSON.stringify({ text }) })
}

export function mergeIssues(sourceIds: string[], targetId: string): Promise<{ ok: true }> {
  return api('/api/taxonomy/merge', {
    method: 'POST',
    body: JSON.stringify({ source_ids: sourceIds, target_id: targetId }),
  })
}

export function splitIssue(
  id: string,
  left: { code: string, name: string, definition: string },
  right: { code: string, name: string, definition: string },
): Promise<{ ok: true }> {
  return api(`/api/taxonomy/${id}/split`, { method: 'POST', body: JSON.stringify({ left, right }) })
}

export interface HistoryEvent {
  id: string
  event_type: string
  created_at: string
  payload: Record<string, unknown>
  undone: boolean
  summary: string
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

export function exportFilename(fmt: ExportFormat): string {
  if (fmt === 'yaml') { return 'review-rubric.yaml' }
  if (fmt === 'json') { return 'review-rubric.json' }
  return 'review-rubric.md'
}

export async function fetchExport(fmt: ExportFormat): Promise<string> {
  const response = await fetch(`/api/taxonomy/export?format=${fmt}`)
  if (!response.ok) {
    await throwHttpError(response)
  }
  return await response.text()
}

export interface LlmSettingsProject {
  id: string
  name: string
  root_path: string
}

export interface LlmSettingsSelected {
  project_id: string
  provider: string | null
  model: string | null
  key_set: boolean
}

export interface LlmSettingsResponse {
  projects: LlmSettingsProject[]
  default_project_id: string | null
  selected: LlmSettingsSelected | null
}

export function fetchLlmSettings(projectId?: string): Promise<LlmSettingsResponse> {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return api(`/api/llm-settings${q}`)
}

export function saveLlmSettings(body: {
  project_id: string
  provider: string
  model: string
  api_key: string
}): Promise<{ ok: true, key_set: boolean }> {
  return api('/api/llm-settings', { method: 'POST', body: JSON.stringify(body) })
}

export interface DataLocation {
  home: string
  comments: string
}

export function fetchDataLocation(): Promise<DataLocation> {
  return api('/api/paths')
}
