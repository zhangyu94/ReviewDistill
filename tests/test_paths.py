import sqlite3

import pytest

from reviewdistill.paths import (
    HomePathError,
    data_location,
    db_path,
    find_project_root,
    home_dir,
    move_home,
    use_home,
)


def test_locator_path_is_isolated_from_real_home(tmp_path):
    from reviewdistill.paths import locator_path

    assert locator_path().resolve().is_relative_to(tmp_path.resolve())


def test_home_dir_defaults_when_locator_missing():
    from reviewdistill import paths as paths_mod

    assert not paths_mod.locator_path().is_file()
    assert paths_mod.home_dir() == paths_mod.Path.home() / ".reviewdistill"


def test_blank_locator_falls_through_to_default(tmp_path, monkeypatch):
    locator = _locator_only(tmp_path, monkeypatch)
    locator.parent.mkdir(parents=True)
    locator.write_text("  \n", encoding="utf-8")
    from reviewdistill import paths as paths_mod

    assert home_dir() == paths_mod.Path.home() / ".reviewdistill"


def test_use_home_writes_isolated_locator(tmp_path):
    from reviewdistill.paths import locator_path

    dest = tmp_path / "Documents" / "reviewdistill"
    use_home(dest)
    assert locator_path().resolve().is_relative_to(tmp_path.resolve())
    assert locator_path().read_text(encoding="utf-8").strip() == str(dest.resolve())


def test_home_dir_uses_locator(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = use_home(tmp_path / "rd")
    assert home_dir() == dest
    assert db_path() == dest / "reviewdistill.db"


def test_data_location_uses_resolved_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = use_home(tmp_path / "rd")
    loc = data_location()
    assert "home_env" not in loc
    assert loc["home"] == str(dest)
    assert loc["database"] == str(dest / "reviewdistill.db")


def test_find_project_root_walks_up(tmp_path):
    repo = tmp_path / "paper"
    nested = repo / "src" / "tex"
    nested.mkdir(parents=True)
    (repo / ".reviewdistill").mkdir()
    (repo / ".reviewdistill" / "config.yaml").write_text("project:\n  name: demo\n")
    assert find_project_root(nested) == repo


def test_find_project_root_missing_returns_none(tmp_path):
    assert find_project_root(tmp_path) is None


def _locator_only(tmp_path, monkeypatch):
    locator = tmp_path / "config" / "reviewdistill" / "home"
    monkeypatch.setattr("reviewdistill.paths.locator_path", lambda: locator)
    return locator


def test_use_home_persists_folder(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = tmp_path / "Documents" / "reviewdistill"
    used = use_home(dest)
    assert used == dest.resolve()
    assert dest.is_dir()
    assert home_dir() == dest.resolve()
    assert db_path() == dest.resolve() / "reviewdistill.db"


def test_env_does_not_override_locator(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    used = use_home(tmp_path / "from-cli")
    monkeypatch.setenv("REVIEWDISTILL_HOME", str(tmp_path / "from-env"))
    assert home_dir() == used
    assert home_dir() != tmp_path / "from-env"


def test_move_home_copies_folder_then_uses_it(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    sqlite3.connect(src / "reviewdistill.db").close()
    (src / "config.yaml").write_text("llm: {}\n")
    dest = tmp_path / "backup" / "reviewdistill"
    moved = move_home(dest)
    assert moved == dest.resolve()
    assert (dest / "reviewdistill.db").is_file()
    assert (dest / "config.yaml").read_text() == "llm: {}\n"
    assert (src / "reviewdistill.db").is_file()
    assert home_dir() == dest.resolve()


def test_move_home_refuses_nonempty_destination(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    sqlite3.connect(src / "reviewdistill.db").close()
    dest = tmp_path / "taken"
    dest.mkdir()
    (dest / "other.txt").write_text("no")
    with pytest.raises(HomePathError, match="already has files"):
        move_home(dest)


def test_move_home_refuses_destination_inside_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    with pytest.raises(HomePathError, match="outside the current home"):
        move_home(src / "backup")


def test_move_home_refuses_empty_destination_already_inside_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    dest = src / "backup"
    dest.mkdir()
    with pytest.raises(HomePathError, match="outside the current home"):
        move_home(dest)


def test_move_home_refuses_when_database_is_busy(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    conn = sqlite3.connect(str(src / "reviewdistill.db"))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("BEGIN EXCLUSIVE")
    conn.execute("INSERT INTO t VALUES (1)")
    try:
        with pytest.raises(HomePathError, match="Stop reviewdistill serve"):
            move_home(tmp_path / "new-home")
    finally:
        conn.close()


def test_move_home_refuses_when_database_is_unreadable(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "reviewdistill.db").write_text("not a database")
    with pytest.raises(HomePathError, match="Could not lock"):
        move_home(tmp_path / "new-home")


def test_move_home_refuses_when_wal_engine_is_idle(tmp_path, monkeypatch):
    from sqlalchemy import event, text
    from sqlmodel import Session, create_engine

    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    db = src / "reviewdistill.db"
    engine = create_engine(
        f"sqlite:///{db}",
        echo=False,
        connect_args={"timeout": 30, "check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    with Session(engine) as session:
        session.execute(text("CREATE TABLE t (x INTEGER)"))
        session.commit()
    try:
        with pytest.raises(HomePathError, match="Stop reviewdistill serve"):
            move_home(tmp_path / "new-home")
    finally:
        engine.dispose()


def test_move_home_wraps_copy_errors(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    sqlite3.connect(src / "reviewdistill.db").close()

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("reviewdistill.paths.shutil.copytree", boom)
    with pytest.raises(HomePathError, match="Could not copy"):
        move_home(tmp_path / "new-home")
