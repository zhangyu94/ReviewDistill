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
    delete_comment,
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
from reviewdistill.llm.provider import llm_http_detail
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
    create_empty_label,
    edit_label,
    flatten_label,
    merge_labels,
    move_label,
    recycle_ungrouped,
    remove_label,
    rename_label,
)
from reviewdistill.views import inbox_payload, label_payload, reveal_comment_file, labels_payload

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
    label_id: str


@router.post("/inbox/code")
def post_code():
    """Propose labels for every unlabeled comment to distill. There is no CLI ``code`` command."""
    try:
        summary = code_uncoded_comments()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=llm_http_detail(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=llm_http_detail(exc)) from exc
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {
        "ok": True,
        "coded": summary.coded,
        "failed": summary.skipped,
        "privacy_warning": summary.privacy_warning,
        "label_names": summary.label_names,
    }


@router.post("/inbox/{comment_id}/accept")
def post_accept(comment_id: str):
    return _mutate(lambda: accept_coding(comment_id))


@router.post("/inbox/{comment_id}/change")
def post_change(comment_id: str, body: ChangeBody):
    return _mutate(lambda: change_coding(comment_id, label_id=body.label_id))


@router.post("/inbox/{comment_id}/verify")
def post_verify(comment_id: str):
    return _mutate(lambda: verify_comment(comment_id))


@router.post("/inbox/{comment_id}/delete")
def post_delete(comment_id: str):
    return _mutate(lambda: delete_comment(comment_id))


@router.post("/inbox/{comment_id}/reveal")
def post_reveal(comment_id: str):
    """Select the comment's `.tex` file in the computer's file manager.

    Body is empty. Do not accept a filesystem path; browsers also cannot use
    ``file://`` from this UI.
    """
    try:
        reveal_comment_file(comment_id)
    except HomePathError as exc:
        raise _paths_http(exc) from exc
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {"ok": True}


class RenameBody(BaseModel):
    name: str


class EditBody(BaseModel):
    definition: str


class MoveBody(BaseModel):
    parent_id: str | None = None
    position: int


class CreateBody(BaseModel):
    parent_id: str | None = None


class MergeBody(BaseModel):
    source_ids: list[str]
    target_id: str


def _llm_mutate(fn):
    try:
        result = fn()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=llm_http_detail(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=llm_http_detail(exc)) from exc
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    warning = getattr(result, "privacy_warning", None)
    body = {"ok": True, "privacy_warning": warning}
    labeled = getattr(result, "labeled", None)
    if labeled is not None:
        body["labeled"] = labeled
    names = getattr(result, "label_names", None)
    if names:
        body["label_names"] = list(names)
    return body


@router.get("/labels")
def get_labels():
    try:
        return labels_payload()
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/labels")
def post_create(body: CreateBody):
    try:
        label = create_empty_label(parent_id=body.parent_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {"ok": True, "id": label.id}


@router.post("/labels/merge")
def post_merge(body: MergeBody):
    return _mutate(lambda: merge_labels(source_ids=body.source_ids, target_id=body.target_id))


@router.post("/labels/split")
def post_split_forest():
    """Header bootstrap. Registered next to merge so ``split`` is not parsed as an id."""
    return _llm_mutate(run_header_split)


@router.post("/labels/recycle")
def post_recycle():
    """Park unlabeled working-set comments on a new ungrouped root. Registered next to merge so ``recycle`` is not parsed as an id."""
    try:
        label = recycle_ungrouped()
    except ValueError as exc:
        raise _domain_http(exc, mutate=True) from exc
    return {"ok": True, "id": label.id}


@router.get("/labels/export")
def get_export(format: str = "md", id: list[str] | None = Query(None)):
    """Rubric for active labels. ``id`` (repeatable) keeps only those labels; omit for all. Does not change labels in the UI."""
    try:
        text = export_rubric(fmt=format, label_ids=id)
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


@router.get("/labels/{label_id}")
def get_label_detail(label_id: str):
    try:
        return label_payload(label_id)
    except ValueError as exc:
        raise _domain_http(exc, mutate=False) from exc


@router.post("/labels/{label_id}/rename")
def post_rename(label_id: str, body: RenameBody):
    return _mutate(lambda: rename_label(label_id, name=body.name))


@router.post("/labels/{label_id}/edit")
def post_edit(label_id: str, body: EditBody):
    return _mutate(
        lambda: edit_label(
            label_id,
            definition=body.definition,
        )
    )


@router.post("/labels/{label_id}/move")
def post_move(label_id: str, body: MoveBody):
    return _mutate(lambda: move_label(label_id, parent_id=body.parent_id, position=body.position))


@router.post("/labels/{label_id}/flatten")
def post_flatten(label_id: str):
    return _mutate(lambda: flatten_label(label_id))


@router.post("/labels/{label_id}/remove")
def post_remove(label_id: str):
    return _mutate(lambda: remove_label(label_id))


@router.post("/labels/{label_id}/split")
def post_split(label_id: str):
    return _llm_mutate(lambda: run_leaf_split(label_id))


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


