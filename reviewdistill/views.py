"""Read models for the workbench. HTTP only serializes these dicts."""

from __future__ import annotations

from pathlib import Path

from reviewdistill.coding.coder import uncoded_comments
from reviewdistill.coding.validation import disappearance_guess, inbox_items
from reviewdistill.db.models import (
    CODING_ACCEPTED,
    Coding,
    IssueType,
    Project,
    ProofreadingComment,
    in_manuscript,
)
from reviewdistill.db.session import get_session
from reviewdistill.errors import NotFound
from reviewdistill.gitinfo import context_permalink, sanitize_remote_url
from reviewdistill.llm.base import get_provider
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


def _guess(comment: ProofreadingComment) -> str:
    with get_session() as session:
        project = session.get(Project, comment.project_id)
    source = None
    if project is not None:
        path = Path(project.root_path) / comment.file_path
        if path.is_file():
            source = path.read_text(errors="replace")
    return disappearance_guess(comment, source=source)


def inbox_payload() -> dict:
    with get_session():
        unlabeled = inbox_items()
        issues = [
            {"id": issue.id, "code": issue.code, "name": issue.name, "parent_id": issue.parent_id}
            for issue in list_active_issue_types()
        ]
        payload = []
        for item in unlabeled:
            payload.append(
                {
                    "comment": comment_json(item.comment),
                    "project_name": _project_name(item.comment.project_id),
                    "permalink": context_permalink(
                        item.comment.git_url,
                        item.comment.git_commit,
                        item.comment.file_path,
                        item.comment.line_number,
                    ),
                    "guess": _guess(item.comment) if not in_manuscript(item.comment) else None,
                    "in_manuscript": in_manuscript(item.comment),
                    "labeled": item.labeled,
                    "issue": (
                        {
                            "id": item.issue.id,
                            "code": item.issue.code,
                            "name": item.issue.name,
                            "parent_id": item.issue.parent_id,
                        }
                        if item.issue is not None
                        else None
                    ),
                    "coding": _coding_json(item.coding),
                }
            )
        llm_name = None
        try:
            llm_name = get_provider().name
        except RuntimeError:
            pass
        return {
            "unlabeled_count": len(unlabeled),
            "pending_code_count": len(uncoded_comments()),
            "llm_provider": llm_name,
            "issues": issues,
            "items": payload,
        }


def _accepted_type_json(session, comment_id: str) -> dict | None:
    for coding in session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED):
        if not coding.issue_type_id:
            continue
        issue = session.get(IssueType, coding.issue_type_id)
        if issue is None:
            continue
        return {
            "id": issue.id,
            "code": issue.code,
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
            "code": issue.code,
            "name": issue.name,
            "parent_id": issue.parent_id,
            "path": type_path(session.find(IssueType), issue.id),
            "definition": issue.definition,
            "notes": issue.notes,
            "status": issue.status,
            "examples": examples,
            "counterexamples": counterexamples,
            "comments": comments,
        }
