from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import uuid4

from reviewdistill.coding.coder import effective_provider_name, hide_placeholder_coding
from reviewdistill.context.manuscript import extract_context, split_stored_context
from reviewdistill.db.models import (
    WORKING_COMMENT_STATUSES,
    Coding,
    IssueExample,
    ProofreadingComment,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.history import dump_row, record
from reviewdistill.taxonomy.operations import (
    add_example,
    create_issue_type,
    get_active_issue_type_by_code,
    get_issue_type,
)

KEEP_MANUSCRIPT_CHANGED = "Keep (nearby manuscript changed)"
RETRACT_UNCHANGED = "Retract (nearby manuscript unchanged)"
KEEP_FILE_MISSING = "Keep (source file missing)"
# Non-binding Disappeared guess: first line of stored context vs current file at the last line number.
CONTEXT_CHANGE_THRESHOLD = 0.8


@dataclass
class InboxItem:
    comment: ProofreadingComment
    coding: Coding | None


def inbox_items() -> list[InboxItem]:
    init_db()
    provider_name = effective_provider_name()
    with get_session() as session:
        comments = session.find(
            ProofreadingComment, status=WORKING_COMMENT_STATUSES, order_by="created_at"
        )
        items: list[InboxItem] = []
        for comment in comments:
            codings = session.find(Coding, comment_id=comment.id)
            if any(row.status in {"accepted", "rejected", "modified"} for row in codings):
                continue
            proposed = _latest_proposed(
                session, comment.id, provider_name=provider_name, skip_placeholders=True
            )
            visible = [
                row
                for row in codings
                if not hide_placeholder_coding(row, provider_name=provider_name)
            ]
            if proposed is None and visible:
                continue
            items.append(InboxItem(comment=comment, coding=proposed))
        return items


def disappeared_items() -> list[InboxItem]:
    init_db()
    with get_session() as session:
        comments = session.find(ProofreadingComment, status="pending_disappeared", order_by="created_at")
        return [InboxItem(comment=comment, coding=None) for comment in comments]


def _existing_example(issue_type_id: str, comment_id: str) -> IssueExample | None:
    with get_session() as session:
        return session.first(
            IssueExample,
            issue_type_id=issue_type_id,
            source_comment_id=comment_id,
        )


def _log_event(event_type: str, payload: dict) -> None:
    with get_session() as session:
        record(session, event_type, payload)
        session.commit()


def keep_comment(comment_id: str) -> None:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise ValueError(f"Unknown comment {comment_id}")
        if comment.status != "pending_disappeared":
            raise ValueError("Keep requires a pending_disappeared comment")
        comment.status = "kept"
        session.add(comment)
        session.commit()
    _log_event("keep", {"comment_id": comment_id})


def retract_comment(comment_id: str) -> None:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise ValueError(f"Unknown comment {comment_id}")
        if comment.status != "pending_disappeared":
            raise ValueError("Retract requires a pending_disappeared comment")
        comment.status = "retracted"
        session.add(comment)
        session.commit()
    _log_event("retract", {"comment_id": comment_id})


def disappearance_guess(comment: ProofreadingComment, *, source: str | None) -> str:
    if source is None:
        return KEEP_FILE_MISSING
    current = extract_context(source, comment.line_number, command=comment.source_command).context_text
    stored = split_stored_context(comment.context_text)[0]
    left = " ".join(stored.split())
    right = " ".join(current.split())
    ratio = SequenceMatcher(None, left, right).ratio()
    if ratio < CONTEXT_CHANGE_THRESHOLD:
        return KEEP_MANUSCRIPT_CHANGED
    return RETRACT_UNCHANGED


def _latest_proposed(
    session, comment_id: str, *, provider_name: str | None = None, skip_placeholders: bool = False
) -> Coding | None:
    rows = session.find(Coding, comment_id=comment_id, status="proposed", order_by="created_at")
    if skip_placeholders:
        rows = [
            row for row in rows if not hide_placeholder_coding(row, provider_name=provider_name)
        ]
    return rows[-1] if rows else None


def accept_coding(comment_id: str) -> Coding:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise ValueError(f"Unknown comment {comment_id}")
        raw_text = comment.raw_text
        coding = _latest_proposed(session, comment_id)
        if coding is None:
            raise ValueError(f"No proposed coding for {comment_id}")
        coding_id = coding.id
        issue_type_id = coding.issue_type_id
        proposed_code = coding.proposed_issue_code
        proposed_name = coding.proposed_issue_name
        proposed_category = coding.proposed_issue_category
        proposed_definition = coding.proposed_issue_definition
        if issue_type_id is not None:
            coding.status = "accepted"
            session.add(coding)
            session.commit()
            session.refresh(coding)
            accepted = coding
        else:
            session.commit()
            accepted = None

    if issue_type_id is None:
        if not proposed_name:
            raise ValueError("Proposed coding has no issue type and no new-issue fields")
        code = proposed_code or _slug_code(proposed_name)
        existing = get_active_issue_type_by_code(code)
        if existing is not None:
            issue_type_id = existing.id
        else:
            issue = create_issue_type(
                code=code,
                name=proposed_name,
                category=proposed_category or "General",
                definition=proposed_definition or proposed_name,
            )
            issue_type_id = issue.id
        with get_session() as session:
            accepted = session.get(Coding, coding_id)
            accepted.issue_type_id = issue_type_id
            accepted.status = "accepted"
            session.add(accepted)
            session.commit()
            session.refresh(accepted)

    existing = _existing_example(issue_type_id, comment_id)
    example = add_example(issue_type_id, text=raw_text, source_comment_id=comment_id)
    created = existing is None
    _log_event(
        "accept",
        {
            "comment_id": comment_id,
            "coding_id": accepted.id,
            "issue_type_id": issue_type_id,
            "previous_status": "proposed",
            "example_id": example.id,
            "example_created": created,
            "example": dump_row(example) if created else None,
        },
    )
    return accepted


def change_coding(comment_id: str, *, issue_type_id: str) -> Coding:
    if get_issue_type(issue_type_id) is None:
        raise ValueError(f"Unknown issue type {issue_type_id}")
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise ValueError(f"Unknown comment {comment_id}")
        raw_text = comment.raw_text
        proposed = _latest_proposed(session, comment_id)
        proposed_id = proposed.id if proposed is not None else None
        if proposed is not None:
            proposed.status = "modified"
            session.add(proposed)
        human = Coding(
            id=str(uuid4()),
            comment_id=comment_id,
            issue_type_id=issue_type_id,
            coder_type="human",
            status="accepted",
            rationale="Human selected an existing issue type.",
        )
        session.add(human)
        session.commit()
        session.refresh(human)
        coding_dump = dump_row(human)
    existing = _existing_example(issue_type_id, comment_id)
    example = add_example(issue_type_id, text=raw_text, source_comment_id=comment_id)
    created = existing is None
    _log_event(
        "change",
        {
            "comment_id": comment_id,
            "proposed_id": proposed_id,
            "coding_id": human.id,
            "coding": coding_dump,
            "example_id": example.id,
            "example_created": created,
            "example": dump_row(example) if created else None,
        },
    )
    return human


def reject_coding(comment_id: str) -> Coding:
    with get_session() as session:
        proposed = _latest_proposed(session, comment_id)
        created = proposed is None
        previous_status = None if created else proposed.status
        if proposed is None:
            proposed = Coding(
                id=str(uuid4()),
                comment_id=comment_id,
                issue_type_id=None,
                coder_type="human",
                status="rejected",
                rationale="Human rejected without an AI proposal.",
            )
            session.add(proposed)
        else:
            proposed.status = "rejected"
            session.add(proposed)
        session.commit()
        session.refresh(proposed)
        dump = dump_row(proposed)
    _log_event(
        "reject",
        {
            "comment_id": comment_id,
            "coding_id": proposed.id,
            "previous_status": previous_status,
            "created": created,
            "coding": dump,
        },
    )
    return proposed


def _slug_code(name: str) -> str:
    return "".join(ch if ch.isalnum() else "" for ch in name.upper())[:16] or "NEWISSUE"
