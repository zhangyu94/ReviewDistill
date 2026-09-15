"""Forest helpers. Counts come from descendant labels; ancestors do not store copies."""

from __future__ import annotations

import re

from reviewdistill.db.models import LABEL_ACTIVE, Label


def active_only(labels: list[Label]) -> list[Label]:
    return [row for row in labels if row.status == LABEL_ACTIVE]


def active_children(labels: list[Label], parent_id: str | None) -> list[Label]:
    rows = [row for row in active_only(labels) if row.parent_id == parent_id]
    return sorted(rows, key=lambda row: (row.position, row.name, row.id))


def descendant_ids(
    labels: list[Label], root_id: str, *, active_only: bool = True
) -> set[str]:
    rows = [
        row for row in labels if (not active_only) or row.status == LABEL_ACTIVE
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


def is_under(labels: list[Label], *, child: str, ancestor: str) -> bool:
    if child == ancestor:
        return True
    return child in descendant_ids(labels, ancestor)


def compact_positions(labels: list[Label], parent_id: str | None) -> None:
    """Rewrite active siblings under parent_id to position 0..n-1."""
    siblings = [row for row in labels if row.status == LABEL_ACTIVE and row.parent_id == parent_id]
    siblings.sort(key=lambda row: (row.position, row.name, row.id))
    for index, row in enumerate(siblings):
        row.position = index


def place_among_siblings(
    labels: list[Label],
    label: Label,
    parent_id: str | None,
    position: int,
) -> None:
    old_parent = label.parent_id
    siblings = [row for row in active_children(labels, parent_id) if row.id != label.id]
    position = max(0, min(int(position), len(siblings)))
    siblings.insert(position, label)
    label.parent_id = parent_id
    for index, row in enumerate(siblings):
        row.position = index
    if old_parent != parent_id:
        compact_positions(labels, old_parent)


def lift_children(labels: list[Label], label: Label) -> list[dict]:
    """Move active children onto label's parent, inserted at label.position."""
    kids = active_children(labels, label.id)
    dumped = []
    new_parent = label.parent_id
    siblings = [row for row in active_children(labels, new_parent) if row.id != label.id]
    at = max(0, min(label.position, len(siblings)))
    for offset, kid in enumerate(kids):
        dumped.append(
            {
                "id": kid.id,
                "from_parent_id": label.id,
                "from_position": kid.position,
            }
        )
        siblings.insert(at + offset, kid)
        kid.parent_id = new_parent
    for index, row in enumerate(siblings):
        row.position = index
    return dumped


def next_unique_name(taken: list[str], name: str = "New label") -> str:
    """Same suffix rule as image-taxonomy-labeler: ``foo``, then ``foo (2)``, filling gaps."""
    if name not in taken:
        return name
    escaped = re.escape(name)
    pattern = re.compile(rf"^{escaped} \((?P<index>\d+)\)$")
    indices: set[int] = set()
    for item in taken:
        if item == name:
            indices.add(1)
            continue
        match = pattern.match(item)
        if match:
            indices.add(int(match.group("index")))
    for i in range(2, len(indices) + 2):
        if i not in indices:
            return f"{name} ({i})"
    return f"{name} ({max(indices) + 1})"


def subtree_count(own: dict[str, int], ids: set[str]) -> int:
    return sum(own.get(i, 0) for i in ids)


def labels_to_forest(labels: list[Label], own_counts: dict[str, int]) -> list[dict]:
    def node(row: Label) -> dict:
        kids = active_children(labels, row.id)
        child_nodes = [node(child) for child in kids]
        ids = descendant_ids(labels, row.id) | {row.id}
        return {
            "id": row.id,
            "name": row.name,
            "count": subtree_count(own_counts, ids),
            "children": child_nodes,
        }

    return [node(row) for row in active_children(labels, None)]


def label_path(labels: list[Label], label_id: str) -> list[dict]:
    by_id = {row.id: row for row in labels}
    chain = []
    current = by_id.get(label_id)
    seen: set[str] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        chain.append({"id": current.id, "name": current.name})
        current = by_id.get(current.parent_id) if current.parent_id else None
    chain.reverse()
    return chain
