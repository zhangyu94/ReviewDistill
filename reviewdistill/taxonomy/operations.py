from __future__ import annotations

from uuid import uuid4

from reviewdistill.db.models import (
    CODING_ACCEPTED,
    ISSUE_ACTIVE,
    ISSUE_INACTIVE,
    Coding,
    IssueCounterexample,
    IssueExample,
    IssueType,
    ProofreadingComment,
    in_working_set,
    utcnow,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.errors import Conflict, NotFound
from reviewdistill.history import dump_row, record


def _log(session, event_type: str, payload: dict) -> None:
    record(session, event_type, payload)


def _active_code_taken(session, code: str, *, except_id: str | None = None) -> bool:
    for issue in session.find(IssueType, status=ISSUE_ACTIVE, code=code):
        if except_id is None or issue.id != except_id:
            return True
    return False


def add_issue_type(
    session,
    *,
    code: str,
    name: str,
    category: str,
    definition: str,
    notes: str | None = None,
    detection_guidance: str | None = None,
) -> IssueType:
    if _active_code_taken(session, code):
        raise Conflict(f"Issue code {code} is already in use")
    issue = IssueType(
        id=str(uuid4()),
        code=code,
        name=name,
        category=category,
        definition=definition,
        notes=notes,
        detection_guidance=detection_guidance,
        status=ISSUE_ACTIVE,
    )
    session.add(issue)
    record(session, "add", {"issue_type_id": issue.id, "code": code, "name": name})
    return issue


def create_issue_type(
    *,
    code: str,
    name: str,
    category: str,
    definition: str,
    notes: str | None = None,
    detection_guidance: str | None = None,
) -> IssueType:
    init_db()
    with get_session() as session:
        issue = add_issue_type(
            session,
            code=code,
            name=name,
            category=category,
            definition=definition,
            notes=notes,
            detection_guidance=detection_guidance,
        )
        session.commit()
        session.refresh(issue)
        return issue


def list_active_issue_types() -> list[IssueType]:
    init_db()
    with get_session() as session:
        return sorted(
            session.find(IssueType, status=ISSUE_ACTIVE),
            key=lambda issue: (issue.category, issue.name),
        )


def get_issue_type(issue_type_id: str) -> IssueType | None:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None or issue.status != ISSUE_ACTIVE:
            return None
        return issue


def get_active_issue_type_by_code(code: str) -> IssueType | None:
    with get_session() as session:
        return session.first(IssueType, status=ISSUE_ACTIVE, code=code)


def ensure_example(
    session,
    issue_type_id: str,
    text: str,
    source_comment_id: str | None = None,
) -> tuple[IssueExample, bool]:
    cleaned = " ".join(text.split())
    if source_comment_id:
        existing = session.first(
            IssueExample,
            issue_type_id=issue_type_id,
            source_comment_id=source_comment_id,
        )
        if existing is not None:
            return existing, False
    row = IssueExample(
        id=str(uuid4()),
        issue_type_id=issue_type_id,
        text=cleaned,
        source_comment_id=source_comment_id,
    )
    session.add(row)
    return row, True


def add_example(issue_type_id: str, text: str, source_comment_id: str | None = None) -> IssueExample:
    with get_session() as session:
        row, _created = ensure_example(session, issue_type_id, text, source_comment_id)
        session.commit()
        session.refresh(row)
        return row


def add_counterexample(
    issue_type_id: str, text: str, source_comment_id: str | None = None
) -> IssueCounterexample:
    cleaned = " ".join(text.split())
    with get_session() as session:
        row = IssueCounterexample(
            id=str(uuid4()),
            issue_type_id=issue_type_id,
            text=cleaned,
            source_comment_id=source_comment_id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_examples(issue_type_id: str) -> list[IssueExample]:
    with get_session() as session:
        rows = session.find(IssueExample, issue_type_id=issue_type_id)
        return [
            row
            for row in rows
            if _source_in_working_set(session, row.source_comment_id)
            and _example_matches_current_label(session, row)
        ]


def list_counterexamples(issue_type_id: str) -> list[IssueCounterexample]:
    with get_session() as session:
        rows = session.find(IssueCounterexample, issue_type_id=issue_type_id)
        return [row for row in rows if _source_in_working_set(session, row.source_comment_id)]


def _source_in_working_set(session, source_comment_id: str | None) -> bool:
    if source_comment_id is None:
        return True
    comment = session.get(ProofreadingComment, source_comment_id)
    return comment is not None and in_working_set(comment)


def _example_matches_current_label(session, example: IssueExample) -> bool:
    if example.source_comment_id is None:
        return True
    return any(
        coding.status == CODING_ACCEPTED and coding.issue_type_id == example.issue_type_id
        for coding in session.find(Coding, comment_id=example.source_comment_id)
    )


def accepted_counts_by_issue_type() -> dict[str, int]:
    init_db()
    counts: dict[str, int] = {}
    with get_session() as session:
        for coding in session.find(Coding, status=CODING_ACCEPTED):
            if not coding.issue_type_id:
                continue
            if not _source_in_working_set(session, coding.comment_id):
                continue
            counts[coding.issue_type_id] = counts.get(coding.issue_type_id, 0) + 1
    return counts


def list_working_observations(issue_type_id: str) -> list[ProofreadingComment]:
    init_db()
    with get_session() as session:
        seen: set[str] = set()
        comments: list[ProofreadingComment] = []
        for coding in session.find(Coding, issue_type_id=issue_type_id, status=CODING_ACCEPTED):
            if coding.comment_id in seen:
                continue
            comment = session.get(ProofreadingComment, coding.comment_id)
            if comment is None or not in_working_set(comment):
                continue
            seen.add(comment.id)
            comments.append(comment)
        return comments


def rename_issue_type(issue_type_id: str, *, name: str, code: str | None = None) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        if code and _active_code_taken(session, code, except_id=issue_type_id):
            raise Conflict(f"Issue code {code} is already in use")
        before = {"name": issue.name, "code": issue.code}
        issue.name = name
        if code:
            issue.code = code
        issue.updated_at = utcnow()
        _log(
            session,
            "rename",
            {
                "issue_type_id": issue_type_id,
                "before": before,
                "after": {"name": issue.name, "code": issue.code},
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def edit_issue_type(
    issue_type_id: str,
    *,
    definition: str | None = None,
    notes: str | None = None,
    detection_guidance: str | None = None,
) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        before = {
            "definition": issue.definition,
            "notes": issue.notes,
            "detection_guidance": issue.detection_guidance,
        }
        if definition is not None:
            issue.definition = definition
        if notes is not None:
            issue.notes = notes
        if detection_guidance is not None:
            issue.detection_guidance = detection_guidance
        issue.updated_at = utcnow()
        _log(
            session,
            "edit",
            {
                "issue_type_id": issue_type_id,
                "before": before,
                "after": {
                    "definition": issue.definition,
                    "notes": issue.notes,
                    "detection_guidance": issue.detection_guidance,
                },
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def move_issue_type(issue_type_id: str, *, category: str) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        before = issue.category
        issue.category = category
        issue.updated_at = utcnow()
        if before != category:
            _log(session, "move", {"issue_type_id": issue_type_id, "from": before, "to": category})
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def deactivate_issue_type(issue_type_id: str) -> IssueType:
    with get_session() as session:
        issue = session.get(IssueType, issue_type_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_type_id}")
        comment_ids = {
            coding.comment_id
            for coding in session.find(Coding, issue_type_id=issue_type_id)
            if coding.status == CODING_ACCEPTED
        }
        deleted_codings = []
        for comment_id in comment_ids:
            for row in list(session.find(Coding, comment_id=comment_id)):
                deleted_codings.append(dump_row(row))
                session.delete(row)
        issue.status = ISSUE_INACTIVE
        issue.updated_at = utcnow()
        _log(
            session,
            "deactivate",
            {
                "issue_type_id": issue_type_id,
                "code": issue.code,
                "deleted_codings": deleted_codings,
            },
        )
        session.add(issue)
        session.commit()
        session.refresh(issue)
        return issue


def merge_issue_types(*, source_ids: list[str], target_id: str) -> IssueType:
    """Fold sources into target: reassign codings/examples/counterexamples, then deactivate sources."""
    with get_session() as session:
        target = session.get(IssueType, target_id)
        if target is None:
            raise NotFound(f"Unknown issue type {target_id}")
        reassigned_codings = []
        reassigned_examples = []
        deleted_examples = []
        reassigned_counters = []
        for source_id in source_ids:
            if source_id == target_id:
                continue
            source = session.get(IssueType, source_id)
            if source is None:
                raise NotFound(f"Unknown issue type {source_id}")
            for coding in session.find(Coding, issue_type_id=source_id):
                reassigned_codings.append({"id": coding.id, "from_issue_type_id": source_id})
                coding.issue_type_id = target_id
                session.add(coding)
            for example in list(session.find(IssueExample, issue_type_id=source_id)):
                if example.source_comment_id:
                    existing = session.first(
                        IssueExample,
                        issue_type_id=target_id,
                        source_comment_id=example.source_comment_id,
                    )
                    if existing is not None:
                        deleted_examples.append(dump_row(example))
                        session.delete(example)
                        continue
                reassigned_examples.append({"id": example.id, "from_issue_type_id": source_id})
                example.issue_type_id = target_id
                session.add(example)
            for counter in session.find(IssueCounterexample, issue_type_id=source_id):
                reassigned_counters.append({"id": counter.id, "from_issue_type_id": source_id})
                counter.issue_type_id = target_id
                session.add(counter)
            source.status = ISSUE_INACTIVE
            source.updated_at = utcnow()
            session.add(source)
        _log(
            session,
            "merge",
            {
                "source_ids": source_ids,
                "target_id": target_id,
                "reassigned_codings": reassigned_codings,
                "reassigned_examples": reassigned_examples,
                "deleted_examples": deleted_examples,
                "reassigned_counters": reassigned_counters,
            },
        )
        session.add(target)
        session.commit()
        session.refresh(target)
        return target


def split_issue_type(source_id: str, *, left: dict, right: dict) -> tuple[IssueType, IssueType]:
    with get_session() as session:
        source = session.get(IssueType, source_id)
        if source is None:
            raise NotFound(f"Unknown issue type {source_id}")
        left_code = left["code"]
        right_code = right["code"]
        if left_code == right_code:
            raise Conflict(f"Issue code {left_code} is already in use")
        for code in (left_code, right_code):
            if _active_code_taken(session, code, except_id=source_id):
                raise Conflict(f"Issue code {code} is already in use")
        comment_ids = {
            coding.comment_id
            for coding in session.find(Coding, issue_type_id=source_id)
            if coding.status == CODING_ACCEPTED
        }
        deleted_codings = []
        for comment_id in comment_ids:
            for row in list(session.find(Coding, comment_id=comment_id)):
                deleted_codings.append(dump_row(row))
                session.delete(row)
        source.status = ISSUE_INACTIVE
        source.updated_at = utcnow()
        created = []
        for spec in (left, right):
            issue = IssueType(
                id=str(uuid4()),
                code=spec["code"],
                name=spec["name"],
                category=spec["category"],
                definition=spec["definition"],
                status=ISSUE_ACTIVE,
            )
            session.add(issue)
            created.append(issue)
        _log(
            session,
            "split",
            {
                "source_id": source_id,
                "created_ids": [issue.id for issue in created],
                "deleted_codings": deleted_codings,
            },
        )
        session.add(source)
        session.commit()
        for issue in created:
            session.refresh(issue)
        return created[0], created[1]
