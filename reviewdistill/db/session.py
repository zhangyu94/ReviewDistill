from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from reviewdistill.db import models  # noqa: F401
from reviewdistill.paths import db_path, home_dir

_engine = None
_engine_path = None


def get_engine():
    global _engine, _engine_path
    current = str(db_path())
    if _engine is None or _engine_path != current:
        if _engine is not None:
            _engine.dispose()
        home_dir().mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{current}",
            echo=False,
            connect_args={"timeout": 30, "check_same_thread": False},
        )
        _engine_path = current

        @event.listens_for(_engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _connection_record):  # noqa: ARG001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    return _engine


def reset_engine() -> None:
    global _engine, _engine_path
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_path = None


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)
    _migrate_comment_statuses(engine)


def _add_missing_columns(engine) -> None:
    inspector = inspect(engine)
    wanted = {
        "comments": (("git_url", "VARCHAR"),),
        "git_commits": (("remote_url", "VARCHAR"),),
        "taxonomy_events": (("undone", "BOOLEAN DEFAULT 0"),),
    }
    with engine.begin() as conn:
        for table, columns in wanted.items():
            if table not in inspector.get_table_names():
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, col_type in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"))


def _migrate_comment_statuses(engine) -> None:
    inspector = inspect(engine)
    if "comments" not in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text("UPDATE comments SET status = 'pending_disappeared' WHERE status = 'deleted'"))
        conn.execute(text("UPDATE comments SET status = 'superseded' WHERE status = 'modified'"))


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
