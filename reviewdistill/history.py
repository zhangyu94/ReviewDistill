"""Linear undo/redo over ``taxonomy_events``.

Undo/Redo mark ``undone`` on the tip instead of appending. A new forward
action deletes the redo tail. Old merge/split rows without invert payload
fields are not invertible. ``propose`` is one event per Label with AI
batch. Accept of a new issue type is ``add`` then ``accept``; undo Accept first.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_MODIFIED,
    CODING_PROPOSED,
    ISSUE_ACTIVE,
    ISSUE_INACTIVE,
    QUALITY_DROPPED,
    QUALITY_UNREVIEWED,
    QUALITY_VERIFIED,
    Coding,
    IssueCounterexample,
    IssueExample,
    IssueType,
    ProofreadingComment,
    TaxonomyEvent,
    as_utc,
    utcnow,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import BadInput
from reviewdistill.taxonomy.tree import next_unique_name

INVERTIBLE = frozenset(
    {
        "add",
        "rename",
        "edit",
        "move",
        "flatten",
        "remove",
        "deactivate",
        "merge",
        "split",
        "propose",
        "accept",
        "change",
        "verify",
        "drop",
    }
)


def _touch_types(session) -> None:
    for row in session.find(IssueType):
        session.add(row)


def _place(session, issue: IssueType, parent_id: str | None, position: int) -> None:
    from reviewdistill.taxonomy.tree import place_among_siblings

    place_among_siblings(session.find(IssueType), issue, parent_id, position)
    _touch_types(session)


def _compact(session, parent_id: str | None) -> None:
    from reviewdistill.taxonomy.tree import compact_positions

    compact_positions(session.find(IssueType), parent_id)
    _touch_types(session)


def dump_row(row) -> dict:
    return row.model_dump(mode="json")


def _parse_dt(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        return as_utc(value)
    return value


def coding_from_dump(data: dict) -> Coding:
    data = dict(data)
    data.pop("proposed_issue_code", None)
    data.pop("code", None)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return Coding(**data)


def example_from_dump(data: dict) -> IssueExample:
    data = dict(data)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return IssueExample(**data)


def counter_from_dump(data: dict) -> IssueCounterexample:
    data = dict(data)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return IssueCounterexample(**data)


def issue_from_dump(data: dict) -> IssueType:
    data = dict(data)
    data.pop("code", None)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    data["updated_at"] = _parse_dt(data.get("updated_at")) or utcnow()
    return IssueType(**data)


def record(session, event_type: str, payload: dict) -> None:
    for event in session.find(TaxonomyEvent, undone=True):
        session.delete(event)
    session.add(
        TaxonomyEvent(
            id=str(uuid4()),
            event_type=event_type,
            payload_json=json.dumps(payload),
            undone=False,
        )
    )


def event_summary(event_type: str, payload: dict) -> str:
    if event_type == "add":
        return f"Add {payload.get('name')}"
    if event_type == "rename":
        before = (payload.get("before") or {}).get("name")
        after = (payload.get("after") or {}).get("name")
        return f"Rename {before} → {after}"
    if event_type == "edit":
        return "Edit definition"
    if event_type == "move":
        return f"Move {payload.get('name')}"
    if event_type == "flatten":
        return f"Flatten {payload.get('name')}"
    if event_type == "remove":
        return f"Remove {payload.get('name')}"
    if event_type == "deactivate":
        return f"Deactivate {payload.get('name')}"
    if event_type == "merge":
        return "Merge issue types"
    if event_type == "split":
        return "Split issue type"
    if event_type == "propose":
        n = len(payload.get("created") or [])
        return f"Label with AI ({n})"
    if event_type == "accept":
        return "Accept label"
    if event_type == "change":
        return "Change label"
    if event_type == "verify":
        return "Verify comment"
    if event_type == "drop":
        return "Drop comment"
    return event_type


def can_invert(event: TaxonomyEvent) -> bool:
    if event.event_type not in INVERTIBLE:
        return False
    payload = json.loads(event.payload_json)
    if event.event_type == "merge":
        return "reassigned_codings" in payload
    if event.event_type == "split":
        return "deleted_codings" in payload
    if event.event_type == "propose":
        return "created" in payload
    if event.event_type == "move":
        return "from_parent_id" in payload
    if event.event_type == "flatten":
        return "reassigned_codings" in payload and "descendant_ids" in payload
    if event.event_type == "remove":
        return "types" in payload
    return True


def list_history() -> dict:
    init_db()
    with get_session() as session:
        rows = session.find(TaxonomyEvent, order_by="created_at", reverse=True)
    events = []
    for event in rows:
        payload = json.loads(event.payload_json)
        events.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "payload": payload,
                "undone": bool(event.undone),
                "summary": event_summary(event.event_type, payload),
            }
        )
    applied = [event for event in reversed(rows) if not event.undone]
    undone = [event for event in rows if event.undone]
    can_undo = bool(applied) and can_invert(applied[-1])
    can_redo = bool(undone)
    return {"events": events, "can_undo": can_undo, "can_redo": can_redo}


def undo() -> None:
    init_db()
    with get_session() as session:
        rows = [
            event
            for event in session.find(TaxonomyEvent, order_by="created_at")
            if not event.undone
        ]
        if not rows:
            raise BadInput("Nothing to undo")
        event = rows[-1]
        if not can_invert(event):
            raise BadInput("This event cannot be undone")
        _invert(session, event)
        event.undone = True
        session.add(event)
        session.commit()


def redo() -> None:
    init_db()
    with get_session() as session:
        undone = [
            event
            for event in session.find(TaxonomyEvent, order_by="created_at")
            if event.undone
        ]
        if not undone:
            raise BadInput("Nothing to redo")
        event = undone[0]
        _apply(session, event)
        event.undone = False
        session.add(event)
        session.commit()


def _payload(event: TaxonomyEvent) -> dict:
    return json.loads(event.payload_json)


def _set_unique_name(session, issue: IssueType, name: str) -> None:
    taken = [
        row.name
        for row in session.find(IssueType, status=ISSUE_ACTIVE)
        if row.id != issue.id
    ]
    issue.name = next_unique_name(taken, name)
    issue.updated_at = utcnow()
    session.add(issue)


def _invert_rename(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    _set_unique_name(session, issue, payload["before"]["name"])


def _apply_rename(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    _set_unique_name(session, issue, payload["after"]["name"])


def _invert_edit(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    before = payload["before"]
    issue.definition = before["definition"]
    issue.notes = before.get("notes")
    issue.detection_guidance = before.get("detection_guidance")
    issue.updated_at = utcnow()
    session.add(issue)


def _apply_edit(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    after = payload["after"]
    issue.definition = after["definition"]
    issue.notes = after.get("notes")
    issue.detection_guidance = after.get("detection_guidance")
    issue.updated_at = utcnow()
    session.add(issue)


def _invert_move(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    _place(session, issue, payload["from_parent_id"], payload["from_position"])
    issue.updated_at = utcnow()


def _apply_move(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    _place(session, issue, payload["to_parent_id"], payload["to_position"])
    issue.updated_at = utcnow()


def _invert_add(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    parent_id = issue.parent_id
    issue.status = ISSUE_INACTIVE
    issue.updated_at = utcnow()
    session.add(issue)
    _compact(session, parent_id)


def _apply_add(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    issue.status = ISSUE_ACTIVE
    issue.updated_at = utcnow()
    session.add(issue)
    _place(session, issue, issue.parent_id, issue.position)


def _invert_deactivate(session, payload: dict) -> None:
    issue = session.get(IssueType, payload["issue_type_id"])
    issue.status = ISSUE_ACTIVE
    issue.updated_at = utcnow()
    session.add(issue)
    _place(session, issue, issue.parent_id, issue.position)
    for row in payload.get("reparented_children") or []:
        child = session.get(IssueType, row["id"])
        if child is not None:
            _place(session, child, row["from_parent_id"], row.get("from_position", 0))
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))


def _apply_deactivate(session, payload: dict) -> None:
    from reviewdistill.taxonomy.tree import lift_children

    issue = session.get(IssueType, payload["issue_type_id"])
    if "reparented_children" in payload:
        lift_children(session.find(IssueType), issue)
    issue.status = ISSUE_INACTIVE
    issue.updated_at = utcnow()
    session.add(issue)
    for row in session.find(IssueType):
        session.add(row)
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)


def _invert_propose(session, payload: dict) -> None:
    for row in payload.get("created") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("replaced") or []:
        session.add(coding_from_dump(row))


def _apply_propose(session, payload: dict) -> None:
    for row in payload.get("replaced") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("created") or []:
        session.add(coding_from_dump(row))


def _invert_accept(session, payload: dict) -> None:
    coding = session.get(Coding, payload["coding_id"])
    coding.status = payload.get("previous_status") or CODING_PROPOSED
    session.add(coding)
    if payload.get("example_created") and payload.get("example_id"):
        example = session.get(IssueExample, payload["example_id"])
        if example is not None:
            session.delete(example)


def _apply_accept(session, payload: dict) -> None:
    coding = session.get(Coding, payload["coding_id"])
    coding.status = CODING_ACCEPTED
    if payload.get("issue_type_id"):
        coding.issue_type_id = payload["issue_type_id"]
    session.add(coding)
    if payload.get("example_created") and payload.get("example"):
        session.add(example_from_dump(payload["example"]))


def _invert_change(session, payload: dict) -> None:
    human = session.get(Coding, payload["coding_id"])
    if human is not None:
        session.delete(human)
    if payload.get("proposed_id"):
        proposed = session.get(Coding, payload["proposed_id"])
        if proposed is not None:
            proposed.status = CODING_PROPOSED
            session.add(proposed)
    if payload.get("example_created") and payload.get("example_id"):
        example = session.get(IssueExample, payload["example_id"])
        if example is not None:
            session.delete(example)
    for row in payload.get("retired_accepted") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.status = row.get("status") or CODING_ACCEPTED
            session.add(coding)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))


def _apply_change(session, payload: dict) -> None:
    if payload.get("proposed_id"):
        proposed = session.get(Coding, payload["proposed_id"])
        if proposed is not None:
            proposed.status = CODING_MODIFIED
            session.add(proposed)
    for row in payload.get("retired_accepted") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.status = CODING_MODIFIED
            session.add(coding)
    session.add(coding_from_dump(payload["coding"]))
    if payload.get("example_created") and payload.get("example"):
        session.add(example_from_dump(payload["example"]))
    for row in payload.get("deleted_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            session.delete(example)


def _invert_quality(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    comment.quality = payload.get("previous_quality") or QUALITY_UNREVIEWED
    session.add(comment)


def _apply_verify(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    comment.quality = QUALITY_VERIFIED
    session.add(comment)


def _apply_drop(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    comment.quality = QUALITY_DROPPED
    session.add(comment)


def _invert(session, event: TaxonomyEvent) -> None:
    pair = HANDLERS.get(event.event_type)
    if pair is None:
        raise BadInput(f"Cannot invert {event.event_type}")
    pair[1](session, _payload(event))


def _apply(session, event: TaxonomyEvent) -> None:
    pair = HANDLERS.get(event.event_type)
    if pair is None:
        raise BadInput(f"Cannot redo {event.event_type}")
    pair[0](session, _payload(event))


def _invert_merge(session, payload: dict) -> None:
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.issue_type_id = row["from_issue_type_id"]
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            example.issue_type_id = row["from_issue_type_id"]
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    for row in payload.get("reassigned_counters") or []:
        counter = session.get(IssueCounterexample, row["id"])
        if counter is not None:
            counter.issue_type_id = row["from_issue_type_id"]
            session.add(counter)
    for source_id in payload.get("source_ids") or []:
        if source_id == payload.get("target_id"):
            continue
        source = session.get(IssueType, source_id)
        if source is not None:
            source.status = ISSUE_ACTIVE
            source.updated_at = utcnow()
            session.add(source)
            _place(session, source, source.parent_id, source.position)
    for row in payload.get("reparented_children") or []:
        child = session.get(IssueType, row["id"])
        if child is not None:
            _place(
                session,
                child,
                row["from_parent_id"],
                row.get("from_position", 0),
            )


def _apply_merge(session, payload: dict) -> None:
    target_id = payload["target_id"]
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.issue_type_id = target_id
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            example.issue_type_id = target_id
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            session.delete(example)
    for row in payload.get("reassigned_counters") or []:
        counter = session.get(IssueCounterexample, row["id"])
        if counter is not None:
            counter.issue_type_id = target_id
            session.add(counter)
    parents: set[str | None] = set()
    for row in payload.get("reparented_children") or []:
        child = session.get(IssueType, row["id"])
        if child is not None:
            child.parent_id = target_id
            session.add(child)
    _compact(session, target_id)
    for source_id in payload.get("source_ids") or []:
        if source_id == target_id:
            continue
        source = session.get(IssueType, source_id)
        if source is not None:
            parents.add(source.parent_id)
            source.status = ISSUE_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
    for parent_id in parents:
        _compact(session, parent_id)


def _invert_split(session, payload: dict) -> None:
    source = session.get(IssueType, payload["source_id"])
    source.status = ISSUE_ACTIVE
    source.updated_at = utcnow()
    session.add(source)
    for created_id in payload.get("created_ids") or []:
        created = session.get(IssueType, created_id)
        if created is not None:
            created.status = ISSUE_INACTIVE
            created.updated_at = utcnow()
            session.add(created)
    _place(session, source, source.parent_id, source.position)
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))


def _apply_split(session, payload: dict) -> None:
    source = session.get(IssueType, payload["source_id"])
    source.status = ISSUE_INACTIVE
    source.updated_at = utcnow()
    session.add(source)
    _compact(session, source.parent_id)
    placements = []
    for created_id in payload.get("created_ids") or []:
        created = session.get(IssueType, created_id)
        if created is not None:
            placements.append((created, created.parent_id, created.position))
    placements.sort(key=lambda item: (item[2], item[0].name, item[0].id))
    for created, parent_id, position in placements:
        created.status = ISSUE_ACTIVE
        created.updated_at = utcnow()
        session.add(created)
        _place(session, created, parent_id, position)
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)


def _invert_flatten(session, payload: dict) -> None:
    target_id = payload["issue_type_id"]
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.issue_type_id = row["from_issue_type_id"]
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            example.issue_type_id = row["from_issue_type_id"]
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    for row in payload.get("reassigned_counters") or []:
        counter = session.get(IssueCounterexample, row["id"])
        if counter is not None:
            counter.issue_type_id = row["from_issue_type_id"]
            session.add(counter)
    for issue_id in payload.get("descendant_ids") or []:
        row = session.get(IssueType, issue_id)
        if row is not None:
            row.status = ISSUE_ACTIVE
            row.updated_at = utcnow()
            session.add(row)


def _apply_flatten(session, payload: dict) -> None:
    target_id = payload["issue_type_id"]
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.issue_type_id = target_id
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            example.issue_type_id = target_id
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        example = session.get(IssueExample, row["id"])
        if example is not None:
            session.delete(example)
    for row in payload.get("reassigned_counters") or []:
        counter = session.get(IssueCounterexample, row["id"])
        if counter is not None:
            counter.issue_type_id = target_id
            session.add(counter)
    for issue_id in payload.get("descendant_ids") or []:
        row = session.get(IssueType, issue_id)
        if row is not None:
            row.status = ISSUE_INACTIVE
            row.updated_at = utcnow()
            session.add(row)


def _invert_remove(session, payload: dict) -> None:
    for row in payload.get("types") or []:
        session.add(issue_from_dump(row))
    for row in payload.get("examples") or []:
        session.add(example_from_dump(row))
    for row in payload.get("counters") or []:
        session.add(counter_from_dump(row))
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))
    root = session.get(IssueType, payload["issue_type_id"])
    if root is not None:
        _place(session, root, root.parent_id, root.position)


def _apply_remove(session, payload: dict) -> None:
    parent_id = None
    for row in payload.get("types") or []:
        if row.get("id") == payload.get("issue_type_id"):
            parent_id = row.get("parent_id")
            break
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("examples") or []:
        existing = session.get(IssueExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("counters") or []:
        existing = session.get(IssueCounterexample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("types") or []:
        existing = session.get(IssueType, row["id"])
        if existing is not None:
            session.delete(existing)
    _compact(session, parent_id)


HANDLERS = {
    "rename": (_apply_rename, _invert_rename),
    "edit": (_apply_edit, _invert_edit),
    "move": (_apply_move, _invert_move),
    "add": (_apply_add, _invert_add),
    "deactivate": (_apply_deactivate, _invert_deactivate),
    "merge": (_apply_merge, _invert_merge),
    "split": (_apply_split, _invert_split),
    "propose": (_apply_propose, _invert_propose),
    "accept": (_apply_accept, _invert_accept),
    "change": (_apply_change, _invert_change),
    "verify": (_apply_verify, _invert_quality),
    "drop": (_apply_drop, _invert_quality),
    "flatten": (_apply_flatten, _invert_flatten),
    "remove": (_apply_remove, _invert_remove),
}
