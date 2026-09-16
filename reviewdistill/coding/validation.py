from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import uuid4

from reviewdistill.coding.coder import effective_provider_name, hide_placeholder_coding
from reviewdistill.context.manuscript import extract_context
from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_MODIFIED,
    CODING_PROPOSED,
    LABEL_ACTIVE,
    Coding,
    LabelExample,
    Label,
    ProofreadingComment,
    in_manuscript,
    in_working_set,
    is_labeled,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import BadInput, Conflict, NotFound
from reviewdistill.history import dump_row, record
from reviewdistill.taxonomy.operations import add_child_label, ensure_example, example_text
from reviewdistill.taxonomy.tree import active_children

VERIFY_MANUSCRIPT_CHANGED = "Verify (nearby manuscript changed)"
DELETE_UNCHANGED = "Delete (nearby manuscript unchanged)"
VERIFY_FILE_MISSING = "Verify (source file missing)"
# Non-binding hint when the comment is not in the manuscript.
CONTEXT_CHANGE_THRESHOLD = 0.8


def _resolved_parent_id(session, parent_id: str | None) -> str | None:
    """Keep only an existing active type id. Unknown or omitted → root (None)."""
    if not parent_id:
        return None
    parent = session.get(Label, parent_id)
    if parent is None or parent.status != LABEL_ACTIVE:
        return None
    return parent.id


@dataclass
class InboxLabel:
    id: str
    name: str
    parent_id: str | None


@dataclass
class InboxItem:
    comment: ProofreadingComment
    coding: Coding | None
    labeled: bool
    label: InboxLabel | None = None


def _accepted_label(session, comment_id: str) -> InboxLabel | None:
    for row in session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED):
        if not row.label_id:
            continue
        label = session.get(Label, row.label_id)
        if label is None or label.status != LABEL_ACTIVE:
            continue
        return InboxLabel(id=label.id, name=label.name, parent_id=label.parent_id)
    return None


def inbox_items() -> list[InboxItem]:
    init_db()
    provider_name = effective_provider_name()
    with get_session() as session:
        comments = session.find(ProofreadingComment, order_by="created_at")
        items: list[InboxItem] = []
        for comment in comments:
            labeled = is_labeled(session, comment.id)
            needs_verify = (not in_manuscript(comment)) and not comment.verified
            unlabeled_in_set = in_working_set(comment) and not labeled
            if not (unlabeled_in_set or needs_verify):
                continue
            proposed = _latest_proposed(
                session, comment.id, provider_name=provider_name, skip_placeholders=True
            )
            items.append(
                InboxItem(
                    comment=comment,
                    coding=proposed,
                    labeled=labeled,
                    label=_accepted_label(session, comment.id) if labeled else None,
                )
            )
        return items


def verify_comment(comment_id: str) -> None:
    """Toggle protect. Same ``POST /api/inbox/{id}/verify`` either way."""
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        if comment.verified:
            comment.verified = False
            session.add(comment)
            record(session, "unverify", {"comment_id": comment_id})
            session.commit()
            return
        comment.verified = True
        session.add(comment)
        record(session, "verify", {"comment_id": comment_id})
        session.commit()


def delete_comment(comment_id: str) -> None:
    """Remove the observation. Refuses a verified row. Later extract of the same wording mints a new id."""
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        if comment.verified:
            raise Conflict("Unverify before deleting")
        payload = {
            "comment_id": comment_id,
            "comment": dump_row(comment),
            "codings": [dump_row(row) for row in session.find(Coding, comment_id=comment_id)],
            "examples": [
                dump_row(row) for row in session.find(LabelExample, source_comment_id=comment_id)
            ],
        }
        session.delete_comment_graph(comment)
        record(session, "delete", payload)
        session.commit()


def disappearance_guess(
    comment: ProofreadingComment,
    *,
    source: str | None,
    commands: list[str] | None = None,
) -> str:
    if source is None:
        return VERIFY_FILE_MISSING
    current = extract_context(
        source,
        comment.line_number,
        commands=commands,
        command=comment.source_command,
    ).context_text
    stored = comment.context_text or ""
    left = " ".join(stored.split())
    right = " ".join(current.split())
    ratio = SequenceMatcher(None, left, right).ratio()
    if ratio < CONTEXT_CHANGE_THRESHOLD:
        return VERIFY_MANUSCRIPT_CHANGED
    return DELETE_UNCHANGED


def _latest_proposed(
    session, comment_id: str, *, provider_name: str | None = None, skip_placeholders: bool = False
) -> Coding | None:
    rows = session.find(Coding, comment_id=comment_id, status=CODING_PROPOSED, order_by="created_at")
    if skip_placeholders:
        rows = [
            row for row in rows if not hide_placeholder_coding(row, provider_name=provider_name)
        ]
    return rows[-1] if rows else None


def accept_coding(comment_id: str) -> Coding:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        coding = _latest_proposed(session, comment_id)
        if coding is None:
            raise BadInput(f"No proposed coding for {comment_id}")
        label_id = coding.label_id
        if label_id is None:
            if not coding.proposed_label_name:
                raise BadInput("Proposed coding has no label and no new-label fields")
            existing = session.first(Label, status=LABEL_ACTIVE, name=coding.proposed_label_name)
            if existing is not None:
                label = existing
                label_id = existing.id
            else:
                label = add_child_label(
                    session,
                    name=coding.proposed_label_name,
                    parent_id=_resolved_parent_id(session, coding.proposed_parent_id),
                    definition=coding.proposed_label_definition or coding.proposed_label_name,
                )
                label_id = label.id
        else:
            label = session.get(Label, label_id)
            if label is None or label.status != LABEL_ACTIVE:
                raise NotFound(f"Unknown label {label_id}")
        if active_children(session.find(Label), label_id):
            raise BadInput("Can only assign a leaf label")
        coding.label_id = label_id
        coding.status = CODING_ACCEPTED
        session.add(coding)
        example, created, previous = ensure_example(session, label_id, example_text(comment), comment_id)
        example_updates = []
        if previous is not None:
            example_updates.append(
                {"id": example.id, "previous_text": previous, "text": example.text}
            )
        record(
            session,
            "accept",
            {
                "comment_id": comment_id,
                "coding_id": coding.id,
                "label_id": label_id,
                "previous_status": CODING_PROPOSED,
                "example_id": example.id,
                "example_created": created,
                "example": dump_row(example) if created else None,
                "example_updates": example_updates,
            },
        )
        session.commit()
        session.refresh(coding)
        return coding


def change_coding(comment_id: str, *, label_id: str) -> Coding:
    with get_session() as session:
        label = session.get(Label, label_id)
        if label is None or label.status != LABEL_ACTIVE:
            raise NotFound(f"Unknown label {label_id}")
        if active_children(session.find(Label), label_id):
            raise BadInput("Can only assign a leaf label")
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        current_accepted = list(session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED))
        if any(row.label_id == label_id for row in current_accepted):
            raise Conflict(f"Comment {comment_id} is already labeled with this label")
        proposed = _latest_proposed(session, comment_id)
        proposed_id = proposed.id if proposed is not None else None
        if proposed is not None:
            proposed.status = CODING_MODIFIED
            session.add(proposed)
        retired_accepted = []
        for row in current_accepted:
            retired_accepted.append(dump_row(row))
            row.status = CODING_MODIFIED
            session.add(row)
        deleted_examples = []
        for example in list(session.find(LabelExample, source_comment_id=comment_id)):
            deleted_examples.append(dump_row(example))
            session.delete(example)
        human = Coding(
            id=str(uuid4()),
            comment_id=comment_id,
            label_id=label_id,
            coder_type="human",
            status=CODING_ACCEPTED,
            rationale="Human selected an existing label.",
        )
        session.add(human)
        example, created, _previous = ensure_example(session, label_id, example_text(comment), comment_id)
        record(
            session,
            "change",
            {
                "comment_id": comment_id,
                "proposed_id": proposed_id,
                "coding_id": human.id,
                "coding": dump_row(human),
                "example_id": example.id,
                "example_created": created,
                "example": dump_row(example) if created else None,
                "retired_accepted": retired_accepted,
                "deleted_examples": deleted_examples,
            },
        )
        session.commit()
        session.refresh(human)
        return human
