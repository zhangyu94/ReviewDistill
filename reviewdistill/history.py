"""Linear undo/redo over ``taxonomy_events``.

Undo/Redo mark ``undone`` on the tip instead of appending. A new forward
action deletes the redo tail. Old merge/split rows without invert payload
fields are not invertible. ``propose`` is one event per Get AI suggestions
batch. Accept of a new issue type is ``add`` then ``accept``; undo Accept first.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlmodel import select

from reviewdistill.db.models import (
    Coding,
    IssueCounterexample,
    IssueExample,
    IssueType,
    ProofreadingComment,
    TaxonomyEvent,
    utcnow,
)
from reviewdistill.db.session import get_session, init_db

INVERTIBLE = frozenset(
    {
        "add",
        "rename",
        "edit",
        "move",
        "deactivate",
        "merge",
        "split",
        "propose",
        "accept",
        "change",
        "reject",
        "keep",
        "retract",
    }
)


def dump_row(row) -> dict:
    return row.model_dump(mode="json")


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def coding_from_dump(data: dict) -> Coding:
    data = dict(data)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return Coding(**data)


def example_from_dump(data: dict) -> IssueExample:
    data = dict(data)
    data["created_at"] = _parse_dt(data.get("created_at")) or utcnow()
    return IssueExample(**data)


def record(session, event_type: str, payload: dict) -> None:
    for event in list(session.exec(select(TaxonomyEvent).where(TaxonomyEvent.undone.is_(True)))):
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
        return f"Add {payload.get('name') or payload.get('code')}"
    if event_type == "rename":
        before = (payload.get("before") or {}).get("name")
        after = (payload.get("after") or {}).get("name")
        return f"Rename {before} → {after}"
    if event_type == "edit":
        return "Edit definition"
    if event_type == "move":
        return f"Move {payload.get('from')} → {payload.get('to')}"
    if event_type == "deactivate":
        return f"Deactivate {payload.get('code')}"
    if event_type == "merge":
        return "Merge issue types"
    if event_type == "split":
        return "Split issue type"
    if event_type == "propose":
        n = len(payload.get("created") or [])
        return f"Get AI suggestions ({n})"
    if event_type == "accept":
        return "Accept coding"
    if event_type == "change":
        return "Change coding"
    if event_type == "reject":
        return "Reject coding"
    if event_type == "keep":
        return "Keep comment"
    if event_type == "retract":
        return "Retract comment"
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
    return True


def list_history() -> dict:
    init_db()
    with get_session() as session:
        rows = list(session.exec(select(TaxonomyEvent).order_by(TaxonomyEvent.created_at.desc())))
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
            for event in session.exec(select(TaxonomyEvent).order_by(TaxonomyEvent.created_at))
            if not event.undone
        ]
        if not rows:
            raise ValueError("Nothing to undo")
        event = rows[-1]
        if not can_invert(event):
            raise ValueError("This event cannot be undone")
        _invert(session, event)
        event.undone = True
        session.add(event)
        session.commit()


def redo() -> None:
    init_db()
    with get_session() as session:
        undone = [
            event
            for event in session.exec(select(TaxonomyEvent).order_by(TaxonomyEvent.created_at))
            if event.undone
        ]
        if not undone:
            raise ValueError("Nothing to redo")
        event = undone[0]
        _apply(session, event)
        event.undone = False
        session.add(event)
        session.commit()


def _payload(event: TaxonomyEvent) -> dict:
    return json.loads(event.payload_json)


def _invert(session, event: TaxonomyEvent) -> None:
    payload = _payload(event)
    kind = event.event_type
    if kind == "rename":
        issue = session.get(IssueType, payload["issue_type_id"])
        before = payload["before"]
        issue.name = before["name"]
        issue.code = before["code"]
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "edit":
        issue = session.get(IssueType, payload["issue_type_id"])
        before = payload["before"]
        issue.definition = before["definition"]
        issue.notes = before.get("notes")
        issue.detection_guidance = before.get("detection_guidance")
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "move":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.category = payload["from"]
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "add":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.status = "inactive"
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "deactivate":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.status = "active"
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "merge":
        _invert_merge(session, payload)
        return
    if kind == "split":
        _invert_split(session, payload)
        return
    if kind == "propose":
        for row in payload.get("created") or []:
            existing = session.get(Coding, row["id"])
            if existing is not None:
                session.delete(existing)
        for row in payload.get("replaced") or []:
            session.add(coding_from_dump(row))
        return
    if kind == "accept":
        coding = session.get(Coding, payload["coding_id"])
        coding.status = payload.get("previous_status") or "proposed"
        session.add(coding)
        if payload.get("example_created") and payload.get("example_id"):
            example = session.get(IssueExample, payload["example_id"])
            if example is not None:
                session.delete(example)
        return
    if kind == "change":
        human = session.get(Coding, payload["coding_id"])
        if human is not None:
            session.delete(human)
        if payload.get("proposed_id"):
            proposed = session.get(Coding, payload["proposed_id"])
            if proposed is not None:
                proposed.status = "proposed"
                session.add(proposed)
        if payload.get("example_created") and payload.get("example_id"):
            example = session.get(IssueExample, payload["example_id"])
            if example is not None:
                session.delete(example)
        return
    if kind == "reject":
        coding = session.get(Coding, payload["coding_id"])
        if payload.get("created"):
            if coding is not None:
                session.delete(coding)
        elif coding is not None:
            coding.status = payload.get("previous_status") or "proposed"
            session.add(coding)
        return
    if kind in {"keep", "retract"}:
        comment = session.get(ProofreadingComment, payload["comment_id"])
        comment.status = "pending_disappeared"
        session.add(comment)
        return
    raise ValueError(f"Cannot invert {kind}")


def _apply(session, event: TaxonomyEvent) -> None:
    payload = _payload(event)
    kind = event.event_type
    if kind == "rename":
        issue = session.get(IssueType, payload["issue_type_id"])
        after = payload["after"]
        issue.name = after["name"]
        issue.code = after["code"]
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "edit":
        issue = session.get(IssueType, payload["issue_type_id"])
        after = payload["after"]
        issue.definition = after["definition"]
        issue.notes = after.get("notes")
        issue.detection_guidance = after.get("detection_guidance")
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "move":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.category = payload["to"]
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "add":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.status = "active"
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "deactivate":
        issue = session.get(IssueType, payload["issue_type_id"])
        issue.status = "inactive"
        issue.updated_at = utcnow()
        session.add(issue)
        return
    if kind == "merge":
        _apply_merge(session, payload)
        return
    if kind == "split":
        _apply_split(session, payload)
        return
    if kind == "propose":
        for row in payload.get("replaced") or []:
            existing = session.get(Coding, row["id"])
            if existing is not None:
                session.delete(existing)
        for row in payload.get("created") or []:
            session.add(coding_from_dump(row))
        return
    if kind == "accept":
        coding = session.get(Coding, payload["coding_id"])
        coding.status = "accepted"
        if payload.get("issue_type_id"):
            coding.issue_type_id = payload["issue_type_id"]
        session.add(coding)
        if payload.get("example_created") and payload.get("example"):
            session.add(example_from_dump(payload["example"]))
        return
    if kind == "change":
        if payload.get("proposed_id"):
            proposed = session.get(Coding, payload["proposed_id"])
            if proposed is not None:
                proposed.status = "modified"
                session.add(proposed)
        session.add(coding_from_dump(payload["coding"]))
        if payload.get("example_created") and payload.get("example"):
            session.add(example_from_dump(payload["example"]))
        return
    if kind == "reject":
        if payload.get("created"):
            session.add(coding_from_dump(payload["coding"]))
        else:
            coding = session.get(Coding, payload["coding_id"])
            coding.status = "rejected"
            session.add(coding)
        return
    if kind == "keep":
        comment = session.get(ProofreadingComment, payload["comment_id"])
        comment.status = "kept"
        session.add(comment)
        return
    if kind == "retract":
        comment = session.get(ProofreadingComment, payload["comment_id"])
        comment.status = "retracted"
        session.add(comment)
        return
    raise ValueError(f"Cannot redo {kind}")


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
            source.status = "active"
            source.updated_at = utcnow()
            session.add(source)


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
    for source_id in payload.get("source_ids") or []:
        if source_id == target_id:
            continue
        source = session.get(IssueType, source_id)
        if source is not None:
            source.status = "inactive"
            source.updated_at = utcnow()
            session.add(source)


def _invert_split(session, payload: dict) -> None:
    source = session.get(IssueType, payload["source_id"])
    source.status = "active"
    source.updated_at = utcnow()
    session.add(source)
    for created_id in payload.get("created_ids") or []:
        created = session.get(IssueType, created_id)
        if created is not None:
            created.status = "inactive"
            created.updated_at = utcnow()
            session.add(created)
    for row in payload.get("deleted_codings") or []:
        session.add(coding_from_dump(row))


def _apply_split(session, payload: dict) -> None:
    source = session.get(IssueType, payload["source_id"])
    source.status = "inactive"
    source.updated_at = utcnow()
    session.add(source)
    for created_id in payload.get("created_ids") or []:
        created = session.get(IssueType, created_id)
        if created is not None:
            created.status = "active"
            created.updated_at = utcnow()
            session.add(created)
    for row in payload.get("deleted_codings") or []:
        existing = session.get(Coding, row["id"])
        if existing is not None:
            session.delete(existing)
