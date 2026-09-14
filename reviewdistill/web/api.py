from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.split import run_header_split, run_leaf_split
from reviewdistill.coding.validation import (
    accept_coding,
    change_coding,
    drop_comment,
    verify_comment,
)
from reviewdistill.config import (
    LLM_SETTINGS_PROVIDERS,
    PROVIDER_ENV_KEYS,
    api_key_from_dotenv,
    default_llm_model,
    ensure_env_gitignore,
    home_key_set,
    load_llm_config,
    upsert_env_var,
    write_home_llm,
)
from reviewdistill.errors import BadInput, Conflict, CorruptStore, NotFound, ReviewDistillError
from reviewdistill.history import list_history, redo, undo
from reviewdistill.paths import (
    HomePathError,
    choose_data_folder,
    data_location,
    home_dir,
    home_env_path,
    open_data_folder,
    use_home,
)
from reviewdistill.taxonomy.export import export_rubric
from reviewdistill.taxonomy.operations import (
    add_counterexample,
    create_empty_issue_type,
    deactivate_issue_type,
    edit_issue_type,
    flatten_issue_type,
    merge_issue_types,
    move_issue_type,
    remove_issue_type,
    rename_issue_type,
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
    """Propose issue types for every unlabeled comment to distill. There is no CLI ``code`` command."""
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


class EditBody(BaseModel):
    definition: str


class MoveBody(BaseModel):
    parent_id: str | None = None
    position: int


class CreateBody(BaseModel):
    parent_id: str | None = None


class CounterexampleBody(BaseModel):
    text: str


class MergeBody(BaseModel):
    source_ids: list[str]
    target_id: str


def _llm_mutate(fn):
    try:
        result = fn()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=_LLM_FAILED) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    warning = getattr(result, "privacy_warning", None)
    return {"ok": True, "privacy_warning": warning}


@router.get("/taxonomy")
def get_taxonomy():
    try:
        return taxonomy_payload()
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/taxonomy")
def post_create(body: CreateBody):
    try:
        issue = create_empty_issue_type(parent_id=body.parent_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {"ok": True, "id": issue.id}


@router.post("/taxonomy/merge")
def post_merge(body: MergeBody):
    return _mutate(lambda: merge_issue_types(source_ids=body.source_ids, target_id=body.target_id))


@router.post("/taxonomy/split")
def post_split_forest():
    """Header bootstrap. Registered next to merge so ``split`` is not parsed as an id."""
    return _llm_mutate(run_header_split)


@router.get("/taxonomy/export")
def get_export(format: str = "md", id: list[str] | None = Query(None)):
    """Rubric for active types. ``id`` (repeatable) keeps only those types; omit for all. Does not change labels in the UI."""
    try:
        text = export_rubric(fmt=format, issue_ids=id)
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


class PathsBody(BaseModel):
    home: str


def _paths_http(exc: HomePathError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/paths")
def post_paths(body: PathsBody):
    """Point ReviewDistill at this folder from now on. Does not copy files."""
    try:
        use_home(body.home)
    except HomePathError as exc:
        raise _paths_http(exc) from exc
    return data_location()


@router.post("/paths/open")
def post_paths_open():
    """Open the data folder in the computer’s file manager."""
    try:
        open_data_folder()
    except HomePathError as exc:
        raise _paths_http(exc) from exc
    return {"ok": True}


@router.post("/paths/choose")
def post_paths_choose():
    """Open a folder picker. Does not change the data folder until Save."""
    try:
        chosen = choose_data_folder()
    except HomePathError as exc:
        raise _paths_http(exc) from exc
    if chosen is None:
        return {"home": None}
    return {"home": str(chosen)}


@router.get("/llm-settings")
def get_llm_settings():
    """Home YAML/``.env`` state, including the saved key for Settings. Ignores ``REVIEWDISTILL_LLM_*``."""
    config = load_llm_config()
    provider = config.llm_provider
    model = config.llm_model
    if provider and provider.lower() == "mock":
        provider = None
        model = None
    return {
        "provider": provider,
        "model": model,
        "key_set": home_key_set(provider),
        "api_key": api_key_from_dotenv(home_env_path(), provider),
    }


class LlmSettingsBody(BaseModel):
    provider: str
    model: str = ""
    api_key: str = ""


@router.post("/llm-settings")
def post_llm_settings(body: LlmSettingsBody):
    """Save provider/model to home YAML and optional key to gitignored ``.env``. Empty ``api_key`` keeps the existing key."""
    provider = body.provider.lower().strip()
    if provider not in LLM_SETTINGS_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown LLM provider")
    model = body.model.strip() or default_llm_model(provider)
    env_name = PROVIDER_ENV_KEYS[provider]
    incoming = body.api_key.strip()
    if not incoming and not home_key_set(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Paste an API key for {provider} ({env_name})",
        )
    write_home_llm(provider=provider, model=model)
    if incoming:
        upsert_env_var(home_env_path(), env_name, incoming)
    ensure_env_gitignore(home_dir())
    return {"ok": True, "key_set": home_key_set(provider)}


@router.get("/taxonomy/{issue_id}")
def get_issue(issue_id: str):
    try:
        return issue_payload(issue_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/taxonomy/{issue_id}/rename")
def post_rename(issue_id: str, body: RenameBody):
    return _mutate(lambda: rename_issue_type(issue_id, name=body.name))


@router.post("/taxonomy/{issue_id}/edit")
def post_edit(issue_id: str, body: EditBody):
    return _mutate(
        lambda: edit_issue_type(
            issue_id,
            definition=body.definition,
        )
    )


@router.post("/taxonomy/{issue_id}/move")
def post_move(issue_id: str, body: MoveBody):
    return _mutate(lambda: move_issue_type(issue_id, parent_id=body.parent_id, position=body.position))


@router.post("/taxonomy/{issue_id}/flatten")
def post_flatten(issue_id: str):
    return _mutate(lambda: flatten_issue_type(issue_id))


@router.post("/taxonomy/{issue_id}/remove")
def post_remove(issue_id: str):
    return _mutate(lambda: remove_issue_type(issue_id))


@router.post("/taxonomy/{issue_id}/deactivate")
def post_deactivate(issue_id: str):
    return _mutate(lambda: deactivate_issue_type(issue_id))


@router.post("/taxonomy/{issue_id}/counterexample")
def post_counterexample(issue_id: str, body: CounterexampleBody):
    return _mutate(lambda: add_counterexample(issue_id, text=body.text))


@router.post("/taxonomy/{issue_id}/split")
def post_split(issue_id: str):
    return _llm_mutate(lambda: run_leaf_split(issue_id))


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


