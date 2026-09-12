from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.validation import (
    accept_coding,
    change_coding,
    drop_comment,
    verify_comment,
)
from reviewdistill.config import (
    LLM_SETTINGS_PROVIDERS,
    PROVIDER_ENV_KEYS,
    default_llm_model,
    ensure_env_gitignore,
    paper_key_set,
    upsert_env_var,
    write_project_llm,
)
from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput, Conflict, CorruptStore, NotFound, ReviewDistillError
from reviewdistill.history import list_history, redo, undo
from reviewdistill.paths import data_location, project_env_path
from reviewdistill.projects import (
    default_registered_project_id,
    list_registered_project_rows,
    llm_selected_payload,
)
from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    add_counterexample,
    deactivate_issue_type,
    edit_issue_type,
    merge_issue_types,
    move_issue_type,
    rename_issue_type,
    split_issue_type,
)
from reviewdistill.views import inbox_payload, issue_payload, taxonomy_payload

router = APIRouter()


@router.get("/inbox")
def get_inbox():
    try:
        return inbox_payload()
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


def _domain_http(exc: ValueError, *, mutate: bool) -> HTTPException:
    msg = str(exc)
    if isinstance(exc, CorruptStore):
        status = 500
    elif isinstance(exc, NotFound):
        status = 404
    elif isinstance(exc, (Conflict, BadInput)):
        status = 400
    elif isinstance(exc, ReviewDistillError):
        status = 400 if mutate else 500
    else:
        status = 400 if mutate else 500
    return HTTPException(status_code=status, detail=msg)


def _mutate(fn):
    try:
        fn()
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {"ok": True}


class ChangeBody(BaseModel):
    issue_type_id: str


_LLM_FAILED = "LLM request failed"


@router.post("/inbox/code")
def post_code():
    """Propose issue types for every unlabeled working-set comment. There is no CLI ``code`` command."""
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
        raise _domain_http(exc, mutate=True) from exc
    return {
        "ok": True,
        "coded": summary.coded,
        "failed": summary.skipped,
        "privacy_warning": summary.privacy_warning,
    }


@router.post("/inbox/{comment_id}/accept")
def post_accept(comment_id: str):
    return _mutate(lambda: accept_coding(comment_id))


@router.post("/inbox/{comment_id}/change")
def post_change(comment_id: str, body: ChangeBody):
    return _mutate(lambda: change_coding(comment_id, issue_type_id=body.issue_type_id))


@router.post("/inbox/{comment_id}/verify")
def post_verify(comment_id: str):
    return _mutate(lambda: verify_comment(comment_id))


@router.post("/inbox/{comment_id}/drop")
def post_drop(comment_id: str):
    return _mutate(lambda: drop_comment(comment_id))


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
    try:
        return taxonomy_payload()
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/taxonomy/merge")
def post_merge(body: MergeBody):
    return _mutate(lambda: merge_issue_types(source_ids=body.source_ids, target_id=body.target_id))


@router.get("/taxonomy/export")
def get_export(format: str = "md"):
    try:
        text = export_rubric(fmt=format)
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc
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
    try:
        projects = list_registered_project_rows()
        default_id = default_registered_project_id()
        selected_id = project_id or default_id
        selected = llm_selected_payload(selected_id) if selected_id else None
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc
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
    try:
        with get_session() as session:
            project = session.get(Project, body.project_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc
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
    try:
        return issue_payload(issue_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


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
    try:
        return list_history()
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/history/undo")
def post_history_undo():
    return _mutate(undo)


@router.post("/history/redo")
def post_history_redo():
    return _mutate(redo)


