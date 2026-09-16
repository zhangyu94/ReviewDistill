import type { InboxItemJson } from '../api/client.ts'

export type CommentTreeGroupKind = 'project' | 'file'

export interface CommentTreeGroup {
  kind: 'group'
  groupKind: CommentTreeGroupKind
  id: string
  name: string
  depth: number
  count: number
  revealId: string | null
  children: CommentTreeNode[]
}

export interface CommentTreeLeaf {
  kind: 'comment'
  id: string
  depth: number
  item: InboxItemJson
}

export type CommentTreeNode = CommentTreeGroup | CommentTreeLeaf

export type CommentTreeRow = Omit<CommentTreeGroup, 'children'> | CommentTreeLeaf

function compareItems(a: InboxItemJson, b: InboxItemJson): number {
  const byName = a.project_name.localeCompare(b.project_name)
  if (byName) { return byName }
  const byProject = a.comment.project_id.localeCompare(b.comment.project_id)
  if (byProject) { return byProject }
  const byPath = a.comment.file_path.localeCompare(b.comment.file_path)
  if (byPath) { return byPath }
  if (a.comment.line_number !== b.comment.line_number) {
    return a.comment.line_number - b.comment.line_number
  }
  return a.comment.id.localeCompare(b.comment.id)
}

function fileGroup(projectId: string, filePath: string, items: InboxItemJson[]): CommentTreeGroup {
  const children: CommentTreeLeaf[] = items.map((item) => ({
    kind: 'comment',
    id: item.comment.id,
    depth: 2,
    item,
  }))
  return {
    kind: 'group',
    groupKind: 'file',
    id: `p:${projectId}/f:${filePath}`,
    name: filePath,
    depth: 1,
    count: children.length,
    revealId: items.find((item) => item.local_file)?.comment.id ?? null,
    children,
  }
}

export function commentTree(items: InboxItemJson[]): CommentTreeGroup[] {
  const sorted = items.slice().sort(compareItems)
  const projects: { id: string, name: string, files: { path: string, items: InboxItemJson[] }[] }[] = []
  const index = new Map<string, (typeof projects)[number]>()
  for (const item of sorted) {
    const id = item.comment.project_id
    let project = index.get(id)
    if (!project) {
      project = { id, name: item.project_name, files: [] }
      index.set(id, project)
      projects.push(project)
    }
    const path = item.comment.file_path
    const last = project.files[project.files.length - 1]
    if (last?.path === path) { last.items.push(item) }
    else { project.files.push({ path, items: [item] }) }
  }
  return projects.map((project) => {
    const children = project.files.map((file) => fileGroup(project.id, file.path, file.items))
    return {
      kind: 'group' as const,
      groupKind: 'project' as const,
      id: `p:${project.id}`,
      name: project.name,
      depth: 0,
      count: children.reduce((sum, file) => sum + file.count, 0),
      revealId: null,
      children,
    }
  })
}

export function flattenCommentTree(
  forest: CommentTreeGroup[],
  collapsed: ReadonlySet<string>,
): CommentTreeRow[] {
  const rows: CommentTreeRow[] = []
  const walk = (nodes: CommentTreeNode[]) => {
    for (const node of nodes) {
      if (node.kind === 'comment') {
        rows.push(node)
        continue
      }
      const { children, ...row } = node
      rows.push(row)
      if (!collapsed.has(node.id)) { walk(children) }
    }
  }
  walk(forest)
  return rows
}

export function visibleCommentTreeIds(
  items: InboxItemJson[],
  collapsed: ReadonlySet<string>,
): string[] {
  return flattenCommentTree(commentTree(items), collapsed)
    .filter((row): row is CommentTreeLeaf => row.kind === 'comment')
    .map((row) => row.id)
}

export function commentTreeIds(items: InboxItemJson[]): string[] {
  return visibleCommentTreeIds(items, new Set())
}

export function ancestorGroupIds(items: InboxItemJson[], commentId: string): string[] {
  const walk = (nodes: CommentTreeNode[], trail: string[]): string[] | undefined => {
    for (const node of nodes) {
      if (node.kind === 'comment') {
        if (node.id === commentId) { return trail }
        continue
      }
      const found = walk(node.children, [...trail, node.id])
      if (found) { return found }
    }
    return undefined
  }
  return walk(commentTree(items), []) ?? []
}

export function expandAncestors(
  collapsed: ReadonlySet<string>,
  items: InboxItemJson[],
  commentId: string,
): Set<string> {
  const next = new Set(collapsed)
  for (const id of ancestorGroupIds(items, commentId)) {
    next.delete(id)
  }
  return next
}

export function adjacentVisibleCommentId(
  items: InboxItemJson[],
  collapsed: ReadonlySet<string>,
  currentId: string,
  step: 1 | -1,
): string | undefined {
  const full = commentTreeIds(items)
  const visible = new Set(visibleCommentTreeIds(items, collapsed))
  const i = full.indexOf(currentId)
  if (i < 0) { return undefined }
  for (let index = i + step; index >= 0 && index < full.length; index += step) {
    const id = full[index]
    if (id && visible.has(id)) { return id }
  }
  return undefined
}

/** After collapse: keep the open comment if it is still visible; else the next visible neighbor; else keep the hidden id so a later expand can restore it. */
export function selectedIdAfterTreeCollapse(
  items: InboxItemJson[],
  collapsed: ReadonlySet<string>,
  selectedId: string | undefined,
): string | undefined {
  if (!selectedId) { return undefined }
  if (visibleCommentTreeIds(items, collapsed).includes(selectedId)) { return selectedId }
  return adjacentVisibleCommentId(items, collapsed, selectedId, 1)
    ?? adjacentVisibleCommentId(items, collapsed, selectedId, -1)
    ?? selectedId
}
