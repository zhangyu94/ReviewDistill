"""Forest helpers. Counts come from descendant labels; ancestors do not store copies."""

from __future__ import annotations

from reviewdistill.db.models import ISSUE_ACTIVE, IssueType


def active_only(types: list[IssueType]) -> list[IssueType]:
    return [row for row in types if row.status == ISSUE_ACTIVE]


def active_children(types: list[IssueType], parent_id: str | None) -> list[IssueType]:
    rows = [row for row in active_only(types) if row.parent_id == parent_id]
    return sorted(rows, key=lambda row: (row.position, row.name, row.id))


def descendant_ids(
    types: list[IssueType], root_id: str, *, active_only: bool = True
) -> set[str]:
    rows = [
        row for row in types if (not active_only) or row.status == ISSUE_ACTIVE
    ]
    children_of: dict[str | None, list[str]] = {}
    for row in rows:
        children_of.setdefault(row.parent_id, []).append(row.id)
    found: set[str] = set()
    stack = list(children_of.get(root_id, []))
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children_of.get(current, []))
    return found


def is_under(types: list[IssueType], *, child: str, ancestor: str) -> bool:
    if child == ancestor:
        return True
    return child in descendant_ids(types, ancestor)


def compact_positions(types: list[IssueType], parent_id: str | None) -> None:
    """Rewrite active siblings under parent_id to position 0..n-1."""
    siblings = [row for row in types if row.status == ISSUE_ACTIVE and row.parent_id == parent_id]
    siblings.sort(key=lambda row: (row.position, row.name, row.id))
    for index, row in enumerate(siblings):
        row.position = index


def place_among_siblings(
    types: list[IssueType],
    issue: IssueType,
    parent_id: str | None,
    position: int,
) -> None:
    old_parent = issue.parent_id
    siblings = [row for row in active_children(types, parent_id) if row.id != issue.id]
    position = max(0, min(int(position), len(siblings)))
    siblings.insert(position, issue)
    issue.parent_id = parent_id
    for index, row in enumerate(siblings):
        row.position = index
    if old_parent != parent_id:
        compact_positions(types, old_parent)


def lift_children(types: list[IssueType], issue: IssueType) -> list[dict]:
    """Move active children onto issue's parent, inserted at issue.position."""
    kids = active_children(types, issue.id)
    dumped = []
    new_parent = issue.parent_id
    siblings = [row for row in active_children(types, new_parent) if row.id != issue.id]
    at = max(0, min(issue.position, len(siblings)))
    for offset, kid in enumerate(kids):
        dumped.append(
            {
                "id": kid.id,
                "from_parent_id": issue.id,
                "from_position": kid.position,
            }
        )
        siblings.insert(at + offset, kid)
        kid.parent_id = new_parent
    for index, row in enumerate(siblings):
        row.position = index
    return dumped


def next_new_code(taken: list[str]) -> str:
    taken_set = set(taken)
    if "NEW" not in taken_set:
        return "NEW"
    n = 2
    while f"NEW_{n}" in taken_set:
        n += 1
    return f"NEW_{n}"


def subtree_count(own: dict[str, int], ids: set[str]) -> int:
    return sum(own.get(i, 0) for i in ids)


def types_to_forest(types: list[IssueType], own_counts: dict[str, int]) -> list[dict]:
    def node(row: IssueType) -> dict:
        kids = active_children(types, row.id)
        child_nodes = [node(child) for child in kids]
        ids = descendant_ids(types, row.id) | {row.id}
        return {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "count": subtree_count(own_counts, ids),
            "children": child_nodes,
        }

    return [node(row) for row in active_children(types, None)]


def type_path(types: list[IssueType], issue_id: str) -> list[dict]:
    by_id = {row.id: row for row in types}
    chain = []
    current = by_id.get(issue_id)
    seen: set[str] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        chain.append({"id": current.id, "name": current.name})
        current = by_id.get(current.parent_id) if current.parent_id else None
    chain.reverse()
    return chain
