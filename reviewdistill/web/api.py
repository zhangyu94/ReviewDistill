from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from reviewdistill.coding.coder import code_uncoded_comments, uncoded_comments
from reviewdistill.coding.validation import (
    accept_coding,
    change_coding,
    disappearance_guess,
    disappeared_items,
    inbox_items,
    keep_comment,
    reject_coding,
    retract_comment,
)
from reviewdistill.config import (
    LLM_SETTINGS_PROVIDERS,
    PROVIDER_ENV_KEYS,
    default_llm_model,
    default_registered_project_id,
    ensure_env_gitignore,
    list_registered_project_rows,
    llm_selected_payload,
    paper_key_set,
    upsert_env_var,
    write_project_llm,
)
from reviewdistill.db.models import Project, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.gitinfo import context_permalink, sanitize_remote_url
from reviewdistill.history import list_history, redo, undo
from reviewdistill.llm.base import get_provider
from reviewdistill.paths import data_location, project_env_path
from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    accepted_counts_by_issue_type,
    add_counterexample,
    deactivate_issue_type,
    edit_issue_type,
    get_issue_type,
    list_active_issue_types,
    list_counterexamples,
    list_examples,
    list_working_observations,
    merge_issue_types,
    move_issue_type,
    rename_issue_type,
    split_issue_type,
)

router = APIRouter()


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _comment_json(comment: ProofreadingComment) -> dict:
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


@router.get("/inbox")
def get_inbox(view: str = "uncoded"):
    view = view if view == "disappeared" else "uncoded"
    with get_session():
        uncoded = inbox_items()
        disappeared = disappeared_items()
        items = disappeared if view == "disappeared" else uncoded
        issues = [
            {"id": issue.id, "code": issue.code, "name": issue.name, "category": issue.category}
            for issue in list_active_issue_types()
        ]
        payload = []
        for item in items:
            payload.append(
                {
                    "comment": _comment_json(item.comment),
                    "project_name": _project_name(item.comment.project_id),
                    "permalink": context_permalink(
                        item.comment.git_url,
                        item.comment.git_commit,
                        item.comment.file_path,
                        item.comment.line_number,
                    ),
                    "guess": _guess(item.comment) if view == "disappeared" else None,
                    "coding": _coding_json(item.coding),
                }
            )
        pending = len(uncoded_comments())
        llm_name = None
        try:
            llm_name = get_provider().name
        except RuntimeError:
            pass
        return {
            "view": view,
            "uncoded_count": len(uncoded),
            "disappeared_count": len(disappeared),
            "pending_code_count": pending,
            "llm_provider": llm_name,
            "issues": issues,
            "items": payload,
        }


def _mutate(fn):
    try:
        fn()
    except ValueError as exc:
        msg = str(exc)
        status = 404 if msg.startswith("Unknown") else 400
        raise HTTPException(status_code=status, detail=msg) from exc
    return {"ok": True}


class ChangeBody(BaseModel):
    issue_type_id: str


_LLM_FAILED = "LLM request failed"


@router.post("/inbox/code")
def post_code():
    """Propose issue types for every uncoded working-dataset comment. There is no CLI ``code`` command."""
    try:
        summary = code_uncoded_comments()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=_LLM_FAILED) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith(_LLM_FAILED):
            raise HTTPException(status_code=400, detail=_LLM_FAILED) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "coded": summary.coded,
        "failed": summary.skipped,
        "privacy_warning": summary.privacy_warning,
    }


@router.post("/inbox/{comment_id}/accept")
def post_accept(comment_id: str):
    return _mutate(lambda: accept_coding(comment_id))


@router.post("/inbox/{comment_id}/reject")
def post_reject(comment_id: str):
    return _mutate(lambda: reject_coding(comment_id))


@router.post("/inbox/{comment_id}/change")
def post_change(comment_id: str, body: ChangeBody):
    return _mutate(lambda: change_coding(comment_id, issue_type_id=body.issue_type_id))


@router.post("/inbox/{comment_id}/keep")
def post_keep(comment_id: str):
    return _mutate(lambda: keep_comment(comment_id))


@router.post("/inbox/{comment_id}/retract")
def post_retract(comment_id: str):
    return _mutate(lambda: retract_comment(comment_id))


class RenameBody(BaseModel):
    name: str
    code: str


class EditBody(BaseModel):
    definition: str
    notes: str = ""
    category: str


class MoveBody(BaseModel):
    category: str


class CounterexampleBody(BaseModel):
    text: str


class MergeBody(BaseModel):
    source_ids: list[str]
    target_id: str


class SplitSide(BaseModel):
    code: str
    name: str
    category: str
    definition: str


class SplitBody(BaseModel):
    left: SplitSide
    right: SplitSide


@router.get("/taxonomy")
def get_taxonomy():
    with get_session():
        issues = list_active_issue_types()
        counts = accepted_counts_by_issue_type()
        grouped: dict[str, list] = {}
        for issue in issues:
            grouped.setdefault(issue.category, []).append(
                {
                    "id": issue.id,
                    "code": issue.code,
                    "name": issue.name,
                    "count": counts.get(issue.id, 0),
                }
            )
        return {"grouped": grouped}


@router.post("/taxonomy/merge")
def post_merge(body: MergeBody):
    return _mutate(lambda: merge_issue_types(source_ids=body.source_ids, target_id=body.target_id))


@router.get("/taxonomy/export")
def get_export(format: str = "md"):
    try:
        text = export_rubric(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    media = "text/markdown; charset=utf-8"
    if format == "yaml":
        media = "application/yaml; charset=utf-8"
    elif format == "json":
        media = "application/json; charset=utf-8"
    return PlainTextResponse(text, media_type=media)


@router.get("/paths")
def get_paths():
    """Home folder and comments JSONL. Copy the folder to back up."""
    return data_location()


@router.get("/llm-settings")
def get_llm_settings(project_id: str | None = None):
    """Paper list + selected YAML/``.env`` state. Never includes the API key (``key_set`` only)."""
    projects = list_registered_project_rows()
    default_id = default_registered_project_id()
    selected_id = project_id or default_id
    selected = llm_selected_payload(selected_id) if selected_id else None
    if project_id and selected is None:
        raise HTTPException(status_code=404, detail="Unknown project")
    return {
        "projects": projects,
        "default_project_id": default_id,
        "selected": selected,
    }


class LlmSettingsBody(BaseModel):
    project_id: str
    provider: str
    model: str = ""
    api_key: str = ""


@router.post("/llm-settings")
def post_llm_settings(body: LlmSettingsBody):
    """Save provider/model to YAML and optional key to gitignored ``.env``. Empty ``api_key`` keeps the existing key."""
    provider = body.provider.lower().strip()
    if provider not in LLM_SETTINGS_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown LLM provider")
    with get_session() as session:
        project = session.get(Project, body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Unknown project")
    root = Path(project.root_path)
    model = body.model.strip() or default_llm_model(provider)
    env_name = PROVIDER_ENV_KEYS[provider]
    incoming = body.api_key.strip()
    if not incoming and not paper_key_set(root, provider):
        raise HTTPException(
            status_code=400,
            detail=f"Paste an API key for {provider} ({env_name})",
        )
    write_project_llm(root, provider=provider, model=model)
    if incoming:
        upsert_env_var(project_env_path(root), env_name, incoming)
    ensure_env_gitignore(root)
    return {"ok": True, "key_set": paper_key_set(root, provider)}


@router.get("/taxonomy/{issue_id}")
def get_issue(issue_id: str):
    with get_session():
        issue = get_issue_type(issue_id)
        if issue is None:
            raise HTTPException(status_code=404, detail=f"Unknown issue type {issue_id}")
        examples = [{"id": row.id, "text": row.text} for row in list_examples(issue_id)]
        counterexamples = [{"id": row.id, "text": row.text} for row in list_counterexamples(issue_id)]
        comments = []
        for comment in list_working_observations(issue_id):
            row = _comment_json(comment)
            row["project_name"] = _project_name(comment.project_id)
            row["permalink"] = context_permalink(
                comment.git_url,
                comment.git_commit,
                comment.file_path,
                comment.line_number,
            )
            comments.append(row)
        return {
            "id": issue.id,
            "code": issue.code,
            "name": issue.name,
            "category": issue.category,
            "definition": issue.definition,
            "notes": issue.notes,
            "status": issue.status,
            "examples": examples,
            "counterexamples": counterexamples,
            "comments": comments,
        }


@router.post("/taxonomy/{issue_id}/rename")
def post_rename(issue_id: str, body: RenameBody):
    return _mutate(lambda: rename_issue_type(issue_id, name=body.name, code=body.code))


@router.post("/taxonomy/{issue_id}/edit")
def post_edit(issue_id: str, body: EditBody):
    def run():
        edit_issue_type(
            issue_id,
            definition=body.definition,
            notes=body.notes or None,
        )
        move_issue_type(issue_id, category=body.category)

    return _mutate(run)


@router.post("/taxonomy/{issue_id}/move")
def post_move(issue_id: str, body: MoveBody):
    """Category-only move so a workbench drag does not round-trip definition fields."""
    return _mutate(lambda: move_issue_type(issue_id, category=body.category))


@router.post("/taxonomy/{issue_id}/deactivate")
def post_deactivate(issue_id: str):
    return _mutate(lambda: deactivate_issue_type(issue_id))


@router.post("/taxonomy/{issue_id}/counterexample")
def post_counterexample(issue_id: str, body: CounterexampleBody):
    return _mutate(lambda: add_counterexample(issue_id, text=body.text))


@router.post("/taxonomy/{issue_id}/split")
def post_split(issue_id: str, body: SplitBody):
    return _mutate(
        lambda: split_issue_type(
            issue_id,
            left=body.left.model_dump(),
            right=body.right.model_dump(),
        )
    )


@router.get("/history")
def get_history():
    return list_history()


@router.post("/history/undo")
def post_history_undo():
    return _mutate(undo)


@router.post("/history/redo")
def post_history_redo():
    return _mutate(redo)


