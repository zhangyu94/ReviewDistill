"""Linear undo/redo over ``taxonomy_events``.

Undo/Redo mark ``undone`` on the tip instead of appending. A new forward
action deletes the redo tail. Old merge/split rows without invert payload
fields are not invertible. ``propose`` is one event per Label with AI
batch. Accept of a leftover stored proposal that mints a label is ``add`` then ``accept``; undo Accept first.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_MODIFIED,
    CODING_PROPOSED,
    LABEL_ACTIVE,
    LABEL_INACTIVE,
    Coding,
    LabelExample,
    Label,
    ProofreadingComment,
    TaxonomyEvent,
    as_utc,
    normalize_comment_record,
    utcnow,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import BadInput
from reviewdistill.history_details import build_lookup, event_details
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
        "unverify",
        "delete",
        "recycle",
    }
)


def _touch_types(session) -> None:
    for row in session.find(Label):
        session.add(row)


def _place(session, label: Label, parent_id: str | None, position: int) -> None:
    from reviewdistill.taxonomy.tree import place_among_siblings

    place_among_siblings(session.find(Label), label, parent_id, position)
    _touch_types(session)


def _compact(session, parent_id: str | None) -> None:
    from reviewdistill.taxonomy.tree import compact_positions

    compact_positions(session.find(Label), parent_id)
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


def comment_from_dump(data: dict) -> ProofreadingComment:
    mapped = normalize_comment_record(dict(data), purge_dropped=False)
    assert mapped is not None
    mapped["created_at"] = _parse_dt(mapped.get("created_at")) or utcnow()
    return ProofreadingComment(**mapped)


def example_from_dump(data: dict) -> LabelExample:
    data = dict(data)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return LabelExample(**data)


def label_from_dump(data: dict) -> Label:
    data = dict(data)
    data.pop("code", None)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    data["updated_at"] = _parse_dt(data.get("updated_at")) or utcnow()
    return Label(**data)


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
    if event_type == "recycle":
        return f"Group unlabeled comments onto {payload.get('name')}"
    if event_type == "deactivate":
        return f"Deactivate {payload.get('name')}"
    if event_type == "merge":
        return "Merge labels"
    if event_type == "split":
        n = len(payload.get("created_ids") or [])
        if payload.get("keep_source"):
            source_name = payload.get("source_name")
            if source_name:
                return f"Split {source_name} into {n} labels"
            return f"Split unlabeled comments into {n} labels"
        return "Split label"
    if event_type == "propose":
        n = len(payload.get("created") or [])
        return f"Label with AI ({n})"
    if event_type == "accept":
        return "Accept suggested label assignment"
    if event_type == "change":
        return "Change label assignment"
    if event_type == "verify":
        return "Verify comment"
    if event_type == "unverify":
        return "Unverify comment"
    if event_type == "delete":
        return "Delete comment"
    return event_type


def can_invert(event: TaxonomyEvent) -> bool:
    if event.event_type not in INVERTIBLE:
        return False
    payload = json.loads(event.payload_json)
    if event.event_type == "merge":
        return "reassigned_codings" in payload
    if event.event_type == "split":
        if payload.get("keep_source"):
            return "created" in payload
        return "deleted_codings" in payload
    if event.event_type == "propose":
        return "created" in payload
    if event.event_type == "move":
        return "from_parent_id" in payload
    if event.event_type == "flatten":
        return "reassigned_codings" in payload and "descendant_ids" in payload
    if event.event_type == "remove":
        return "types" in payload
    if event.event_type == "delete":
        return "comment" in payload
    if event.event_type == "recycle":
        return "label_id" in payload and "created" in payload
    return True


def list_history() -> dict:
    init_db()
    with get_session() as session:
        rows = session.find(TaxonomyEvent, order_by="created_at", reverse=True)
        parsed = [(event, json.loads(event.payload_json)) for event in rows]
        lookup = build_lookup(session, [(event.event_type, payload) for event, payload in parsed])
        events = []
        for event, payload in parsed:
            summary = event_summary(event.event_type, payload)
            events.append(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "payload": payload,
                    "undone": bool(event.undone),
                    "summary": summary,
                    "details": event_details(event.event_type, payload, lookup, summary=summary),
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


def _set_unique_name(session, label: Label, name: str) -> None:
    taken = [
        row.name
        for row in session.find(Label, status=LABEL_ACTIVE)
        if row.id != label.id
    ]
    label.name = next_unique_name(taken, name)
    label.updated_at = utcnow()
    session.add(label)


def _invert_rename(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    _set_unique_name(session, label, payload["before"]["name"])


def _apply_rename(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    _set_unique_name(session, label, payload["after"]["name"])


def _invert_edit(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    before = payload["before"]
    label.definition = before["definition"]
    # Ignore leftover notes keys on old edit payloads.
    label.detection_guidance = before.get("detection_guidance")
    label.updated_at = utcnow()
    session.add(label)


def _apply_edit(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    after = payload["after"]
    label.definition = after["definition"]
    label.detection_guidance = after.get("detection_guidance")
    label.updated_at = utcnow()
    session.add(label)


def _deactivate_parked_ungrouped(session, payload: dict) -> None:
    ungrouped_id = payload.get("ungrouped_id")
    if not ungrouped_id:
        return
    extra = session.get(Label, ungrouped_id)
    if extra is None:
        return
    extra.status = LABEL_INACTIVE
    extra.updated_at = utcnow()
    session.add(extra)
    _compact(session, extra.parent_id)


def _reactivate_parked_ungrouped(session, payload: dict) -> None:
    ungrouped_id = payload.get("ungrouped_id")
    if not ungrouped_id:
        return
    extra = session.get(Label, ungrouped_id)
    if extra is None:
        return
    extra.status = LABEL_ACTIVE
    extra.updated_at = utcnow()
    session.add(extra)
    _place(session, extra, extra.parent_id, extra.position)


def _invert_move(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    _place(session, label, payload["from_parent_id"], payload["from_position"])
    label.updated_at = utcnow()
    if payload.get("ungrouped_id"):
        _deactivate_parked_ungrouped(session, payload)
        _restore_reassigned(session, payload)


def _apply_move(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    _place(session, label, payload["to_parent_id"], payload["to_position"])
    label.updated_at = utcnow()
    ungrouped_id = payload.get("ungrouped_id")
    if ungrouped_id:
        _reactivate_parked_ungrouped(session, payload)
        _apply_reassigned(session, payload, ungrouped_id)


def _invert_add(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    parent_id = label.parent_id
    label.status = LABEL_INACTIVE
    label.updated_at = utcnow()
    session.add(label)
    ungrouped_id = payload.get("ungrouped_id")
    if ungrouped_id:
        _deactivate_parked_ungrouped(session, payload)
        _restore_reassigned(session, payload)
    _compact(session, parent_id)


def _apply_add(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    label.status = LABEL_ACTIVE
    label.updated_at = utcnow()
    session.add(label)
    _place(session, label, label.parent_id, label.position)
    ungrouped_id = payload.get("ungrouped_id")
    if ungrouped_id:
        _reactivate_parked_ungrouped(session, payload)
        _apply_reassigned(session, payload, ungrouped_id)


def _restore_reassigned(session, payload: dict) -> None:
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.label_id = row["from_label_id"]
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = row["from_label_id"]
            session.add(example)


def _apply_reassigned(session, payload: dict, target_id: str) -> None:
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.label_id = target_id
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = target_id
            session.add(example)


def _invert_deactivate(session, payload: dict) -> None:
    label = session.get(Label, payload["label_id"])
    label.status = LABEL_ACTIVE
    label.updated_at = utcnow()
    session.add(label)
    _place(session, label, label.parent_id, label.position)
    for row in payload.get("reparented_children") or []:
        child = session.get(Label, row["id"])
        if child is not None:
            _place(session, child, row["from_parent_id"], row.get("from_position", 0))
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))


def _apply_deactivate(session, payload: dict) -> None:
    from reviewdistill.taxonomy.tree import lift_children

    label = session.get(Label, payload["label_id"])
    if "reparented_children" in payload:
        lift_children(session.find(Label), label)
    label.status = LABEL_INACTIVE
    label.updated_at = utcnow()
    session.add(label)
    for row in session.find(Label):
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
    for row in payload.get("examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for label_id in payload.get("created_label_ids") or []:
        created = session.get(Label, label_id)
        if created is not None:
            created.status = LABEL_INACTIVE
            created.updated_at = utcnow()
            session.add(created)
    for row in payload.get("replaced") or []:
        comment_id = row.get("comment_id")
        if comment_id and session.get(ProofreadingComment, comment_id) is None:
            continue
        session.add(coding_from_dump(row))


def _apply_propose(session, payload: dict) -> None:
    placements = []
    for label_id in payload.get("created_label_ids") or []:
        created = session.get(Label, label_id)
        if created is not None:
            placements.append((created, created.parent_id, created.position))
    placements.sort(key=lambda item: (item[2], item[0].name, item[0].id))
    for created, parent_id, position in placements:
        created.status = LABEL_ACTIVE
        created.updated_at = utcnow()
        session.add(created)
        _place(session, created, parent_id, position)
    for row in payload.get("replaced") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("created") or []:
        session.add(coding_from_dump(row))
    for row in payload.get("examples") or []:
        session.add(example_from_dump(row))


def _invert_accept(session, payload: dict) -> None:
    coding = session.get(Coding, payload["coding_id"])
    if coding is None:
        return
    coding.status = payload.get("previous_status") or CODING_PROPOSED
    session.add(coding)
    if payload.get("example_created") and payload.get("example_id"):
        example = session.get(LabelExample, payload["example_id"])
        if example is not None:
            session.delete(example)


def _apply_accept(session, payload: dict) -> None:
    coding = session.get(Coding, payload["coding_id"])
    if coding is None:
        return
    coding.status = CODING_ACCEPTED
    if payload.get("label_id"):
        coding.label_id = payload["label_id"]
    session.add(coding)
    if payload.get("example_created") and payload.get("example"):
        example = payload["example"]
        comment_id = example.get("source_comment_id")
        if comment_id and session.get(ProofreadingComment, comment_id) is None:
            return
        session.add(example_from_dump(example))


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
        example = session.get(LabelExample, payload["example_id"])
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
        example = session.get(LabelExample, row["id"])
        if example is not None:
            session.delete(example)


def _invert_verify(session, payload: dict) -> None:
    # Event type is enough; ignore leftover previous_quality on old dumps.
    comment = session.get(ProofreadingComment, payload["comment_id"])
    if comment is None:
        return
    comment.verified = False
    session.add(comment)


def _apply_verify(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    if comment is None:
        return
    comment.verified = True
    session.add(comment)


def _invert_unverify(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    if comment is None:
        return
    comment.verified = True
    session.add(comment)


def _apply_unverify(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    if comment is None:
        return
    comment.verified = False
    session.add(comment)


def _apply_delete(session, payload: dict) -> None:
    comment = session.get(ProofreadingComment, payload["comment_id"])
    if comment is not None:
        session.delete_comment_graph(comment)
        return
    for row in payload.get("codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)


def _invert_delete(session, payload: dict) -> None:
    dumped = payload.get("comment")
    if not dumped:
        return
    if session.get(ProofreadingComment, payload["comment_id"]) is None:
        session.add(comment_from_dump(dumped))
    for row in payload.get("codings") or []:
        if session.get(Coding, row["id"]) is None:
            session.add(coding_from_dump(row))
    for row in payload.get("examples") or []:
        if session.get(LabelExample, row["id"]) is None:
            session.add(example_from_dump(row))


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
            coding.label_id = row["from_label_id"]
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = row["from_label_id"]
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    for source_id in payload.get("source_ids") or []:
        if source_id == payload.get("target_id"):
            continue
        source = session.get(Label, source_id)
        if source is not None:
            source.status = LABEL_ACTIVE
            source.updated_at = utcnow()
            session.add(source)
            _place(session, source, source.parent_id, source.position)
    for row in payload.get("reparented_children") or []:
        child = session.get(Label, row["id"])
        if child is not None:
            _place(
                session,
                child,
                row["from_parent_id"],
                row.get("from_position", 0),
            )
    _deactivate_parked_ungrouped(session, payload)


def _apply_merge(session, payload: dict) -> None:
    target_id = payload["target_id"]
    dest_id = payload.get("ungrouped_id") or target_id
    _reactivate_parked_ungrouped(session, payload)
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.label_id = dest_id
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = dest_id
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            session.delete(example)
    parents: set[str | None] = set()
    for row in payload.get("reparented_children") or []:
        child = session.get(Label, row["id"])
        if child is not None:
            child.parent_id = target_id
            session.add(child)
    _compact(session, target_id)
    for source_id in payload.get("source_ids") or []:
        if source_id == target_id:
            continue
        source = session.get(Label, source_id)
        if source is not None:
            parents.add(source.parent_id)
            source.status = LABEL_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
    for parent_id in parents:
        _compact(session, parent_id)


def _invert_keep_source_split(session, payload: dict) -> None:
    for created_id in payload.get("created_ids") or []:
        created = session.get(Label, created_id)
        if created is not None:
            created.status = LABEL_INACTIVE
            created.updated_at = utcnow()
            session.add(created)
    _compact(session, payload.get("source_id"))
    for row in payload.get("created") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))
    for row in payload.get("replaced") or []:
        session.add(coding_from_dump(row))
    for row in payload.get("examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    _restore_reassigned(session, payload)


def _apply_keep_source_split(session, payload: dict) -> None:
    placements = []
    for created_id in payload.get("created_ids") or []:
        created = session.get(Label, created_id)
        if created is not None:
            placements.append((created, created.parent_id, created.position))
    placements.sort(key=lambda item: (item[2], item[0].name, item[0].id))
    for created, parent_id, position in placements:
        created.status = LABEL_ACTIVE
        created.updated_at = utcnow()
        session.add(created)
        _place(session, created, parent_id, position)
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("replaced") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("created") or []:
        session.add(coding_from_dump(row))
    for row in payload.get("deleted_examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("examples") or []:
        session.add(example_from_dump(row))
    ungrouped_id = payload.get("ungrouped_id")
    if ungrouped_id:
        _apply_reassigned(session, payload, ungrouped_id)


def _invert_split(session, payload: dict) -> None:
    if payload.get("keep_source"):
        # LLM split keeps the parent; rows without this flag are the old sibling-split operator.
        _invert_keep_source_split(session, payload)
        return
    source = session.get(Label, payload["source_id"])
    source.status = LABEL_ACTIVE
    source.updated_at = utcnow()
    session.add(source)
    for created_id in payload.get("created_ids") or []:
        created = session.get(Label, created_id)
        if created is not None:
            created.status = LABEL_INACTIVE
            created.updated_at = utcnow()
            session.add(created)
    _place(session, source, source.parent_id, source.position)
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))


def _apply_split(session, payload: dict) -> None:
    if payload.get("keep_source"):
        _apply_keep_source_split(session, payload)
        return
    source = session.get(Label, payload["source_id"])
    source.status = LABEL_INACTIVE
    source.updated_at = utcnow()
    session.add(source)
    _compact(session, source.parent_id)
    placements = []
    for created_id in payload.get("created_ids") or []:
        created = session.get(Label, created_id)
        if created is not None:
            placements.append((created, created.parent_id, created.position))
    placements.sort(key=lambda item: (item[2], item[0].name, item[0].id))
    for created, parent_id, position in placements:
        created.status = LABEL_ACTIVE
        created.updated_at = utcnow()
        session.add(created)
        _place(session, created, parent_id, position)
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)


def _invert_flatten(session, payload: dict) -> None:
    target_id = payload["label_id"]
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.label_id = row["from_label_id"]
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = row["from_label_id"]
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    for label_id in payload.get("descendant_ids") or []:
        row = session.get(Label, label_id)
        if row is not None:
            row.status = LABEL_ACTIVE
            row.updated_at = utcnow()
            session.add(row)


def _apply_flatten(session, payload: dict) -> None:
    target_id = payload["label_id"]
    for row in payload.get("reassigned_codings") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.label_id = target_id
            session.add(coding)
    for row in payload.get("reassigned_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            example.label_id = target_id
            session.add(example)
    for row in payload.get("deleted_examples") or []:
        example = session.get(LabelExample, row["id"])
        if example is not None:
            session.delete(example)
    for label_id in payload.get("descendant_ids") or []:
        row = session.get(Label, label_id)
        if row is not None:
            row.status = LABEL_INACTIVE
            row.updated_at = utcnow()
            session.add(row)


def _invert_remove(session, payload: dict) -> None:
    for row in payload.get("types") or []:
        session.add(label_from_dump(row))
    for row in payload.get("examples") or []:
        session.add(example_from_dump(row))
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))
    root = session.get(Label, payload["label_id"])
    if root is not None:
        _place(session, root, root.parent_id, root.position)


def _apply_remove(session, payload: dict) -> None:
    parent_id = None
    for row in payload.get("types") or []:
        if row.get("id") == payload.get("label_id"):
            parent_id = row.get("parent_id")
            break
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("types") or []:
        existing = session.get(Label, row["id"])
        if existing is not None:
            session.delete(existing)
    _compact(session, parent_id)


def _invert_recycle(session, payload: dict) -> None:
    for row in payload.get("created") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)
    for row in payload.get("modified_proposed") or []:
        proposed = session.get(Coding, row["id"])
        if proposed is not None:
            proposed.status = CODING_PROPOSED
            session.add(proposed)
    for row in payload.get("retired_accepted") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.status = row.get("status") or CODING_ACCEPTED
            session.add(coding)
    for row in payload.get("deleted_examples") or []:
        session.add(example_from_dump(row))
    _invert_add(session, payload)


def _apply_recycle(session, payload: dict) -> None:
    _apply_add(session, payload)
    for row in payload.get("modified_proposed") or []:
        proposed = session.get(Coding, row["id"])
        if proposed is not None:
            proposed.status = CODING_MODIFIED
            session.add(proposed)
    for row in payload.get("retired_accepted") or []:
        coding = session.get(Coding, row["id"])
        if coding is not None:
            coding.status = CODING_MODIFIED
            session.add(coding)
    for row in payload.get("created") or []:
        session.add(coding_from_dump(row))
    for row in payload.get("examples") or []:
        session.add(example_from_dump(row))
    for row in payload.get("deleted_examples") or []:
        existing = session.get(LabelExample, row["id"])
        if existing is not None:
            session.delete(existing)


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
    "verify": (_apply_verify, _invert_verify),
    "unverify": (_apply_unverify, _invert_unverify),
    "delete": (_apply_delete, _invert_delete),
    "flatten": (_apply_flatten, _invert_flatten),
    "remove": (_apply_remove, _invert_remove),
    "recycle": (_apply_recycle, _invert_recycle),
}
