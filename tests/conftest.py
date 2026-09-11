from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def fake_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "user-home"
    home.mkdir()
    monkeypatch.setattr("reviewdistill.paths.Path.home", lambda: home)
    return home


@pytest.fixture
def rd_home(tmp_path: Path) -> Path:
    from reviewdistill.paths import use_home

    return use_home(tmp_path / "rd-home")


@pytest.fixture
def db(rd_home):
    from reviewdistill.db.session import init_db, reset_engine

    reset_engine()
    init_db()
    yield
    reset_engine()
