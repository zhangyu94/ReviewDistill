"""Read models for the UI. HTTP only serializes these dicts."""

from __future__ import annotations

from pathlib import Path

from reviewdistill.coding.coder import effective_provider_name, uncoded_comments
from reviewdistill.coding.validation import _latest_proposed, disappearance_guess, inbox_items
from reviewdistill.db.models import (
    CODING_ACCEPTED,
    ISSUE_ACTIVE,
    Coding,
    IssueType,
    Project,
    ProofreadingComment,
    in_manuscript,
    in_working_set,
    is_labeled,
)
from reviewdistill.db.session import get_session
from reviewdistill.errors import NotFound
from reviewdistill.gitinfo import context_permalink, sanitize_remote_url
from reviewdistill.llm.base import get_provider
from reviewdistill.manuscript import comment_source_file
from reviewdistill.paths import reveal_in_file_manager
from reviewdistill.taxonomy.operations import (
    accepted_counts_by_issue_type,
    get_issue_type,
    list_active_issue_types,
    list_counterexamples,
    list_examples,
    list_working_observations,
)
from reviewdistill.taxonomy.tree import type_path, types_to_forest


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def comment_json(comment: ProofreadingComment) -> dict:
    data = comment.model_dump(mode="json")
    data["created_at"] = _iso(comment.created_at)
    data["git_url"] = sanitize_remote_url(comment.git_url)
    return data


def _coding_json(coding) -> dict | None:
    if coding is None:
        return None
    return {
        "id": coding.id,
        "status": coding.status,
        "issue_type_id": coding.issue_type_id,
        "proposed_issue_name": coding.proposed_issue_name,
        "confidence": coding.confidence,
        "rationale": coding.rationale,
        "kind": "existing" if coding.issue_type_id else "new",
    }


def _project_name(project_id: str) -> str:
    with get_session() as session:
        project = session.get(Project, project_id)
    return project.name if project is not None else project_id


def _source_file(comment: ProofreadingComment, project: Project | None) -> Path | None:
    if project is None:
        return None
    return comment_source_file(project.root_path, comment.file_path)


def _guess_from_source(comment: ProofreadingComment, source_path: Path | None) -> str:
    text = source_path.read_text(errors="replace") if source_path is not None else None
    return disappearance_guess(comment, source=text)


def reveal_comment_file(comment_id: str) -> Path:
    """Show the comment's ``.tex`` file in the OS file manager.

    The path is resolved from the stored comment and project root. The client
    sends only ``comment_id``; a ``file://`` href from the UI is blocked on
    localhost.
    """
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        if comment is None:
            raise NotFound(f"Unknown comment {comment_id}")
        project = session.get(Project, comment.project_id)
    if project is None:
        raise NotFound("This file is not on this computer.")
    path = comment_source_file(project.root_path, comment.file_path)
    if path is None:
        raise NotFound("This file is not on this computer.")
    reveal_in_file_manager(path)
    return path


def comment_progress(comments: list, labeled_ids: set[str]) -> dict:
    """Footer counts. ``unlabeled`` here is comments to distill only, not the Unlabeled chip.

    There is no ``absent`` key. Presence is ``in_manuscript`` on each item.
    """
    working_set = unlabeled = labeled = 0
    unreviewed = verified = dropped = 0
    for comment in comments:
        quality = comment.quality
        if quality == "unreviewed":
            unreviewed += 1
        elif quality == "verified":
            verified += 1
        elif quality == "dropped":
            dropped += 1
        if in_working_set(comment):
            working_set += 1
            if comment.id in labeled_ids:
                labeled += 1
            else:
                unlabeled += 1
    return {
        "working_set": working_set,
        "unlabeled": unlabeled,
        "labeled": labeled,
        "unreviewed": unreviewed,
        "verified": verified,
        "dropped": dropped,
    }


def _item_dict(comment, *, labeled: bool, issue, coding, project: Project | None) -> dict:
    source = _source_file(comment, project)
    return {
        "comment": comment_json(comment),
        "project_name": project.name if project is not None else comment.project_id,
        "permalink": context_permalink(
            comment.git_url,
            comment.git_commit,
            comment.file_path,
            comment.line_number,
        ),
        "guess": _guess_from_source(comment, source) if not in_manuscript(comment) else None,
        "in_manuscript": in_manuscript(comment),
        "labeled": labeled,
        "issue": (
            {
                "id": issue.id,
                "name": issue.name,
                "parent_id": issue.parent_id,
            }
            if issue is not None
            else None
        ),
        "coding": _coding_json(coding),
        "in_working_set": in_working_set(comment),
        "local_file": source is not None,
    }


def inbox_payload() -> dict:
    """Inbox JSON for the UI.

    ``items`` is the Unlabeled queue. ``working_items`` is every comment to distill
    row (labeled included) so the client can AND chips without extra fetches.
    """
    with get_session() as session:
        unlabeled = inbox_items()
        projects = {row.id: row for row in session.find(Project)}
        issues = [
            {"id": issue.id, "name": issue.name, "parent_id": issue.parent_id}
            for issue in list_active_issue_types()
        ]
        payload = [
            _item_dict(
                item.comment,
                labeled=item.labeled,
                issue=item.issue,
                coding=item.coding,
                project=projects.get(item.comment.project_id),
            )
            for item in unlabeled
        ]
        provider_name = effective_provider_name()
        working_payload = []
        for comment in session.find(ProofreadingComment, order_by="created_at"):
            if not in_working_set(comment):
                continue
            labeled = is_labeled(session, comment.id)
            issue = None
            if labeled:
                issue_json = _accepted_type_json(session, comment.id)
                issue = session.get(IssueType, issue_json["id"]) if issue_json else None
            working_payload.append(
                _item_dict(
                    comment,
                    labeled=labeled,
                    issue=issue,
                    coding=_latest_proposed(
                        session, comment.id, provider_name=provider_name, skip_placeholders=True
                    ),
                    project=projects.get(comment.project_id),
                )
            )
        llm_name = None
        try:
            llm_name = get_provider().name
        except RuntimeError:
            pass
        active_type_ids = {
            row.id for row in session.find(IssueType) if row.status == ISSUE_ACTIVE
        }
        labeled_ids = {
            row.comment_id
            for row in session.find(Coding)
            if row.status == CODING_ACCEPTED and row.issue_type_id in active_type_ids
        }
        return {
            "unlabeled_count": len(unlabeled),
            "pending_code_count": len(uncoded_comments()),
            "llm_provider": llm_name,
            "issues": issues,
            "items": payload,
            "working_items": working_payload,
            "progress": comment_progress(session.find(ProofreadingComment), labeled_ids),
        }


def _accepted_type_json(session, comment_id: str) -> dict | None:
    for coding in session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED):
        if not coding.issue_type_id:
            continue
        issue = session.get(IssueType, coding.issue_type_id)
        if issue is None or issue.status != ISSUE_ACTIVE:
            continue
        return {
            "id": issue.id,
            "name": issue.name,
            "parent_id": issue.parent_id,
        }
    return None


def taxonomy_payload() -> dict:
    with get_session() as session:
        types = session.find(IssueType)
        counts = accepted_counts_by_issue_type()
        return {"forest": types_to_forest(types, counts)}


def issue_payload(issue_id: str) -> dict:
    with get_session() as session:
        issue = get_issue_type(issue_id)
        if issue is None:
            raise NotFound(f"Unknown issue type {issue_id}")
        examples = [{"id": row.id, "text": row.text} for row in list_examples(issue_id)]
        counterexamples = [{"id": row.id, "text": row.text} for row in list_counterexamples(issue_id)]
        comments = []
        for comment in list_working_observations(issue_id):
            row = comment_json(comment)
            row["project_name"] = _project_name(comment.project_id)
            row["permalink"] = context_permalink(
                comment.git_url,
                comment.git_commit,
                comment.file_path,
                comment.line_number,
            )
            row["issue"] = _accepted_type_json(session, comment.id)
            comments.append(row)
        return {
            "id": issue.id,
            "name": issue.name,
            "parent_id": issue.parent_id,
            "path": type_path(session.find(IssueType), issue.id),
            "definition": issue.definition,
            "status": issue.status,
            "examples": examples,
            "counterexamples": counterexamples,
            "comments": comments,
        }
