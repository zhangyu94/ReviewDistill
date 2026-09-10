from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def rd_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "rd-home"
    home.mkdir()
    monkeypatch.setenv("REVIEWDISTILL_HOME", str(home))
    return home


@pytest.fixture
def db(rd_home):
    from reviewdistill.db.session import init_db, reset_engine

    reset_engine()
    init_db()
    yield
    reset_engine()
