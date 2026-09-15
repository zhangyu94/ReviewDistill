"""Read models for the UI. HTTP only serializes these dicts."""

from __future__ import annotations

from pathlib import Path

from reviewdistill.coding.coder import effective_provider_name, uncoded_comments
from reviewdistill.config import load_project_config
from reviewdistill.coding.validation import _latest_proposed, disappearance_guess, inbox_items
from reviewdistill.db.models import (
    CODING_ACCEPTED,
    LABEL_ACTIVE,
    Coding,
    Label,
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
    accepted_counts_by_label,
    get_label,
    list_active_labels,
    list_examples,
    list_working_observations,
)
from reviewdistill.taxonomy.tree import label_path, labels_to_forest


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
        "label_id": coding.label_id,
        "proposed_label_name": coding.proposed_label_name,
        "confidence": coding.confidence,
        "rationale": coding.rationale,
        "kind": "existing" if coding.label_id else "new",
    }


def _project_name(project_id: str) -> str:
    with get_session() as session:
        project = session.get(Project, project_id)
    return project.name if project is not None else project_id


def _source_file(comment: ProofreadingComment, project: Project | None) -> Path | None:
    if project is None:
        return None
    return comment_source_file(project.root_path, comment.file_path)


def _guess_from_source(
    comment: ProofreadingComment, source_path: Path | None, project: Project | None
) -> str:
    text = source_path.read_text(errors="replace") if source_path is not None else None
    commands = (
        load_project_config(Path(project.root_path)).latex_commands
        if project is not None
        else None
    )
    return disappearance_guess(comment, source=text, commands=commands)


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
    unreviewed = verified = 0
    for comment in comments:
        if comment.verified:
            verified += 1
        else:
            unreviewed += 1
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
    }


def _item_dict(comment, *, labeled: bool, label, coding, project: Project | None) -> dict:
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
        "guess": _guess_from_source(comment, source, project) if not in_manuscript(comment) else None,
        "in_manuscript": in_manuscript(comment),
        "labeled": labeled,
        "label": (
            {
                "id": label.id,
                "name": label.name,
                "parent_id": label.parent_id,
            }
            if label is not None
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
        labels = [
            {"id": row.id, "name": row.name, "parent_id": row.parent_id}
            for row in list_active_labels()
        ]
        payload = [
            _item_dict(
                item.comment,
                labeled=item.labeled,
                label=item.label,
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
            label = None
            if labeled:
                label_json = _accepted_label_json(session, comment.id)
                label = session.get(Label, label_json["id"]) if label_json else None
            working_payload.append(
                _item_dict(
                    comment,
                    labeled=labeled,
                    label=label,
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
        active_label_ids = {
            row.id for row in session.find(Label) if row.status == LABEL_ACTIVE
        }
        labeled_ids = {
            row.comment_id
            for row in session.find(Coding)
            if row.status == CODING_ACCEPTED and row.label_id in active_label_ids
        }
        return {
            "unlabeled_count": len(unlabeled),
            "pending_code_count": len(uncoded_comments()),
            "llm_provider": llm_name,
            "labels": labels,
            "items": payload,
            "working_items": working_payload,
            "progress": comment_progress(session.find(ProofreadingComment), labeled_ids),
        }


def _accepted_label_json(session, comment_id: str) -> dict | None:
    for coding in session.find(Coding, comment_id=comment_id, status=CODING_ACCEPTED):
        if not coding.label_id:
            continue
        label = session.get(Label, coding.label_id)
        if label is None or label.status != LABEL_ACTIVE:
            continue
        return {
            "id": label.id,
            "name": label.name,
            "parent_id": label.parent_id,
        }
    return None


def labels_payload() -> dict:
    with get_session() as session:
        labels = session.find(Label)
        counts = accepted_counts_by_label()
        return {"forest": labels_to_forest(labels, counts)}


def label_payload(label_id: str) -> dict:
    with get_session() as session:
        label = get_label(label_id)
        if label is None:
            raise NotFound(f"Unknown label {label_id}")
        examples = [{"id": row.id, "text": row.text} for row in list_examples(label_id)]
        comments = []
        for comment in list_working_observations(label_id):
            row = comment_json(comment)
            row["project_name"] = _project_name(comment.project_id)
            row["permalink"] = context_permalink(
                comment.git_url,
                comment.git_commit,
                comment.file_path,
                comment.line_number,
            )
            row["label"] = _accepted_label_json(session, comment.id)
            comments.append(row)
        return {
            "id": label.id,
            "name": label.name,
            "parent_id": label.parent_id,
            "path": label_path(session.find(Label), label.id),
            "definition": label.definition,
            "status": label.status,
            "examples": examples,
            "comments": comments,
        }
