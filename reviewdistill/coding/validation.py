from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import uuid4

from reviewdistill.coding.coder import effective_provider_name, hide_placeholder_coding
from reviewdistill.context.manuscript import extract_context, split_stored_context
from reviewdistill.db.models import (
    CODING_ACCEPTED,
    CODING_MODIFIED,
    CODING_PROPOSED,
    ISSUE_ACTIVE,
    QUALITY_DROPPED,
    QUALITY_UNREVIEWED,
    QUALITY_VERIFIED,
    Coding,
    IssueExample,
    IssueType,
    ProofreadingComment,
    comment_quality,
    in_manuscript,
    in_working_set,
    is_labeled,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import BadInput, Conflict, NotFound
from reviewdistill.history import dump_row, record
from reviewdistill.taxonomy.operations import add_child_issue_type, ensure_example
from reviewdistill.taxonomy.tree import active_children

VERIFY_MANUSCRIPT_CHANGED = "Verify (nearby manuscript changed)"
DROP_UNCHANGED = "Drop (nearby manuscript unchanged)"
VERIFY_FILE_MISSING = "Verify (source file missing)"
# Non-binding hint when the comment is not in the manuscript.
CONTEXT_CHANGE_THRESHOLD = 0.8


def _resolved_parent_id(session, parent_id: str | None) -> str | None:
    """Keep only an existing active type id. Unknown or omitted → root (None)."""
    if not parent_id:
        return None
    parent = session.get(IssueType, parent_id)
    if parent is None or parent.status != ISSUE_ACTIVE:
        return None
    return parent.id


@dataclass
class InboxIssue:
    id: str
    name: str
    parent_id: str | None


@dataclass
class InboxItem:
    comment: ProofreadingComment
    coding: Coding | None
    labeled: bool
    issue: InboxIssue | None = None


def _accepted_issue(session, comment_id: str) -> InboxIssue | None:
    for row in session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED):
        if not row.issue_type_id:
            continue
        issue = session.get(IssueType, row.issue_type_id)
        if issue is None or issue.status != ISSUE_ACTIVE:
            continue
        return InboxIssue(id=issue.id, name=issue.name, parent_id=issue.parent_id)
    return None


def inbox_items() -> list[InboxItem]:
    init_db()
    provider_name = effective_provider_name()
    with get_session() as session:
        comments = session.find(ProofreadingComment, order_by="created_at")
        items: list[InboxItem] = []
        for comment in comments:
            labeled = is_labeled(session, comment.id)
            needs_quality = (not in_manuscript(comment)) and comment_quality(comment) == QUALITY_UNREVIEWED
            unlabeled_in_set = in_working_set(comment) and not labeled
            if not (unlabeled_in_set or needs_quality):
                continue
            proposed = _latest_proposed(
                session, comment.id, provider_name=provider_name, skip_placeholders=True
            )
            items.append(
                InboxItem(
                    comment=comment,
                    coding=proposed,
                    labeled=labeled,
                    issue=_accepted_issue(session, comment.id) if labeled else None,
                )
            )
        return items


def verify_comment(comment_id: str) -> None:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        previous = comment_quality(comment)
        if previous == QUALITY_VERIFIED:
            return
        comment.quality = QUALITY_VERIFIED
        session.add(comment)
        record(session, "verify", {"comment_id": comment_id, "previous_quality": previous})
        session.commit()


def drop_comment(comment_id: str) -> None:
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        previous = comment_quality(comment)
        if previous == QUALITY_DROPPED:
            return
        comment.quality = QUALITY_DROPPED
        session.add(comment)
        record(session, "drop", {"comment_id": comment_id, "previous_quality": previous})
        session.commit()


def disappearance_guess(comment: ProofreadingComment, *, source: str | None) -> str:
    if source is None:
        return VERIFY_FILE_MISSING
    current = extract_context(source, comment.line_number, command=comment.source_command).context_text
    stored = split_stored_context(comment.context_text)[0]
    left = " ".join(stored.split())
    right = " ".join(current.split())
    ratio = SequenceMatcher(None, left, right).ratio()
    if ratio < CONTEXT_CHANGE_THRESHOLD:
        return VERIFY_MANUSCRIPT_CHANGED
    return DROP_UNCHANGED


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
        issue_type_id = coding.issue_type_id
        if issue_type_id is None:
            if not coding.proposed_issue_name:
                raise BadInput("Proposed coding has no issue type and no new-issue fields")
            existing = session.first(IssueType, status=ISSUE_ACTIVE, name=coding.proposed_issue_name)
            if existing is not None:
                issue = existing
                issue_type_id = existing.id
            else:
                issue = add_child_issue_type(
                    session,
                    name=coding.proposed_issue_name,
                    parent_id=_resolved_parent_id(session, coding.proposed_parent_id),
                    definition=coding.proposed_issue_definition or coding.proposed_issue_name,
                )
                issue_type_id = issue.id
        else:
            issue = session.get(IssueType, issue_type_id)
            if issue is None or issue.status != ISSUE_ACTIVE:
                raise NotFound(f"Unknown issue type {issue_type_id}")
        if active_children(session.find(IssueType), issue_type_id):
            raise BadInput("Can only assign a leaf issue type")
        coding.issue_type_id = issue_type_id
        coding.status = CODING_ACCEPTED
        session.add(coding)
        example, created = ensure_example(session, issue_type_id, comment.raw_text, comment_id)
        record(
            session,
            "accept",
            {
                "comment_id": comment_id,
                "coding_id": coding.id,
                "issue_type_id": issue_type_id,
                "previous_status": CODING_PROPOSED,
                "example_id": example.id,
                "example_created": created,
                "example": dump_row(example) if created else None,
            },
        )
        session.commit()
        session.refresh(coding)
        return coding


def change_coding(comment_id: str, *, issue_type_id: str) -> Coding:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None or issue.status != ISSUE_ACTIVE:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        if active_children(session.find(IssueType), issue_type_id):
            raise BadInput("Can only assign a leaf issue type")
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        current_accepted = list(session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED))
        if any(row.issue_type_id == issue_type_id for row in current_accepted):
            raise Conflict(f"Comment {comment_id} is already labeled with this type")
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
        for example in list(session.find(IssueExample, source_comment_id=comment_id)):
            deleted_examples.append(dump_row(example))
            session.delete(example)
        human = Coding(
            id=str(uuid4()),
            comment_id=comment_id,
            issue_type_id=issue_type_id,
            coder_type="human",
            status=CODING_ACCEPTED,
            rationale="Human selected an existing issue type.",
        )
        session.add(human)
        example, created = ensure_example(session, issue_type_id, comment.raw_text, comment_id)
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
