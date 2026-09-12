from __future__ import annotations

import fcntl
import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Self, TypeVar

from reviewdistill.db.models import (
    Coding,
    GitCommitRecord,
    IssueCounterexample,
    IssueExample,
    IssueType,
    Project,
    ProofreadingComment,
    TaxonomyEvent,
    comment_quality,
)
from reviewdistill.paths import LOCK_NAME, STAGING_DIRNAME, home_dir

T = TypeVar("T")

MODELS = (
    Project,
    ProofreadingComment,
    Coding,
    IssueType,
    IssueExample,
    IssueCounterexample,
    TaxonomyEvent,
    GitCommitRecord,
)

FILES = {
    Project: "projects.jsonl",
    ProofreadingComment: "comments.jsonl",
    Coding: "codings.jsonl",
    IssueType: "issue_types.jsonl",
    IssueExample: "issue_examples.jsonl",
    IssueCounterexample: "issue_counterexamples.jsonl",
    TaxonomyEvent: "taxonomy_events.jsonl",
    GitCommitRecord: "git_commits.jsonl",
}

SENTINEL_NAME = "COMMIT"


class StoreSession:
    def __init__(self, home: Path):
        self._home = home
        self._lock_fp = None
        self._tables: dict[type, dict[str, object]] = {model: {} for model in MODELS}

    def __enter__(self) -> Self:
        self._home.mkdir(parents=True, exist_ok=True)
        self._lock_fp = (self._home / LOCK_NAME).open("a+")
        fcntl.flock(self._lock_fp, fcntl.LOCK_EX)
        try:
            self._load()
        except Exception:
            self._unlock()
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._unlock()

    def _unlock(self) -> None:
        if self._lock_fp is not None:
            fcntl.flock(self._lock_fp, fcntl.LOCK_UN)
            self._lock_fp.close()
            self._lock_fp = None

    def add(self, obj: object) -> None:
        if isinstance(obj, ProofreadingComment):
            comment_quality(obj)
        self._tables[type(obj)][obj.id] = obj  # type: ignore[attr-defined]

    def delete(self, obj: object) -> None:
        self._tables[type(obj)].pop(obj.id, None)  # type: ignore[attr-defined]

    def get(self, model: type[T], ident: str) -> T | None:
        return self._tables[model].get(ident)  # type: ignore[return-value]

    def find(
        self,
        model: type[T],
        *,
        order_by: str | None = "id",
        reverse: bool = False,
        **eq,
    ) -> list[T]:
        rows = list(self._tables[model].values())
        for key, expected in eq.items():
            if isinstance(expected, (list, tuple, set, frozenset)):
                rows = [row for row in rows if getattr(row, key) in expected]
            else:
                rows = [row for row in rows if getattr(row, key) == expected]
        if order_by is not None:
            rows.sort(key=lambda row: (getattr(row, order_by), getattr(row, "id", "")), reverse=reverse)
        return rows  # type: ignore[return-value]

    def first(self, model: type[T], **eq) -> T | None:
        rows = self.find(model, **eq)
        return rows[0] if rows else None

    def commit(self) -> None:
        self._save()

    def refresh(self, obj: object) -> object:
        return obj

    def _load(self) -> None:
        apply_pending_commit(self._home)
        _cleanup_tmp(self._home)
        self._tables = {model: {} for model in MODELS}
        for model, name in FILES.items():
            path = self._home / name
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    from reviewdistill.errors import CorruptStore

                    raise CorruptStore(f"Invalid JSON in {name}") from exc
                row = model.model_validate(data)
                if model is ProofreadingComment:
                    comment_quality(row)
                self._tables[model][row.id] = row

    def _save(self) -> None:
        for row in self._tables[ProofreadingComment].values():
            comment_quality(row)  # type: ignore[arg-type]
        self._home.mkdir(parents=True, exist_ok=True)
        apply_pending_commit(self._home)
        staging = self._home / STAGING_DIRNAME
        staging.mkdir()
        try:
            for model, name in FILES.items():
                rows = sorted(self._tables[model].values(), key=lambda row: row.id)  # type: ignore[attr-defined]
                path = staging / name
                path.write_text(_jsonl_text(rows), encoding="utf-8")
                _fsync(path)
            sentinel = staging / SENTINEL_NAME
            sentinel.write_text("ok\n", encoding="utf-8")
            _fsync(sentinel)
            _fsync(staging)
            for name in FILES.values():
                (staging / name).replace(self._home / name)
            _fsync(self._home)
            shutil.rmtree(staging, ignore_errors=True)
        finally:
            _cleanup_tmp(self._home)


def _jsonl_text(rows) -> str:
    return "".join(json.dumps(row.model_dump(mode="json"), ensure_ascii=False) + "\n" for row in rows)


def _fsync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _cleanup_tmp(home: Path) -> None:
    for name in FILES.values():
        (home / f"{name}.tmp").unlink(missing_ok=True)


def apply_pending_commit(home: Path) -> None:
    staging = home / STAGING_DIRNAME
    if not staging.is_dir():
        return
    sentinel = staging / SENTINEL_NAME
    if sentinel.is_file():
        for name in FILES.values():
            src = staging / name
            if src.is_file():
                src.replace(home / name)
        try:
            _fsync(home)
        except OSError:
            pass
    shutil.rmtree(staging, ignore_errors=True)


def _ensure_lock_gitignore(home: Path) -> None:
    gitignore = home / ".gitignore"
    if gitignore.is_file():
        text = gitignore.read_text(encoding="utf-8")
        if any(line.strip() == LOCK_NAME for line in text.splitlines()):
            return
        if text and not text.endswith("\n"):
            text += "\n"
        gitignore.write_text(text + f"{LOCK_NAME}\n", encoding="utf-8")
        return
    gitignore.write_text(f"{LOCK_NAME}\n", encoding="utf-8")


_active_session: ContextVar[StoreSession | None] = ContextVar("store_session", default=None)


def init_db() -> None:
    home = home_dir()
    home.mkdir(parents=True, exist_ok=True)
    _ensure_lock_gitignore(home)


def reset_engine() -> None:
    _active_session.set(None)


@contextmanager
def get_session() -> Iterator[StoreSession]:
    existing = _active_session.get()
    if existing is not None:
        yield existing
        return
    init_db()
    with StoreSession(home_dir()) as session:
        token = _active_session.set(session)
        try:
            yield session
        finally:
            _active_session.reset(token)
